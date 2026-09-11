"""Register public chat without changing existing page routes."""
import os
from .providers import create_provider
from .routes import bp
from .runtime import Admission
from .worker_relay import WorkerRelay, bp as worker_bp


def init_chat(app):
    # Loopback defaults are for local development, not production hosting.
    for key, default in {"OES_CHAT_PROVIDER": "ollama",
                         "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
                         "OLLAMA_MODEL": "llama3.2",
                         "OES_AI_BASE_URL": "", "OES_AI_API_KEY": "", "OES_AI_MODEL": "",
                         "OES_EYEBALL_ENABLED": "true", "OES_AI_CHAT_ENABLED": "true",
                         "OES_PROACTIVE_ENABLED": "true", "OES_API_RATE_LIMIT": "60",
                         "OES_CHAT_RATE_LIMIT": "12", "OES_PROACTIVE_RATE_LIMIT": "3",
                         "OES_AI_MAX_CONCURRENCY": "2", "OES_WORKER_ENABLED": "false",
                         "OES_WORKER_ID": "", "OES_WORKER_KEY_ID": "",
                         "OES_WORKER_SHARED_KEY": ""}.items():
        app.config.setdefault(key, os.environ.get(key, default))
    relay = WorkerRelay(app.config)
    app.extensions['worker_relay'] = relay
    app.config['_OES_WORKER_RELAY'] = relay
    app.extensions["chat_provider_factory"] = lambda: create_provider(app.config)
    app.extensions['chat_admission'] = Admission(app.config)
    app.register_blueprint(bp)
    app.register_blueprint(worker_bp)
