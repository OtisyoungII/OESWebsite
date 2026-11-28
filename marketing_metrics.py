"""Optional private daily aggregates. No raw events or visitor identifiers."""
import os

from flask import Blueprint, current_app, request

from chat.runtime import Admission
from product_intelligence import same_origin


bp = Blueprint('marketing_metrics', __name__)
PAGES = frozenset({'chaseingreen', 'getting_started', 'onboarding', 'aquafunded',
                   'lottovate', 'sportfolio', 'drinks-with-friendz', 'scout',
                   'rush-and-risk', 'eyeball'})
CLICKS = frozenset({'app_store', 'discord', 'linkedin', 'affiliate'})
STEPS = frozenset(f'step_{n}' for n in range(1, 9))


def init_marketing_metrics(app):
    app.config.setdefault('OES_MARKETING_METRICS_DSN', os.environ.get('OES_MARKETING_METRICS_DSN', ''))
    app.extensions['marketing_metrics_admission'] = Admission({'OES_API_RATE_LIMIT': 40})
    app.register_blueprint(bp)


def increment(dsn, page, action):
    import psycopg

    with psycopg.connect(dsn, connect_timeout=3, sslmode='verify-full',
                         options='-c statement_timeout=2000') as connection:
        connection.execute(
            'INSERT INTO oes_marketing.daily (day_utc, page, action, total) '
            "VALUES ((CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date, %s, %s, 1) "
            'ON CONFLICT (day_utc, page, action) DO UPDATE SET total = daily.total + 1',
            (page, action))


@bp.post('/api/marketing-metric')
def metric():
    dsn = current_app.config['OES_MARKETING_METRICS_DSN']
    if not dsn:
        return '', 404
    if not same_origin():
        return '', 403
    request.max_content_length = 512
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or set(payload) != {'page', 'action'}:
        return '', 400
    page, action = payload['page'], payload['action']
    if not isinstance(page, str) or not isinstance(action, str) or page not in PAGES:
        return '', 400
    if action != 'view' and action not in CLICKS and action not in STEPS:
        return '', 400
    if (action == 'affiliate' or action in STEPS) and page != 'aquafunded':
        return '', 400
    if not current_app.extensions['marketing_metrics_admission'].request_allowed(request.remote_addr):
        return '', 429
    try:
        increment(dsn, page, action)
    except Exception:
        current_app.logger.warning('marketing_metrics_unavailable')
        return '', 503
    return '', 204
