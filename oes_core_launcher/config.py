import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


CONFIG_NAME = 'config.json'


def local_data_dir(env=None):
    env = os.environ if env is None else env
    root = env.get('LOCALAPPDATA')
    if not root:
        raise ValueError('Windows local application data is unavailable')
    return Path(root) / 'OES' / 'Core'


@dataclass(frozen=True)
class LauncherConfig:
    worker_id: str
    key_id: str
    relay_url: str
    model_digest: str
    ollama_url: str = 'http://127.0.0.1:11434'
    model: str = 'llama3.2'

    @classmethod
    def load(cls, path=None):
        path = Path(path) if path else local_data_dir() / CONFIG_NAME
        try:
            value = json.loads(path.read_text(encoding='utf-8'))
        except FileNotFoundError as error:
            raise ValueError(f'Configuration is missing: {path}') from error
        except (OSError, ValueError, TypeError) as error:
            raise ValueError('Configuration is not valid JSON') from error
        if not isinstance(value, dict) or set(value) - {
                'worker_id', 'key_id', 'relay_url', 'model_digest', 'ollama_url', 'model'}:
            raise ValueError('Configuration contains unsupported fields')
        config = cls(**value)
        config.validate()
        return config

    def validate(self):
        token = re.compile(r'^[a-zA-Z0-9_-]{1,80}$')
        if not token.fullmatch(self.worker_id) or not token.fullmatch(self.key_id):
            raise ValueError('Worker identity or key identifier is invalid')
        parsed = urlsplit(self.relay_url)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            raise ValueError('Relay URL must be a fixed HTTPS origin')
        if not re.fullmatch(r'[0-9a-f]{64}', self.model_digest):
            raise ValueError('Model digest must be 64 lowercase hexadecimal characters')
        if self.ollama_url != 'http://127.0.0.1:11434':
            raise ValueError('Ollama must use the fixed loopback URL')
        if self.model not in ('llama3.2', 'llama3.2:latest'):
            raise ValueError('The configured model must be llama3.2')

    def worker_environment(self, secret):
        if not re.fullmatch(r'[0-9a-f]{64}', secret or ''):
            raise ValueError('Worker credential is unavailable or invalid')
        return {
            'OES_WORKER_ID': self.worker_id,
            'OES_WORKER_KEY_ID': self.key_id,
            'OES_WORKER_SHARED_KEY': secret,
            'OES_WORKER_RELAY_URL': self.relay_url,
            'OES_WORKER_MODEL_DIGEST': self.model_digest,
            'OLLAMA_BASE_URL': self.ollama_url,
            'OLLAMA_MODEL': self.model,
        }
