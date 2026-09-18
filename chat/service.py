"""Policy assembly and provider-independent output boundary."""
import json
from uuid import uuid4
from .policy import (SYSTEM_IDENTITY, PUBLIC_CONTEXT, SERIOUS_INSTRUCTION,
                     serious_selection_instruction, render_serious_selection,
                     public_fact_selection_instruction, render_public_fact_selection)
from .providers import ChatEvent
from .situation import (SituationAnalyzer, response_contract, validate_playful,
                        validate_character, character_correction, character_style_instruction,
                        bounded_history)
from .observations import (ObservationState, infer, observation_contract,
                           log_observations, InitiationDecision)
from .worker_protocol import CONTEXT_BUDGET, context_cost

SAFE_ERROR = "Eyeball is temporarily unavailable. Please try again shortly."


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

        model_history = [] if state.requires_oes_facts and not serious else history

        yield ChatEvent("start", {"request_id": uuid4().hex})

        if state.interaction_kind == 'unknown_visitor_reason':
            yield ChatEvent('delta', {'text': "I can't know why you're here. What caught your eye?"})
            yield ChatEvent('done', {})
            return

        stream = None

        try:
            messages = fit_messages(instruction, model_history, message)

            if state.response_action in ('playful_reply', 'character_reply'):
                # Hold casual character replies until validated. Never release a failed draft.
                for attempt in range(2):
                    candidate = ''
                    finished = False
                    stream = self.provider.stream(messages)

                    try:
                        for event in stream:
                            if event.kind == 'delta':
                                text = event.data['text']

                                if not isinstance(text, str):
                                    raise ValueError('Invalid text')

                                candidate += text

                                if len(candidate) > 16000:
                                    raise ValueError('Output limit exceeded')

                            elif event.kind == 'done':
                                finished = True
                                break

                            else:
                                raise ValueError('Unexpected provider event')

                    finally:
                        if hasattr(stream, 'close'):
                            stream.close()
                        stream = None

                    if not finished:
                        raise ValueError('Incomplete stream')

                    validator = (validate_playful
                                 if state.response_action == 'playful_reply'
                                 else validate_character)

                    failures = validator(candidate, continuity)

                    if not failures:
                        yield ChatEvent('delta', {'text': candidate})
                        yield ChatEvent('done', {})
                        return

                    if attempt == 0:
                        # Only bounded correction instructions enter; rejected text stays untrusted.
                        correction = (
                            'Regenerate once. Fix: ' + ', '.join(failures)
                            + '. Follow the response contract; do not explain the correction.'
                            if state.response_action == 'playful_reply'
                            else character_correction()
                        )

                        corrected_instruction = instruction + '\n' + correction

                        # Re-fit after adding correction text because the correction itself
                        # consumes worker context and may require dropping older history.
                        messages = fit_messages(
                            corrected_instruction,
                            model_history,
                            message,
                        )

                raise ValueError('Playful response failed validation twice')

            stream = self.provider.stream(messages)
            size = 0
            candidate = ""

            for event in stream:
                if event.kind == "delta":
                    text = event.data["text"]

                    if not isinstance(text, str):
                        raise ValueError("Invalid text")

                    size += len(text)

                    if size > 16000:
                        raise ValueError("Output limit exceeded")

                    if serious or state.requires_oes_facts:
                        candidate += text
                    else:
                        yield ChatEvent("delta", {"text": text})

                elif event.kind == "done":
                    if serious or state.requires_oes_facts:
                        rendered = (
                            render_serious_selection(candidate)
                            if serious
                            else render_public_fact_selection(candidate)
                        )
                        yield ChatEvent("delta", {"text": rendered})

                    yield ChatEvent("done", {})
                    return

                else:
                    raise ValueError("Unexpected provider event")

            raise ValueError("Incomplete stream")

        except Exception:
            # Never serialize provider exceptions, URLs, prompts or machine paths.
            yield ChatEvent("error", {"message": SAFE_ERROR})

        finally:
            if stream is not None and hasattr(stream, "close"):
                stream.close()