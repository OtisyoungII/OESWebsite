"""Register public chat without changing existing page routes."""
import os
from .providers import create_provider
from .routes import bp


def init_chat(app):
    # Loopback defaults are for local development, not production hosting.
    for key, default in {"OES_CHAT_PROVIDER": "ollama",
                         "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
                         "OLLAMA_MODEL": "llama3.2"}.items():
        app.config.setdefault(key, os.environ.get(key, default))
    app.extensions["chat_provider_factory"] = lambda: create_provider(app.config)
    app.register_blueprint(bp)
