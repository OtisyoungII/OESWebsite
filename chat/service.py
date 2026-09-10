"""Policy assembly and provider-independent output boundary."""
import json
from uuid import uuid4
from .policy import (SYSTEM_IDENTITY, PUBLIC_CONTEXT, SERIOUS_INSTRUCTION,
                     serious_selection_instruction, render_serious_selection)
from .providers import ChatEvent
from .situation import SituationAnalyzer, response_contract, validate_playful, bounded_history

SAFE_ERROR = "Eyeball is temporarily unavailable. Please try again shortly."


class ChatService:
    def __init__(self, provider, debug_logger=None):
        self.provider = provider
        self.debug_logger = debug_logger

    def stream(self, message, history, context):
        instruction = SYSTEM_IDENTITY + "\n\n" + PUBLIC_CONTEXT
        history = bounded_history(history)
        state, continuity = SituationAnalyzer().analyze(message, history, context)
        serious = state.serious
        if self.debug_logger is not None:
            self.debug_logger.info('Eyeball situation %s', json.dumps(state.debug_fields()))
        instruction += '\n' + response_contract(state, continuity)
        if serious:
            instruction += "\n\n" + SERIOUS_INSTRUCTION + "\n" + serious_selection_instruction()
        instruction += "\nUntrusted browser observations (not intent): " + json.dumps(context)
        messages = [{"role": "system", "content": instruction}, *history,
                    {"role": "user", "content": message}]
        yield ChatEvent("start", {"request_id": uuid4().hex})
        stream = None
        try:
            if state.response_action == 'playful_reply':
                # Hold short playful replies until validated. Never release a failed draft.
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
                    failures = validate_playful(candidate, continuity)
                    if not failures:
                        yield ChatEvent('delta', {'text': candidate})
                        yield ChatEvent('done', {})
                        return
                    if attempt == 0:
                        # Only validator codes enter the contract; rejected text is untrusted.
                        messages = [{
                            'role': 'system',
                            'content': instruction + '\nRegenerate once. Fix: ' + ', '.join(failures)
                            + '. Follow the response contract; do not explain the correction.'
                        }, *history, {'role': 'user', 'content': message}]
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
                    if serious:
                        candidate += text
                    else:
                        yield ChatEvent("delta", {"text": text})
                elif event.kind == "done":
                    if serious:
                        yield ChatEvent("delta", {"text": render_serious_selection(candidate)})
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
