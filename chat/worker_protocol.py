"""Small versioned wire contract shared by the relay and outbound-only worker."""
import hashlib
import hmac
import json
import re
import time

MAX_BODY = 262144
MAX_OUTPUT = 16000
JOB_SECONDS = 100
LEASE_SECONDS = 15
POLL_SECONDS = 10
TOKEN = re.compile(r'^[a-zA-Z0-9_-]{1,80}$')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate field')
            result[key] = value
        return result
    if len(raw) > MAX_BODY:
        raise ValueError('Body too large')
    try:
        value = json.loads(raw, object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Invalid number')))
        if not isinstance(value, dict) or canonical(value) != raw:
            raise ValueError('Canonical object required')
    except (RecursionError, UnicodeError) as error:
        raise ValueError('Invalid JSON encoding or nesting') from None
    return value


def fields(value, names):
    if not isinstance(value, dict) or set(value) != set(names):
        raise ValueError('Invalid fields')


def token(value):
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise ValueError('Invalid identifier')
    return value


def settings(config):
    identity, key_id, key = (config.get(k, '') for k in
                            ('OES_WORKER_ID', 'OES_WORKER_KEY_ID', 'OES_WORKER_SHARED_KEY'))
    token(identity)
    token(key_id)
    if not isinstance(key, str) or not re.fullmatch(r'[0-9a-f]{64}', key):
        raise ValueError('Invalid worker credential configuration')
    return identity, key_id, bytes.fromhex(key)


def signature(key, direction, path, identity, key_id, stamp, nonce, raw):
    material = '\n'.join(('oes-worker-v1', direction, 'POST', path, identity,
                          key_id, stamp, nonce, hashlib.sha256(raw).hexdigest())).encode()
    return hmac.new(key, material, hashlib.sha256).hexdigest()


def signed_headers(config, path, raw, nonce, now=None):
    identity, key_id, key = settings(config)
    stamp = str(int(time.time() if now is None else now))
    return {'Content-Type': 'application/json', 'X-OES-Worker': identity,
            'X-OES-Key': key_id, 'X-OES-Time': stamp, 'X-OES-Nonce': nonce,
            'X-OES-Signature': signature(key, 'request', path, identity, key_id, stamp, nonce, raw)}


def messages_valid(messages):
    if not isinstance(messages, list) or not 2 <= len(messages) <= 12:
        raise ValueError('Invalid messages')
    history_chars = 0
    for index, item in enumerate(messages):
        fields(item, ('role', 'content'))
        role, content = item['role'], item['content']
        allowed = ('system',) if index == 0 else ('user',) if index == len(messages)-1 else ('user', 'assistant')
        if role not in allowed or not isinstance(content, str) or not content.strip():
            raise ValueError('Invalid message')
        if len(content) > (16000 if index == 0 else 4000):
            raise ValueError('Message too large')
        if 0 < index < len(messages)-1:
            history_chars += len(content)
    if history_chars > 12000 or len(canonical({'messages': messages})) > MAX_BODY - 2048:
        raise ValueError('History too large')
