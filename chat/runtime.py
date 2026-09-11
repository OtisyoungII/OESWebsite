"""Small-beta, process-local admission control. No browser restraint is trusted."""
from collections import deque
import hashlib
import hmac
import secrets
import threading
import time


def enabled(config, key):
    value = config.get(key, True)
    return value is True or (isinstance(value, str) and value.lower() == 'true')


class Admission:
    def __init__(self, config, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.Lock()
        self.salt = secrets.token_bytes(32)
        self.clients = {}
        self.active = 0
        self.global_calls = deque()
        self.limits = {}
        for name, default in [('OES_API_RATE_LIMIT', 60), ('OES_CHAT_RATE_LIMIT', 12),
                              ('OES_PROACTIVE_RATE_LIMIT', 3), ('OES_AI_MAX_CONCURRENCY', 2)]:
            value = int(config.get(name, default))
            if not 1 <= value <= 1000:
                raise ValueError('Invalid runtime limit: ' + name)
            self.limits[name] = value

    def _client(self, address, now):
        key = hmac.new(self.salt, (address or 'unknown').encode(), hashlib.sha256).digest()
        # Bounded map; full capacity fails closed rather than evicting active limits.
        for old in [k for k, v in self.clients.items() if now - v['last'] >= 600]:
            del self.clients[old]
        if key not in self.clients:
            if len(self.clients) >= 2048:
                return None
            self.clients[key] = {'last': now, 'api': deque(), 'chat': deque(), 'proactive': deque()}
        entry = self.clients[key]
        entry['last'] = now
        for kind, window in [('api', 60), ('chat', 60), ('proactive', 600)]:
            while entry[kind] and entry[kind][0] <= now - window:
                entry[kind].popleft()
        return entry

    def request_allowed(self, address):
        with self.lock:
            now = self.clock()
            entry = self._client(address, now)
            if entry is None or len(entry['api']) >= self.limits['OES_API_RATE_LIMIT']:
                return False
            entry['api'].append(now)
            return True

    def acquire(self, address, proactive=False):
        with self.lock:
            now = self.clock()
            entry = self._client(address, now)
            while self.global_calls and self.global_calls[0] <= now - 60:
                self.global_calls.popleft()
            if (entry is None or len(entry['chat']) >= self.limits['OES_CHAT_RATE_LIMIT']
                    or len(self.global_calls) >= 30
                    or (proactive and len(entry['proactive']) >= self.limits['OES_PROACTIVE_RATE_LIMIT'])):
                return None, 429
            if self.active >= self.limits['OES_AI_MAX_CONCURRENCY']:
                return None, 503
            entry['chat'].append(now)
            if proactive:
                entry['proactive'].append(now)
            self.global_calls.append(now)
            self.active += 1
        released = False

        def release():
            nonlocal released
            with self.lock:
                if not released:
                    self.active -= 1
                    released = True
        return release, None
