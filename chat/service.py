"""Policy assembly and provider-independent output boundary."""
import json
import logging
from uuid import uuid4
from .policy import (SYSTEM_IDENTITY, PUBLIC_CONTEXT, SERIOUS_INSTRUCTION,
                     serious_selection_instruction, render_serious_selection,
                     public_fact_selection_instruction, render_public_fact_selection)
from .providers import ChatEvent
from .situation import (SituationAnalyzer, response_contract, validate_playful,
                        validate_character_style, validate_character_safety,
                        character_correction, character_style_instruction, bounded_history,
                        conversational_history)
from .observations import (ObservationState, infer, observation_contract,
                           log_observations, InitiationDecision)
from .worker_protocol import CONTEXT_BUDGET, context_cost

SAFE_ERROR = "Eyeball is temporarily unavailable. Please try again shortly."
LOG = logging.getLogger('oes.chat')


class ServiceFailure(ValueError):
    def __init__(self, category):
        super().__init__(category)
        self.category = category


def fit_messages(instruction, history, message):
    """
    Fit provider-bound messages to the worker's inference budget.

    Authoritative system instructions and the current user message are never
    truncated. Oldest conversation history is discarded first, preferring a
    complete user/assistant exchange when one is available.
    """
    fitted_history = list(history)

    def assemble():
        return [
            {"role": "system", "content": instruction},
            *fitted_history,
            {"role": "user", "content": message},
        ]

    messages = assemble()

    while context_cost(messages) > CONTEXT_BUDGET and fitted_history:
        if (len(fitted_history) >= 2
                and fitted_history[0].get("role") == "user"
                and fitted_history[1].get("role") == "assistant"):
            del fitted_history[:2]
        else:
            del fitted_history[0]

        messages = assemble()

    if context_cost(messages) > CONTEXT_BUDGET:
        raise ValueError("Mandatory prompt exceeds context budget")

    return messages


