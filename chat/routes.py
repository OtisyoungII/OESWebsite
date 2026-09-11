"""Bounded public request contract. No browser-controlled configuration."""
import json
from flask import Blueprint, Response, current_app, jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge
from .service import ChatService, SAFE_ERROR
from .observations import (validate_context, ObservationState, InitiationRestraint,
                           decide_initiation, infer, log_observations)
from .initiative import authorize_intent
from .runtime import enabled
from .providers import create_provider

bp = Blueprint("chat", __name__)


def unavailable(status=503):
    response = jsonify(message=SAFE_ERROR)
    response.status_code = status
    response.headers['Retry-After'] = '60' if status == 429 else '5'
    return response


@bp.before_request
def runtime_gate():
    if request.method != 'POST':
        return None
    config = current_app.config
    manual = request.endpoint == 'chat.chat'
    live = enabled(config, 'OES_EYEBALL_ENABLED') and enabled(config, 'OES_AI_CHAT_ENABLED')
    if not live or (not manual and not enabled(config, 'OES_PROACTIVE_ENABLED')):
        return unavailable() if manual else jsonify(action='stay_silent', reason='disabled')
    if not current_app.extensions['chat_admission'].request_allowed(request.remote_addr):
        return unavailable(429)


@bp.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'no-store, no-transform'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@bp.route('/api/chat/health', methods=['GET'])
def health():
    config = current_app.config
    live = enabled(config, 'OES_EYEBALL_ENABLED')
    chat_on = live and enabled(config, 'OES_AI_CHAT_ENABLED')
    try:
        create_provider(config)  # Validate only; no DNS, health probe or generation.
        configured = True
    except Exception:
        configured = False
    response = jsonify(eyeball='enabled' if live else 'disabled',
                       chat=('ready' if configured else 'unavailable') if chat_on else 'disabled',
                       proactive='enabled' if chat_on and enabled(config, 'OES_PROACTIVE_ENABLED') else 'disabled',
                       provider='configured' if configured else 'unconfigured', reachability='unchecked')
    response.status_code = 503 if chat_on and not configured else 200
    return response


def validate(payload):
    if not isinstance(payload, dict) or set(payload) - {"message", "history", "context"}:
        raise ValueError("Only message, history and context are accepted.")
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip() or len(message) > 4000:
        raise ValueError("Message must contain 1–4,000 characters.")
    history = payload.get("history", [])
    if not isinstance(history, list) or len(history) > 10:
        raise ValueError("History must contain at most 10 messages.")
    cleaned = []
    for item in history:
        if (not isinstance(item, dict) or set(item) != {"role", "content"}
                or item.get("role") not in ("user", "assistant")
                or not isinstance(item.get("content"), str)
                or not item["content"].strip() or len(item["content"]) > 4000):
            raise ValueError("History accepts bounded user/assistant text only.")
        cleaned.append({"role": item["role"], "content": item["content"].strip()})
    if sum(len(item["content"]) for item in cleaned) > 12000:
        raise ValueError("History exceeds the conversation limit.")
    context = validate_context(payload.get("context", {}))
    return message.strip(), cleaned, context


@bp.route("/api/chat", methods=["POST"])
def chat():
    if request.mimetype != "application/json":
        return jsonify(message="Use application/json."), 415
    if (request.headers.get("Sec-Fetch-Site") == "cross-site"
            or (request.origin and request.origin != request.host_url.rstrip("/"))):
        return jsonify(message="Same-origin requests only."), 403
    request.max_content_length = 65536
    try:
        args = validate(request.get_json())
    except RequestEntityTooLarge:
        return jsonify(message="Request exceeds 64 KiB."), 413
    except BadRequest:
        return jsonify(message="Invalid JSON request."), 400
    except ValueError as error:
        return jsonify(message=str(error)), 400
    release, status = current_app.extensions['chat_admission'].acquire(request.remote_addr)
    if release is None:
        return unavailable(status)
    try:
        provider = current_app.extensions["chat_provider_factory"]()
    except Exception:
        release()
        return jsonify(message=SAFE_ERROR), 503

    # Capture configuration before streaming; no request content enters debug logs.
    debug_logger = current_app.logger if current_app.debug else None

    def generate():
        stream = ChatService(provider, debug_logger=debug_logger).stream(*args)
        try:
            for event in stream:
                yield f"event: {event.kind}\ndata: {json.dumps(event.data)}\n\n"
        finally:
            try:
                stream.close()
            finally:
                release()

    response = Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-store", "X-Accel-Buffering": "no",
        "X-Content-Type-Options": "nosniff",
    })
    response.call_on_close(release)  # Also covers a response closed before iteration.
    return response


