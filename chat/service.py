"""Policy assembly and provider-independent output boundary."""
import json
import logging
import time
from dataclasses import replace
from uuid import uuid4
from .policy import (SYSTEM_IDENTITY, PUBLIC_CONTEXT, SERIOUS_INSTRUCTION,
                     serious_selection_instruction, render_serious_selection,
                     public_fact_selection_instruction, render_public_fact_selection,
                     FACTUAL_DISCIPLINE)
from .providers import ChatEvent
from .situation import (SituationAnalyzer, response_contract, validate_playful,
                        validate_character_style, validate_character_safety,
                        character_correction, character_style_instruction, bounded_history,
                        conversational_history, is_lookup_followup)
from .observations import (ObservationState, infer, observation_contract,
                           log_observations, InitiationDecision)
from .worker_protocol import CONTEXT_BUDGET, context_cost
from .capabilities import (CapabilityDenied, CapabilityRegistry, PUBLIC_LOOKUP,
                           evidence_instruction, validate_evidence_answer,
                           public_search_query)
from .localization import DEFAULT_LOCALE, deterministic_response, response_language_instruction
from .clarification import ClarificationAnalyzer

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
    def __init__(self, provider, debug_logger=None, capabilities=None, telemetry=None):
        self.provider = provider
        self.debug_logger = debug_logger
        self.capabilities = capabilities or CapabilityRegistry()
        self.telemetry = telemetry or (lambda event_type, **fields: False)

    def invitation(self, intent, recent):
        """Separate from public conversation; caller must authorize the typed intent."""
        from .initiative import generate_invitation
        return generate_invitation(self.provider, intent, recent, self.debug_logger)

    def stream(self, message, history, context, locale=DEFAULT_LOCALE,
               continuation=None, clarification=None, continuity_store=None,
               clarification_store=None):
        request_started = time.monotonic()
        request_id = uuid4().hex
        if clarification is not None:
            selected = clarification_store.consume(clarification) if clarification_store else None
            if selected is None:
                self.telemetry('safe_error', request_id=request_id,
                               outcome='failure', reason='invalid_request')
                yield ChatEvent('start', {'request_id': request_id})
                yield ChatEvent('error', {'message': SAFE_ERROR})
                return
            message, clarification_reason = selected
            self.telemetry('eyeball_clarification_selected', request_id=request_id,
                           outcome='accepted', dimensions={
                               'product': 'eyeball', 'surface': 'web',
                               'clarification_reason': clarification_reason})
        else:
            decision = ClarificationAnalyzer().analyze(message, locale)
            if decision is not None:
                self.telemetry('request_accepted', request_id=request_id, outcome='accepted')
                self.telemetry('eyeball_clarification_requested', request_id=request_id,
                               outcome='accepted', dimensions={
                                   'product': 'eyeball', 'surface': 'web',
                                   'clarification_reason': decision.reason})
                yield ChatEvent('start', {'request_id': request_id})
                choices = []
                if clarification_store is not None:
                    choices = [{'label': candidate,
                                'token': clarification_store.issue(candidate, decision.reason)}
                               for candidate in decision.candidates]
                prompt_key = ('clarification_candidates' if choices else 'clarification_rephrase')
                yield ChatEvent('clarification', {
                    'prompt': deterministic_response(prompt_key, locale),
                    'choices': choices, 'reason': decision.reason})
                yield ChatEvent('done', {'history': 'exclude_exchange'})
                return
        instruction = SYSTEM_IDENTITY + "\n\n" + PUBLIC_CONTEXT
        history = bounded_history(history)
        state, continuity = SituationAnalyzer().analyze(message, history, context)
        prior_lookup = (continuity_store.consume(continuation, locale)
                        if continuity_store is not None and continuation else None)
        inherited_lookup = bool(prior_lookup and is_lookup_followup(message, state))
        if inherited_lookup:
            state = replace(state, interaction_kind='current_public_information',
                            tone='informative', grounding_mode='public_evidence',
                            response_action='answer_with_public_evidence', certainty='high')
        serious = state.serious
        observed = ObservationState.from_context(context)
        interpretation = infer(observed)

        if self.debug_logger is not None:
            log_observations(self.debug_logger, observed, interpretation,
                             InitiationDecision('stay_silent', 'user_request_precedence'))
            self.debug_logger.info('Eyeball situation %s', json.dumps(state.debug_fields()))

        instruction += observation_contract(observed, interpretation)
        instruction += '\n' + response_contract(state, continuity)
        if not serious and not state.requires_oes_facts:
            instruction += '\n' + FACTUAL_DISCIPLINE
        instruction += '\n' + response_language_instruction(locale)

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

        self.telemetry('request_accepted', request_id=request_id, outcome='accepted')
        self.telemetry('situation_classified', request_id=request_id,
                       dimensions={'interaction_kind': state.interaction_kind,
                                   'response_action': state.response_action,
                                   'grounding_mode': state.grounding_mode})
        if serious or state.requires_oes_facts:
            self.telemetry('grounding_required', request_id=request_id, outcome='allowed',
                           dimensions={'grounding_mode': state.grounding_mode})
        yield ChatEvent("start", {"request_id": request_id})

        def emit(text, chunks=None, done_data=None):
            for chunk in chunks if chunks is not None else (text,):
                yield ChatEvent('delta', {'text': chunk})
            duration = min(600000, int((time.monotonic() - request_started) * 1000))
            self.telemetry('response_completed', request_id=request_id,
                           duration_ms=duration, outcome='success')
            yield ChatEvent('done', done_data or {})

        if state.interaction_kind == 'unknown_visitor_reason':
            yield from emit(deterministic_response('unknown_visitor_reason', locale))
            return

        if state.response_action == 'request_location':
            yield from emit(deterministic_response('request_location', locale))
            return

        if state.response_action == 'answer_with_public_evidence':
            started = time.monotonic()
            success, reason = False, 'not_assigned'
            capability_outcome = 'allowed'
            try:
                lookup_request = (prior_lookup + ' Follow-up: ' + message
                                  if inherited_lookup else message)
                result = self.capabilities.invoke('eyeball', PUBLIC_LOOKUP, lookup_request)
                success, reason = result.success, result.reason
            except CapabilityDenied:
                result = None
                capability_outcome = 'denied'
            except Exception:
                result, reason = None, 'provider_failure'
            self.telemetry('capability_requested', request_id=request_id,
                           outcome=capability_outcome,
                           dimensions={'capability': PUBLIC_LOOKUP})
            duration_ms = max(0, int((time.monotonic() - started) * 1000))
            self.telemetry('capability_completed', request_id=request_id,
                           duration_ms=min(600000, duration_ms),
                           outcome='success' if success else 'failure', reason=reason,
                           dimensions={'capability': PUBLIC_LOOKUP})
            LOG.info('chat capability request_id=%s capability=%s category=public success=%s '
                     'duration_ms=%s reason=%s', request_id, PUBLIC_LOOKUP, success,
                     duration_ms, reason)
            lookup_succeeded = result is not None and result.success
            if lookup_succeeded:
                instruction += '\n\n' + evidence_instruction(result)
            else:
                instruction += (
                    '\n\nThe assigned public lookup did not return verified evidence. Answer any '
                    'stable, non-current part of the user request normally. Do not answer or guess '
                    'the freshness-dependent part, and do not redirect the user to another website. '
                    'The application will append a concise verification limitation.'
                )

        stream = None
        last_chunks = None
        active_attempt = 1

        def provider_candidate(provider_messages, attempt):
            nonlocal stream, last_chunks
            if hasattr(self.provider, 'set_trace'):
                self.provider.set_trace(request_id, attempt)
            candidate = ''
            chunks = []
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
                        chunks.append(text)
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
            last_chunks = tuple(chunks)
            return candidate

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
                    for reason in hard_failures:
                        self.telemetry('validation_rejected', request_id=request_id, attempt=1,
                                       outcome='rejected', reason=reason)
                    raise ServiceFailure('response_validation_exhausted')
                yield from emit(candidate)
                return

            if state.response_action == 'answer_with_public_evidence':
                if not lookup_succeeded:
                    active_attempt = 1
                    candidate = provider_candidate(messages, active_attempt)
                    hard_failures = validate_character_safety(candidate)
                    if hard_failures:
                        LOG.warning('chat response review request_id=%s attempt=1 '
                                    'category=character_validation hard=True reasons=%s',
                                    request_id, ','.join(hard_failures))
                        for reason in hard_failures:
                            self.telemetry('validation_rejected', request_id=request_id, attempt=1,
                                           outcome='rejected', reason=reason)
                        raise ServiceFailure('response_validation_exhausted')
                    limitation = deterministic_response('lookup_limitation', locale)
                    combined = (candidate.rstrip() + '\n\n' + limitation
                                if candidate.strip() else limitation)
                    yield from emit(combined, done_data={'history': 'exclude_exchange'})
                    return

                for attempt in range(2):
                    active_attempt = attempt + 1
                    candidate = provider_candidate(messages, active_attempt)
                    hard_failures = (*validate_character_safety(
                                         candidate, allow_evidence_quantities=True),
                                     *validate_evidence_answer(candidate, result, lookup_request))
                    if not hard_failures:
                        next_token = (continuity_store.issue(
                            public_search_query(lookup_request), locale)
                            if continuity_store is not None else None)
                        done_data = {'continuation': next_token} if next_token else None
                        yield from emit(candidate, done_data=done_data)
                        return
                    LOG.warning('chat response review request_id=%s attempt=%s '
                                'category=character_validation hard=True reasons=%s',
                                request_id, active_attempt, ','.join(hard_failures))
                    for reason in hard_failures:
                        self.telemetry('validation_rejected', request_id=request_id,
                                       attempt=active_attempt, outcome='rejected', reason=reason)
                    if attempt == 0:
                        self.telemetry('correction_attempted', request_id=request_id, attempt=2,
                                       outcome='accepted')
                        correction = (
                            '\nRegenerate once. Answer every material part of the request. Use the '
                            'provided evidence for the current part, retain ordinary reasoning for '
                            'stable parts, and do not redirect the user or deny lookup capability.'
                        )
                        messages = fit_messages(instruction + correction, model_history, message)
                raise ServiceFailure('response_validation_exhausted')

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
                        for reason in (*hard_failures, *soft_failures):
                            self.telemetry('validation_rejected', request_id=request_id,
                                           attempt=attempt + 1, outcome='rejected', reason=reason)

                    if not hard_failures:
                        if best_safe is None or len(soft_failures) < len(best_style):
                            best_safe, best_style = candidate, soft_failures
                        if not soft_failures:
                            yield from emit(candidate)
                            return

                    if attempt == 0:
                        self.telemetry('correction_attempted', request_id=request_id, attempt=2,
                                       outcome='accepted')
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

            if serious or state.requires_oes_facts:
                active_attempt = 1
                candidate = provider_candidate(messages, active_attempt)
                try:
                    rendered = (render_serious_selection(candidate, message) if serious
                                else render_public_fact_selection(candidate))
                except Exception as error:
                    raise ServiceFailure('grounded_rendering') from error
                yield from emit(rendered)
                return

            # Ordinary answers are buffered so hard factual/self-model boundaries can
            # be enforced before any model text is released. This remains one bounded
            # correction attempt and does not create a queue or new capability route.
            for attempt in range(2):
                active_attempt = attempt + 1
                candidate = provider_candidate(messages, active_attempt)
                hard_failures = validate_character_safety(candidate)
                if not hard_failures:
                    yield from emit(candidate, last_chunks)
                    return
                LOG.warning('chat response review request_id=%s attempt=%s '
                            'category=character_validation hard=True reasons=%s',
                            request_id, active_attempt, ','.join(hard_failures))
                for reason in hard_failures:
                    self.telemetry('validation_rejected', request_id=request_id,
                                   attempt=active_attempt, outcome='rejected', reason=reason)
                if attempt == 0:
                    self.telemetry('correction_attempted', request_id=request_id, attempt=2,
                                   outcome='accepted')
                    correction = (
                        '\nRegenerate once. Correct the unsupported factual or self-model claim. '
                        'Treat conversation history as context, not evidence. Do not invent literal '
                        'feelings, desires, independent goals, percentages, probabilities, odds, '
                        'rankings, or quantitative confidence. Preserve a natural concise answer.'
                    )
                    messages = fit_messages(instruction + correction, model_history, message)
            raise ServiceFailure('response_validation_exhausted')

        except Exception as error:
            # Never serialize provider exceptions, URLs, prompts or machine paths.
            category = getattr(error, 'category', 'provider_event_protocol')
            if str(error) == 'Mandatory prompt exceeds context budget':
                category = 'context_budget'
            LOG.warning('chat request failed request_id=%s attempt=%s category=%s',
                        request_id, active_attempt, category)
            safe_reason = category if category in {
                'context_budget', 'worker_unavailable_busy', 'relay_ownership_lease',
                'job_deadline', 'model_readiness_digest', 'ollama_connect_failure',
                'ollama_cold_start_timeout', 'ollama_read_timeout',
                'ollama_protocol_malformed_event', 'incomplete_ollama_stream',
                'output_limit', 'response_output_limit', 'provider_event_protocol',
                'incomplete_provider_stream', 'grounded_rendering',
                'response_validation_exhausted', 'result_rejection_obsolete',
                'transport_rpc_timeout', 'cancellation', 'input_message_bounds'} else 'provider_event_protocol'
            self.telemetry('safe_error', request_id=request_id, attempt=active_attempt,
                           outcome='failure', reason=safe_reason)
            yield ChatEvent("error", {"message": SAFE_ERROR})

        finally:
            if stream is not None and hasattr(stream, "close"):
                stream.close()