class ChatService:
    def __init__(self, provider, debug_logger=None):
        self.provider = provider
        self.debug_logger = debug_logger

    def invitation(self, intent, recent):
        """Separate from public conversation; caller must authorize the typed intent."""
        from .initiative import generate_invitation
        return generate_invitation(self.provider, intent, recent, self.debug_logger)

    def stream(self, message, history, context):
        instruction = SYSTEM_IDENTITY + "\n\n" + PUBLIC_CONTEXT
        history = bounded_history(history)
        state, continuity = SituationAnalyzer().analyze(message, history, context)
        serious = state.serious
        observed = ObservationState.from_context(context)
        interpretation = infer(observed)

        if self.debug_logger is not None:
            log_observations(self.debug_logger, observed, interpretation,
                             InitiationDecision('stay_silent', 'user_request_precedence'))
            self.debug_logger.info('Eyeball situation %s', json.dumps(state.debug_fields()))

        instruction += observation_contract(observed, interpretation)
        instruction += '\n' + response_contract(state, continuity)

        if state.response_action == 'character_reply':
            instruction += '\n' + character_style_instruction(message)

        if serious:
            instruction += "\n\n" + SERIOUS_INSTRUCTION + "\n" + serious_selection_instruction()
        elif state.requires_oes_facts:
            instruction += "\n\n" + public_fact_selection_instruction()

        # Grounded selection receives no untrusted conversation prose. Ordinary and
        # hypothetical turns retain only conversational exchanges, excluding earlier
        # grounded requests and their deterministic assistant fallbacks.
        model_history = ([] if state.requires_oes_facts
                         else conversational_history(history))

        request_id = uuid4().hex
        yield ChatEvent("start", {"request_id": request_id})

        if state.interaction_kind == 'unknown_visitor_reason':
            yield ChatEvent('delta', {'text': "I can't know why you're here. What caught your eye?"})
            yield ChatEvent('done', {})
            return

        stream = None
        active_attempt = 1

        def provider_candidate(provider_messages, attempt):
            nonlocal stream
            if hasattr(self.provider, 'set_trace'):
                self.provider.set_trace(request_id, attempt)
            candidate = ''
            finished = False
            stream = self.provider.stream(provider_messages)
            try:
                for event in stream:
                    if event.kind == 'delta':
                        try:
                            text = event.data['text']
                        except (KeyError, TypeError) as error:
                            raise ServiceFailure('provider_event_protocol') from error
                        if not isinstance(text, str):
                            raise ServiceFailure('provider_event_protocol')
                        candidate += text
                        if len(candidate) > 16000:
                            raise ServiceFailure('response_output_limit')
                    elif event.kind == 'done':
                        finished = True
                        break
                    else:
                        raise ServiceFailure('provider_event_protocol')
            finally:
                if hasattr(stream, 'close'):
                    stream.close()
                stream = None
            if not finished:
                raise ServiceFailure('incomplete_provider_stream')
            return candidate

        def emit(text):
            yield ChatEvent('delta', {'text': text})
            yield ChatEvent('done', {})

        try:
            messages = fit_messages(instruction, model_history, message)

            if state.response_action == 'reason_hypothetically':
                active_attempt = 1
                candidate = provider_candidate(messages, active_attempt)
                hard_failures = validate_character_safety(candidate)
                if hard_failures:
                    LOG.warning('chat response review request_id=%s attempt=1 '
                                'category=character_validation hard=True reasons=%s',
                                request_id, ','.join(hard_failures))
                    raise ServiceFailure('response_validation_exhausted')
                yield from emit(candidate)
                return

            if state.response_action in ('playful_reply', 'character_reply'):
                # Safety is blocking. Style is a best-effort quality pass and can
                # never make a completed safe response unavailable.
                best_safe = None
                best_style = None
                for attempt in range(2):
                    active_attempt = attempt + 1
                    try:
                        candidate = provider_candidate(messages, attempt + 1)
                    except Exception as error:
                        if best_safe is not None and attempt == 1:
                            category = getattr(error, 'category', 'provider_event_protocol')
                            LOG.warning('chat correction skipped request_id=%s attempt=2 category=%s',
                                        request_id, category)
                            yield from emit(best_safe)
                            return
                        raise

                    hard_failures = validate_character_safety(candidate)
                    soft_failures = (validate_playful(candidate, continuity)
                                     if state.response_action == 'playful_reply'
                                     else validate_character_style(candidate, continuity))

                    if hard_failures or soft_failures:
                        LOG.warning('chat response review request_id=%s attempt=%s '
                                    'category=character_validation hard=%s reasons=%s',
                                    request_id, attempt + 1, bool(hard_failures),
                                    ','.join((*hard_failures, *soft_failures)))

                    if not hard_failures:
                        if best_safe is None or len(soft_failures) < len(best_style):
                            best_safe, best_style = candidate, soft_failures
                        if not soft_failures:
                            yield from emit(candidate)
                            return

                    if attempt == 0:
                        failures = (*hard_failures, *soft_failures)
                        correction = (
                            'Regenerate once. Fix: ' + ', '.join(failures)
                            + '. Follow the response contract; do not explain the correction.'
                            if state.response_action == 'playful_reply'
                            else character_correction()
                        )

                        corrected_instruction = instruction + '\n' + correction

                        # Re-fit after adding correction text because the correction itself
                        # consumes worker context and may require dropping older history.
                        try:
                            messages = fit_messages(corrected_instruction, model_history, message)
                        except ValueError as error:
                            if best_safe is not None:
                                LOG.warning('chat correction skipped request_id=%s attempt=2 '
                                            'category=context_budget', request_id)
                                yield from emit(best_safe)
                                return
                            raise ServiceFailure('context_budget') from error

                if best_safe is not None:
                    yield from emit(best_safe)
                    return
                raise ServiceFailure('response_validation_exhausted')

            active_attempt = 1
            if hasattr(self.provider, 'set_trace'):
                self.provider.set_trace(request_id, active_attempt)
            stream = self.provider.stream(messages)
            size = 0
            candidate = ""

            for event in stream:
                if event.kind == "delta":
                    try:
                        text = event.data["text"]
                    except (KeyError, TypeError) as error:
                        raise ServiceFailure('provider_event_protocol') from error

                    if not isinstance(text, str):
                        raise ServiceFailure('provider_event_protocol')

                    size += len(text)

                    if size > 16000:
                        raise ServiceFailure('response_output_limit')

                    if serious or state.requires_oes_facts:
                        candidate += text
                    else:
                        yield ChatEvent("delta", {"text": text})

                elif event.kind == "done":
                    if serious or state.requires_oes_facts:
                        try:
                            rendered = (render_serious_selection(candidate, message) if serious
                                        else render_public_fact_selection(candidate))
                        except Exception as error:
                            raise ServiceFailure('grounded_rendering') from error
                        yield ChatEvent("delta", {"text": rendered})

                    yield ChatEvent("done", {})
                    return

                else:
                    raise ServiceFailure('provider_event_protocol')

            raise ServiceFailure('incomplete_provider_stream')

        except Exception as error:
            # Never serialize provider exceptions, URLs, prompts or machine paths.
            category = getattr(error, 'category', 'provider_event_protocol')
            if str(error) == 'Mandatory prompt exceeds context budget':
                category = 'context_budget'
            LOG.warning('chat request failed request_id=%s attempt=%s category=%s',
                        request_id, active_attempt, category)
            yield ChatEvent("error", {"message": SAFE_ERROR})

        finally:
            if stream is not None and hasattr(stream, "close"):
                stream.close()
