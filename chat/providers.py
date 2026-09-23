"""Provider-owned HTTP details; only normalized events leave this module."""
from dataclasses import dataclass
import json
import time
from typing import Iterator, Protocol
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from ipaddress import ip_address
from urllib.error import HTTPError


@dataclass(frozen=True)
class ChatEvent:
    kind: str
    data: dict


class ChatProvider(Protocol):
    def stream(self, messages: list[dict]) -> Iterator[ChatEvent]: ...


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GenerationDeadline(TimeoutError):
    pass


def open_response(opener, request, timeout):
    try:
        return opener.open(request, timeout=timeout)
    except HTTPError as error:
        error.close()
        raise ValueError('Upstream HTTP failure') from None


def bounded_lines(response, started, deadline):
    """read1 returns available bytes: trickled lines cannot evade the deadline."""
    buffer = b''
    total = 0
    while True:
        if time.monotonic() - started > deadline:
            raise GenerationDeadline('Generation deadline exceeded')
        chunk = response.read1(4096)
        if not chunk:
            if buffer:
                yield buffer
            return
        total += len(chunk)
        if total > 1048576:
            raise ValueError('Upstream byte limit exceeded')
        buffer += chunk
        while b'\n' in buffer:
            line, buffer = buffer.split(b'\n', 1)
            if len(line) > 65536:
                raise ValueError('Provider event too large')
            yield line.rstrip(b'\r')
        if len(buffer) > 65536:
            raise ValueError('Provider event too large')


class OllamaProvider:
    def __init__(self, base_url, model, timeout=30, deadline=120):
        if not isinstance(model, str) or not model.strip() or any(ord(c) < 32 for c in model):
            raise ValueError('Invalid server inference model')
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
        with open_response(opener, request, self.timeout) as response:
            for line in bounded_lines(response, started, self.deadline):
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
            raise ValueError('Incomplete provider stream')


class OpenAICompatibleProvider:
    """Server-configured HTTPS Chat Completions SSE; no SDK or provider retries."""
    def __init__(self, base_url, api_key, model, timeout=30, deadline=120):
        parsed = urlsplit(base_url)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment
                or any(c.isspace() or ord(c) < 32 for c in base_url)
                or '\\' in base_url or '%' in parsed.netloc):
            raise ValueError('Invalid hosted provider URL')
        # Configuration is trusted server input, but reject obvious local destinations.
        host = parsed.hostname.lower().rstrip('.')
        if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')):
            raise ValueError('Hosted provider must be public HTTPS')
        try:
            address = ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError('Hosted provider must be public HTTPS')
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError('Invalid hosted provider port')
        for value in (api_key, model):
            if not isinstance(value, str) or not value.strip() or len(value) > 4096 or any(ord(c) < 32 for c in value):
                raise ValueError('Missing or invalid hosted configuration')
        self.url = base_url.rstrip('/') + '/chat/completions'
        self.api_key, self.model = api_key, model
        self.timeout, self.deadline = timeout, deadline

    def stream(self, messages):
        payload = json.dumps({'model': self.model, 'messages': messages,
                              'stream': True, 'max_tokens': 600}).encode()
        request = Request(self.url, data=payload, headers={
            'Content-Type': 'application/json', 'Accept': 'text/event-stream',
            'Authorization': 'Bearer ' + self.api_key})
        opener = build_opener(ProxyHandler({}), NoRedirect())
        started = time.monotonic()
        with open_response(opener, request, self.timeout) as response:
            if response.headers.get_content_type() != 'text/event-stream':
                raise ValueError('Expected provider SSE')
            data, frame_size, finished = [], 0, False
            for line in bounded_lines(response, started, self.deadline):
                frame_size += len(line)
                if frame_size > 65536:
                    raise ValueError('Provider frame too large')
                if line:
                    if line.startswith(b'data:'):
                        data.append(line[5:].lstrip(b' '))
                    continue
                frame_size = 0
                if not data:
                    continue
                raw, data = b'\n'.join(data), []
                if raw == b'[DONE]':
                    if not finished:
                        raise ValueError('Incomplete provider completion')
                    yield ChatEvent('done', {})
                    return
                record = json.loads(raw)
                if not isinstance(record, dict) or record.get('error'):
                    raise ValueError('Invalid provider event')
                choices = record.get('choices')
                if choices == [] and isinstance(record.get('usage'), dict):
                    continue
                if not isinstance(choices, list) or len(choices) != 1 or finished:
                    raise ValueError('Invalid provider choices')
                choice = choices[0]
                if not isinstance(choice, dict) or choice.get('index') != 0:
                    raise ValueError('Invalid provider choice')
                delta = choice.get('delta')
                if not isinstance(delta, dict) or delta.get('tool_calls') or delta.get('function_call'):
                    raise ValueError('Unexpected provider action')
                text = delta.get('content')
                if text is not None:
                    if not isinstance(text, str):
                        raise ValueError('Invalid provider text')
                    if text:
                        yield ChatEvent('delta', {'text': text})
                finish = choice.get('finish_reason')
                if finish is not None:
                    if finish != 'stop':
                        raise ValueError('Provider did not complete normally')
                    finished = True
            raise ValueError('Incomplete provider stream')


def create_provider(config):
    if config['OES_CHAT_PROVIDER'] == 'outbound_worker':
        from .outbound_provider import OutboundWorkerProvider
        return OutboundWorkerProvider(config)
    if config['OES_CHAT_PROVIDER'] == 'ollama':
        return OllamaProvider(config['OLLAMA_BASE_URL'], config['OLLAMA_MODEL'])
    if config['OES_CHAT_PROVIDER'] == 'openai_compatible':
        return OpenAICompatibleProvider(config.get('OES_AI_BASE_URL', ''),
                                        config.get('OES_AI_API_KEY', ''), config.get('OES_AI_MODEL', ''))
    raise ValueError('Unsupported server provider')