@bp.route('/api/chat/initiation', methods=['POST'])
def initiation():
    """Deterministic permission for an invitation; never calls a model."""
    if request.mimetype != 'application/json':
        return jsonify(message='Use application/json.'), 415
    if (request.headers.get('Sec-Fetch-Site') == 'cross-site'
            or (request.origin and request.origin != request.host_url.rstrip('/'))):
        return jsonify(message='Same-origin requests only.'), 403
    request.max_content_length = 4096
    try:
        payload = request.get_json()
        if not isinstance(payload, dict) or set(payload) - {'context', 'restraint'}:
            raise ValueError('Only context and restraint are accepted.')
        observed = ObservationState.from_context(payload.get('context', {}))
        restraint = InitiationRestraint.from_payload(payload.get('restraint', {}))
    except RequestEntityTooLarge:
        return jsonify(message='Request exceeds 4 KiB.'), 413
    except BadRequest:
        return jsonify(message='Invalid JSON request.'), 400
    except ValueError as error:
        return jsonify(message=str(error)), 400
    decision = decide_initiation(observed, restraint)
    if current_app.debug:
        log_observations(current_app.logger, observed, infer(observed), decision)
    response = jsonify(action=decision.action, reason=decision.reason)
    response.headers['Cache-Control'] = 'no-store'
    return response


@bp.route('/api/chat/invitation', methods=['POST'])
def invitation():
    """Reauthorize in software before constructing a provider or generating wording."""
    if request.mimetype != 'application/json':
        return jsonify(message='Use application/json.'), 415
    if (request.headers.get('Sec-Fetch-Site') == 'cross-site'
            or (request.origin and request.origin != request.host_url.rstrip('/'))):
        return jsonify(message='Same-origin requests only.'), 403
    request.max_content_length = 8192
    try:
        payload = request.get_json()
        if not isinstance(payload, dict) or set(payload) - {'context', 'restraint', 'history', 'recent_invitations'}:
            raise ValueError('Invalid invitation request fields.')
        _, history, context = validate({'message': 'invitation eligibility',
                                       'history': payload.get('history', []),
                                       'context': payload.get('context', {})})
        observed = ObservationState.from_context(context)
        restraint = InitiationRestraint.from_payload(payload.get('restraint', {}))
        recent = payload.get('recent_invitations', [])
        if (not isinstance(recent, list) or len(recent) > 3
                or any(not isinstance(text, str) or len(text) > 240 for text in recent)):
            raise ValueError('Recent invitations must be at most three bounded texts.')
    except RequestEntityTooLarge:
        return jsonify(message='Request exceeds 8 KiB.'), 413
    except BadRequest:
        return jsonify(message='Invalid JSON request.'), 400
    except ValueError as error:
        return jsonify(message=str(error)), 400
    intent, reason = authorize_intent(observed, restraint, history)
    logger = current_app.logger if current_app.debug else None
    if logger is not None:
        logger.info('Eyeball invitation initiation %s', json.dumps({
            'action': intent.action if intent else 'stay_silent',
            'target': intent.target if intent else None, 'reason': reason}))
    result = {'action': 'stay_silent', 'reason': reason}
    if intent is not None:
        release, status = current_app.extensions['chat_admission'].acquire(request.remote_addr, proactive=True)
        if release is None:
            return unavailable(status)
        try:
            provider = current_app.extensions['chat_provider_factory']()
            text = ChatService(provider, debug_logger=logger).invitation(intent, recent)
        except Exception:
            text = None
        finally:
            release()
        result = ({'action': 'offer_help', 'reason': reason, 'text': text} if text
                  else {'action': 'stay_silent', 'reason': 'generation_unavailable_or_rejected'})
    response = jsonify(result)
    response.headers['Cache-Control'] = 'no-store'
    return response
