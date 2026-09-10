"""Bounded public request contract. No browser-controlled configuration."""
import json
from flask import Blueprint, Response, current_app, jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge
from .service import ChatService, SAFE_ERROR

bp = Blueprint("chat", __name__)
CONTEXT_VALUES = {
    "section": {"home", "products", "client-work", "services", "government", "community", "research", "about", "contact"},
    "project": {"chaseingreen", "lottovate", "drinkswithfriendz"},
    "device": {"desktop", "tablet", "mobile"},
    "interaction_mode": {"pointer", "touch", "keyboard"},
}


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
    context = payload.get("context", {})
    if not isinstance(context, dict) or set(context) - CONTEXT_VALUES.keys():
        raise ValueError("Invalid context fields.")
    for key, value in context.items():
        if not isinstance(value, str) or value not in CONTEXT_VALUES[key]:
            raise ValueError("Invalid context value.")
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
    try:
        provider = current_app.extensions["chat_provider_factory"]()
    except Exception:
        return jsonify(message=SAFE_ERROR), 503

    def generate():
        yield from (f"event: {event.kind}\ndata: {json.dumps(event.data)}\n\n"
                    for event in ChatService(provider).stream(*args))

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-store", "X-Accel-Buffering": "no",
        "X-Content-Type-Options": "nosniff",
    })
