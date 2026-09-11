"""Production entry point. Never enables the interactive development debugger."""
import os
from werkzeug.middleware.proxy_fix import ProxyFix
from app import app

app.config.update(DEBUG=False, TESTING=False)
# Production must explicitly select a provider; do not silently fall back to a laptop.
app.config['OES_CHAT_PROVIDER'] = os.environ.get('OES_CHAT_PROVIDER', '')
hops = int(os.environ.get('OES_TRUSTED_PROXY_HOPS', '0'))
if not 0 <= hops <= 2:
    raise ValueError('OES_TRUSTED_PROXY_HOPS must be between zero and two')
if hops:
    # Only enable behind that exact number of trusted, header-sanitizing proxies.
    # The origin server must be inaccessible to direct public clients.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=0, x_port=0, x_prefix=0)
