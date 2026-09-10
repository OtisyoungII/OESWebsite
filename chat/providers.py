"""Provider-owned HTTP details; only normalized events leave this module."""
from dataclasses import dataclass
import json
import time
from typing import Iterator, Protocol
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler


@dataclass(frozen=True)
class ChatEvent:
    kind: str
    data: dict


class ChatProvider(Protocol):
    def stream(self, messages: list[dict]) -> Iterator[ChatEvent]: ...


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OllamaProvider:
    def __init__(self, base_url, model, timeout=30, deadline=120):
        parsed = urlsplit(base_url)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"}):
            raise ValueError("Invalid server inference configuration")
        self.url = base_url.rstrip("/") + "/api/chat"
        self.model = model
        self.timeout = timeout
        self.deadline = deadline

    def stream(self, messages):
        payload = json.dumps({"model": self.model, "messages": messages,
                              "stream": True, "options": {"num_predict": 600}}).encode()
        request = Request(self.url, data=payload, headers={"Content-Type": "application/json"})
        # Server configuration is authoritative. No environment proxy or redirects.
        opener = build_opener(ProxyHandler({}), NoRedirect())
        started = time.monotonic()
        with opener.open(request, timeout=self.timeout) as response:
            while True:
                if time.monotonic() - started > self.deadline:
                    raise TimeoutError("Generation deadline exceeded")
                line = response.readline(65537)
                if not line:
                    raise ValueError("Incomplete provider stream")
                if len(line) > 65536:
                    raise ValueError("Provider event too large")
                record = json.loads(line)
                if not isinstance(record, dict) or record.get("error"):
                    raise ValueError("Invalid provider event")
                text = record.get("message", {}).get("content", "")
                if not isinstance(text, str):
                    raise ValueError("Invalid provider text")
                if text:
                    yield ChatEvent("delta", {"text": text})
                if record.get("done") is True:
                    yield ChatEvent("done", {})
                    return


def create_provider(config):
    if config["OES_CHAT_PROVIDER"] != "ollama":
        raise ValueError("Unsupported server provider")
    return OllamaProvider(config["OLLAMA_BASE_URL"], config["OLLAMA_MODEL"])
