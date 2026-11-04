"""Explicit UTC aggregation and retention; never runs in a public request."""
from datetime import date, datetime, timedelta, timezone
import logging
import os

from .constants import MAINTENANCE_LOCK_ID


LOG = logging.getLogger('oes.analytics')
DETAIL_DAYS = 30
EXPIRED_SESSION_DAYS = 30
AGGREGATE_MONTHS = 13
METRICS = (
    'sessions', 'visits', 'page_views', 'product_activations',
    'eyeball_interactions', 'response_successes', 'safe_errors',
    'cancelled_requests', 'response_latency', 'analytics_drops', 'telemetry_gaps',
)


def enabled(value):
    return str(value).strip().lower() == 'true'


def _utc_day(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date()
    if isinstance(value, date):
        return value
    raise ValueError('Invalid analytics maintenance time')


class AnalyticsMaintenance:
    """One bounded transactional maintenance pass over persisted facts."""
    def __init__(self, database_url, *, connect=None, now=None):
        self.database_url = database_url
        self._connect = connect
        self.now = now or (lambda: datetime.now(timezone.utc))

    def _connection(self):
        if self._connect is None:
            import psycopg
            self._connect = psycopg.connect
        return self._connect(
            self.database_url, connect_timeout=2,
            options='-c statement_timeout=30000 -c lock_timeout=5000')

    def run(self):
        current = self.now()
        today = _utc_day(current)
        detail_cutoff = today - timedelta(days=DETAIL_DAYS)
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_try_advisory_xact_lock(%s)',
                               (MAINTENANCE_LOCK_ID,))
                if cursor.fetchone() != (True,):
                    return {'status': 'already_running', 'days': 0}
                cursor.execute(
                    "SELECT day FROM ("
                    "SELECT (occurred_at AT TIME ZONE 'UTC')::date AS day FROM analytics_events "
                    "UNION SELECT day FROM analytics_dropped_events "
                    "UNION SELECT day FROM analytics_aggregation_days WHERE finalized_at IS NULL"
                    ") candidates WHERE day < %s AND NOT EXISTS ("
                    "SELECT 1 FROM analytics_aggregation_days finalized "
                    "WHERE finalized.day=candidates.day AND finalized.finalized_at IS NOT NULL) "
                    "ORDER BY day", (today,))
                days = [row[0] for row in cursor.fetchall()]
                for day in days:
                    self._aggregate_day(cursor, day, current, day < detail_cutoff)
                cursor.execute(
                    "DELETE FROM analytics_events e USING analytics_aggregation_days a "
                    "WHERE a.day=(e.occurred_at AT TIME ZONE 'UTC')::date "
                    "AND a.finalized_at IS NOT NULL AND e.occurred_at < %s",
                    (datetime.combine(detail_cutoff, datetime.min.time(), timezone.utc),))
                cursor.execute(
                    'DELETE FROM analytics_dropped_events d USING analytics_aggregation_days a '
                    'WHERE a.day=d.day AND a.finalized_at IS NOT NULL AND d.day < %s',
                    (detail_cutoff,))
                cursor.execute(
                    'DELETE FROM analytics_sessions WHERE expires_at < %s',
                    (current - timedelta(days=EXPIRED_SESSION_DAYS),))
                cursor.execute(
                    'DELETE FROM analytics_owner_sessions WHERE expires_at <= %s', (current,))
                cursor.execute(
                    "DELETE FROM analytics_daily_metrics WHERE day < "
                    "(%s::date - INTERVAL '13 months')::date", (today,))
                cursor.execute(
                    "DELETE FROM analytics_aggregation_days WHERE day < "
                    "(%s::date - INTERVAL '13 months')::date", (today,))
                self._update_earliest(cursor)
            connection.commit()
        return {'status': 'completed', 'days': len(days)}

    @staticmethod
    def _aggregate_day(cursor, day, current, finalize):
        cursor.execute('DELETE FROM analytics_daily_metrics WHERE day=%s', (day,))
        cursor.execute(
            "INSERT INTO analytics_daily_metrics(day,metric,count) "
            "SELECT %s, metric, count FROM (VALUES "
            "('sessions', (SELECT COUNT(*) FROM analytics_events WHERE event_type='website_session_started' AND (occurred_at AT TIME ZONE 'UTC')::date=%s)),"
            "('visits', (SELECT COUNT(*) FROM analytics_events WHERE event_type='website_visit_started' AND (occurred_at AT TIME ZONE 'UTC')::date=%s)),"
            "('page_views', (SELECT COUNT(*) FROM analytics_events WHERE event_type='website_page_viewed' AND (occurred_at AT TIME ZONE 'UTC')::date=%s)),"
            "('product_activations', (SELECT COUNT(*) FROM analytics_events WHERE event_type='product_card_activated' AND (occurred_at AT TIME ZONE 'UTC')::date=%s)),"
            "('eyeball_interactions', (SELECT COUNT(*) FROM analytics_events WHERE event_type IN ('eyeball_opened','eyeball_closed','eyeball_message_submitted','eyeball_language_changed','eyeball_clarification_requested','eyeball_clarification_selected','eyeball_clarification_rephrase') AND (occurred_at AT TIME ZONE 'UTC')::date=%s)),"
            "('response_successes', (SELECT COUNT(*) FROM analytics_events WHERE event_type='response_completed' AND outcome='success' AND (occurred_at AT TIME ZONE 'UTC')::date=%s)),"
            "('safe_errors', (SELECT COUNT(*) FROM analytics_events WHERE event_type='safe_error' AND (occurred_at AT TIME ZONE 'UTC')::date=%s)),"
            "('cancelled_requests', (SELECT COUNT(*) FROM analytics_events WHERE event_type='request_cancelled' AND (occurred_at AT TIME ZONE 'UTC')::date=%s)),"
            "('response_latency', 0),"
            "('analytics_drops', (SELECT COALESCE(SUM(count),0) FROM analytics_dropped_events WHERE day=%s)),"
            "('telemetry_gaps', (SELECT COALESCE(SUM(value),0) FROM analytics_events WHERE event_type='telemetry_gap' AND (occurred_at AT TIME ZONE 'UTC')::date=%s))"
            ") AS totals(metric,count)",
            (day, day, day, day, day, day, day, day, day, day, day))
        cursor.execute(
            "UPDATE analytics_daily_metrics SET duration_count=latency.samples, "
            "duration_sum=latency.total FROM (SELECT COUNT(duration_ms) AS samples, "
            "COALESCE(SUM(duration_ms),0) AS total FROM analytics_events "
            "WHERE event_type='response_completed' AND outcome='success' "
            "AND (occurred_at AT TIME ZONE 'UTC')::date=%s) latency "
            "WHERE day=%s AND metric='response_latency'", (day, day))
        cursor.execute(
            "SELECT COUNT(*), COALESCE(SUM(CASE WHEN event_type='telemetry_gap' THEN value ELSE 0 END),0) "
            "FROM analytics_events WHERE (occurred_at AT TIME ZONE 'UTC')::date=%s", (day,))
        event_count, gap_count = cursor.fetchone()
        cursor.execute(
            'SELECT COALESCE(SUM(count),0) FROM analytics_dropped_events WHERE day=%s', (day,))
        drop_count = cursor.fetchone()[0]
        cursor.execute(
            'INSERT INTO analytics_aggregation_days '
            '(day,source_event_count,source_drop_count,telemetry_gap_count,aggregated_at,finalized_at) '
            'VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(day) DO UPDATE SET '
            'source_event_count=EXCLUDED.source_event_count, '
            'source_drop_count=EXCLUDED.source_drop_count, '
            'telemetry_gap_count=EXCLUDED.telemetry_gap_count, '
            'aggregated_at=EXCLUDED.aggregated_at, '
            'finalized_at=COALESCE(analytics_aggregation_days.finalized_at,EXCLUDED.finalized_at)',
            (day, event_count, drop_count, gap_count, current, current if finalize else None))

    @staticmethod
    def _update_earliest(cursor):
        cursor.execute(
            "SELECT MIN(day) FROM ("
            "SELECT MIN(started_at AT TIME ZONE 'UTC')::date AS day FROM analytics_sessions "
            "UNION ALL SELECT MIN(occurred_at AT TIME ZONE 'UTC')::date FROM analytics_events "
            "UNION ALL SELECT MIN(day) FROM analytics_dropped_events "
            "UNION ALL SELECT MIN(day) FROM analytics_aggregation_days"
            ") available")
        earliest = cursor.fetchone()[0]
        if earliest is not None:
            cursor.execute(
                "INSERT INTO analytics_metadata(key,value) VALUES('earliest_available_date',%s) "
                "ON CONFLICT(key) DO UPDATE SET value=EXCLUDED.value",
                (earliest.isoformat(),))
        else:
            cursor.execute(
                "DELETE FROM analytics_metadata WHERE key='earliest_available_date'")


def main():
    if not enabled(os.environ.get('OES_ANALYTICS_MAINTENANCE_ENABLED', 'false')):
        print('Analytics maintenance disabled.')
        return 0
    database_url = os.environ.get('OES_ANALYTICS_DATABASE_URL', '').strip()
    if not database_url:
        print('Analytics maintenance unavailable.')
        return 1
    try:
        result = AnalyticsMaintenance(database_url).run()
    except Exception:
        LOG.warning('analytics maintenance failed category=database_unavailable')
        print('Analytics maintenance unavailable.')
        return 1
    print('Analytics maintenance:', result['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
