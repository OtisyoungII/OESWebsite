"""Private owner-only analytics routes; absent unless explicitly configured."""
import hashlib
import hmac
import os
import secrets

from flask import (Blueprint, current_app, make_response, redirect, render_template,
                   request, url_for)

from .auth import (COOKIE, CSRF_COOKIE, LoginLimiter, OwnerAuthStore, PASSWORD, SESSION_SECONDS,
                   totp_counter, verify_password)
from .query import AnalyticsQuery, RANGES


bp = Blueprint('owner_analytics', __name__, template_folder='templates')


def _enabled(value):
    return str(value).strip().lower() == 'true'


def _fingerprint():
    # Ephemeral rate-limit key only; never logged or persisted.
    value = request.remote_addr or 'unknown'
    secret = current_app.config['OES_OWNER_SESSION_SECRET'].encode('utf-8')
    return hmac.new(secret, value.encode('utf-8'), hashlib.sha256).digest()


def _login_csrf(value=None):
    nonce = value or secrets.token_urlsafe(24)
    secret = current_app.config['OES_OWNER_SESSION_SECRET'].encode('utf-8')
    signature = hmac.new(secret, nonce.encode('ascii'), hashlib.sha256).hexdigest()
    return f'{nonce}.{signature}'


def _valid_login_csrf(value):
    if not isinstance(value, str) or value.count('.') != 1 or len(value) > 160:
        return False
    nonce, _ = value.rsplit('.', 1)
    return hmac.compare_digest(_login_csrf(nonce), value)


def _security(response):
    response.headers['Cache-Control'] = 'no-store, private'
    response.headers['Content-Security-Policy'] = (
        "default-src 'none'; style-src 'self'; img-src 'self'; form-action 'self'; "
        "base-uri 'none'; frame-ancestors 'none'")
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response


def _set_cookie(response, name, value, max_age):
    response.set_cookie(name, value, max_age=max_age, httponly=True,
                        secure=current_app.config['OES_OWNER_COOKIE_SECURE'],
                        samesite='Strict', path='/owner/analytics')


def _clear(response):
    for name in (COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path='/owner/analytics',
                               secure=current_app.config['OES_OWNER_COOKIE_SECURE'],
                               samesite='Strict')


def _login_page(error=None, status=200):
    csrf = _login_csrf()
    response = make_response(render_template(
        'owner_analytics/login.html', csrf_token=csrf, error=error), status)
    _set_cookie(response, CSRF_COOKIE, csrf, 600)
    return response


def _authenticated(csrf=False, touch=True):
    token = request.cookies.get(COOKIE)
    supplied = request.form.get('csrf_token') if csrf else None
    try:
        return current_app.extensions['owner_analytics_auth'].validate(
            token, supplied, touch=touch)
    except Exception:
        return False


@bp.after_request
def secure_owner_response(response):
    return _security(response)


@bp.get('/login')
def login_form():
    if _authenticated():
        return redirect(url_for('owner_analytics.dashboard'))
    return _login_page()


@bp.post('/login')
def login():
    limiter = current_app.extensions['owner_analytics_limiter']
    key = _fingerprint()
    if not limiter.allow(key):
        return _login_page('Sign-in unavailable.', 429)
    csrf = request.form.get('csrf_token', '')
    if not (_valid_login_csrf(csrf)
            and hmac.compare_digest(csrf, request.cookies.get(CSRF_COOKIE, ''))):
        return _login_page('Sign-in unavailable.', 400)
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    code = request.form.get('totp', '')
    password_valid = verify_password(password, current_app.config['OES_OWNER_PASSWORD_HASH'])
    valid = (hmac.compare_digest(username, current_app.config['OES_OWNER_USERNAME'])
             and password_valid)
    counter = totp_counter(current_app.config['OES_OWNER_TOTP_SECRET'], code) if valid else None
    try:
        accepted = counter is not None and current_app.extensions[
            'owner_analytics_auth'].consume_totp(counter)
        if not accepted:
            return _login_page('Sign-in unavailable.', 401)
        session = current_app.extensions['owner_analytics_auth'].create()
    except Exception:
        return _login_page('Sign-in unavailable.', 503)
    limiter.clear(key)
    response = redirect(url_for('owner_analytics.dashboard'))
    _set_cookie(response, COOKIE, session.token, SESSION_SECONDS)
    _set_cookie(response, CSRF_COOKIE, session.csrf, SESSION_SECONDS)
    return response


@bp.get('/')
def dashboard():
    if not _authenticated():
        response = redirect(url_for('owner_analytics.login_form'))
        _clear(response)
        return response
    selected = request.args.get('range', '30d')
    if selected not in RANGES:
        selected = '30d'
    try:
        snapshot = current_app.extensions['owner_analytics_query'].snapshot(selected)
        unavailable = False
    except Exception:
        snapshot, unavailable = None, True
    return render_template('owner_analytics/dashboard.html', snapshot=snapshot,
                           unavailable=unavailable,
                           csrf_token=request.cookies.get(CSRF_COOKIE, ''))


@bp.post('/logout')
def logout():
    token = request.cookies.get(COOKIE)
    if not _authenticated(csrf=True, touch=False):
        return 'Invalid request.', 400
    try:
        current_app.extensions['owner_analytics_auth'].delete(token)
    except Exception:
        pass
    response = redirect(url_for('owner_analytics.login_form'))
    _clear(response)
    return response


def init_owner_analytics(app):
    defaults = {
        'OES_OWNER_ANALYTICS_ENABLED': 'false',
        'OES_OWNER_USERNAME': '', 'OES_OWNER_PASSWORD_HASH': '',
        'OES_OWNER_TOTP_SECRET': '', 'OES_OWNER_SESSION_SECRET': '',
        'OES_OWNER_COOKIE_SECURE': 'true',
    }
    for key, default in defaults.items():
        app.config.setdefault(key, os.environ.get(key, default))
    app.config['OES_OWNER_COOKIE_SECURE'] = _enabled(app.config['OES_OWNER_COOKIE_SECURE'])
    if not _enabled(app.config['OES_OWNER_ANALYTICS_ENABLED']):
        return False
    database_url = str(app.config.get('OES_ANALYTICS_DATABASE_URL', '')).strip()
    required = (database_url, app.config['OES_OWNER_USERNAME'],
                app.config['OES_OWNER_PASSWORD_HASH'], app.config['OES_OWNER_TOTP_SECRET'],
                app.config['OES_OWNER_SESSION_SECRET'])
    if not all(required):
        return False
    try:
        import base64
        totp_key = base64.b32decode(
            str(app.config['OES_OWNER_TOTP_SECRET']).strip().upper(), casefold=True)
    except Exception:
        return False
    if (not PASSWORD.fullmatch(str(app.config['OES_OWNER_PASSWORD_HASH']))
            or len(totp_key) < 20 or not 1 <= len(str(app.config['OES_OWNER_USERNAME'])) <= 64):
        return False
    try:
        auth = OwnerAuthStore(database_url, app.config['OES_OWNER_SESSION_SECRET'])
    except ValueError:
        return False
    app.extensions['owner_analytics_auth'] = auth
    app.extensions['owner_analytics_query'] = AnalyticsQuery(database_url)
    app.extensions['owner_analytics_limiter'] = LoginLimiter()
    app.register_blueprint(bp, url_prefix='/owner/analytics')
    return True
