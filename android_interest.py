"""Opt-in Android interest list. Public requests can insert, never read."""
import hmac
import os
import re
import secrets

from flask import Blueprint, current_app, make_response, render_template, request

from chat.runtime import Admission
from product_intelligence import same_origin


bp = Blueprint('android_interest', __name__)
COOKIE = 'oes_android_form'
CONSENT_VERSION = 'android-interest-v1'
FORM_TOKEN = re.compile(r'[a-f0-9]{64}')
EMAIL = re.compile(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[a-z0-9-]+(?:\.[a-z0-9-]+)+", re.I)


def init_android_interest(app):
    app.config.setdefault('OES_ANDROID_INTEREST_DSN', os.environ.get('OES_ANDROID_INTEREST_DSN', ''))
    app.extensions['android_interest_admission'] = Admission({'OES_API_RATE_LIMIT': 6})
    app.register_blueprint(bp)


def save_interest(dsn, email):
    import psycopg

    with psycopg.connect(dsn, connect_timeout=3, sslmode='verify-full',
                         options='-c statement_timeout=2000') as connection:
        connection.execute(
            'INSERT INTO android_interest.registrations (email, consent_version) '
            'VALUES (%s, %s) ON CONFLICT DO NOTHING',
            (email, CONSENT_VERSION))


@bp.route('/chaseingreen/android', methods=['GET', 'POST'])
def register():
    dsn = current_app.config['OES_ANDROID_INTEREST_DSN']
    if not dsn:
        return make_response(render_template('android_interest.html', unavailable=True,
                                             openai_ads_pixel_id=''), 200 if request.method == 'GET' else 503,
                             {'Cache-Control': 'no-store'})
    token = secrets.token_hex(32)
    status, result = 200, None
    if request.method == 'POST':
        request.max_content_length = 4096
        cookie, submitted = request.cookies.get(COOKIE, ''), request.form.get('csrf', '')
        if not (same_origin() and FORM_TOKEN.fullmatch(submitted)
                and FORM_TOKEN.fullmatch(cookie) and hmac.compare_digest(cookie, submitted)):
            status, result = 403, 'Please reload the page and try again.'
        elif not current_app.extensions['android_interest_admission'].request_allowed(request.remote_addr):
            status, result = 429, 'Too many attempts. Please try again later.'
        else:
            email = request.form.get('email', '').strip().lower()
            if (request.form.get('consent') != 'yes' or len(email) > 254
                    or not EMAIL.fullmatch(email)):
                status, result = 400, 'Enter a valid email address and confirm consent.'
            else:
                try:
                    save_interest(dsn, email)
                    result = 'Your request was received. We will contact you if there is an Android update.'
                except Exception:
                    current_app.logger.warning('android_interest_storage_unavailable')
                    status, result = 503, 'Registration is temporarily unavailable. Please try again later.'
    response = make_response(render_template('android_interest.html', csrf=token,
                                             result=result, submitted=status == 200 and result,
                                             openai_ads_pixel_id=''), status)
    response.headers['Cache-Control'] = 'no-store'
    response.set_cookie(COOKIE, token, secure=True, httponly=True, samesite='Strict',
                        max_age=900, path='/chaseingreen/android')
    return response
