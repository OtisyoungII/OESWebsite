from collections import Counter
from datetime import date, datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from persistent_analytics.maintenance import AnalyticsMaintenance, main
from persistent_analytics.sink import PsycopgAnalyticsWriter
from oes_telemetry import make_event


NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)


class MaintenanceDatabase:
    def __init__(self, days=()):
        self.days = list(days)
        self.calls = []
        self.commits = 0

    def connect(self, database_url, **kwargs):
        self.calls.append(('connect', database_url, kwargs))
        return Connection(self)


class Connection:
    def __init__(self, database): self.database = database
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def cursor(self): return Cursor(self.database)
    def commit(self): self.database.commits += 1


class Cursor:
    def __init__(self, database):
        self.database = database
        self.result = []
        self.rowcount = 1

    def __enter__(self): return self
    def __exit__(self, *args): return False

    def execute(self, sql, params=None):
        normalized = ' '.join(sql.split())
        self.database.calls.append((normalized, params))
        if normalized.startswith('SELECT pg_try_advisory'):
            self.result = [(True,)]
        elif normalized.startswith('SELECT day FROM'):
            self.result = [(day,) for day in self.database.days]
        elif normalized.startswith('SELECT COUNT(*), COALESCE'):
            self.result = [(11, 3)]
        elif normalized.startswith('SELECT COALESCE(SUM(count)'):
            self.result = [(2,)]
        elif normalized.startswith('SELECT MIN(day)'):
            self.result = [(min(self.database.days) if self.database.days else None,)]
        else:
            self.result = []

    def fetchone(self): return self.result[0] if self.result else None
    def fetchall(self): return self.result


class WriterCursor:
    def __init__(self, finalized):
        self.finalized = iter(finalized)
        self.calls = []
        self.result = None
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, params=None):
        normalized = ' '.join(sql.split())
        self.calls.append((normalized, params))
        if normalized.startswith('SELECT pg_advisory_xact_lock'):
            self.result = None
        elif normalized.startswith('SELECT EXISTS'):
            self.result = (next(self.finalized),)
        else:
            self.result = None
    def fetchone(self): return self.result


class WriterConnection:
    def __init__(self, cursor): self.value, self.commits = cursor, 0
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def cursor(self): return self.value
    def commit(self): self.commits += 1


class MaintenanceTests(unittest.TestCase):
    def test_completed_days_recompute_idempotently_with_utc_metrics(self):
        database = MaintenanceDatabase([date(2026, 11, 2), date(2026, 11, 3)])
        job = AnalyticsMaintenance('postgresql://private', connect=database.connect,
                                   now=lambda: NOW)
        self.assertEqual(job.run(), {'status':'completed', 'days':2})
        self.assertEqual(job.run(), {'status':'completed', 'days':2})
        sql = '\n'.join(call[0] for call in database.calls if isinstance(call[0], str))
        self.assertEqual(sql.count('DELETE FROM analytics_daily_metrics WHERE day=%s'), 4)
        for event in ('website_session_started', 'website_visit_started',
                      'website_page_viewed', 'product_card_activated', 'eyeball_opened'):
            self.assertIn(event, sql)
        self.assertIn("AT TIME ZONE 'UTC'", sql)
        self.assertIn('ON CONFLICT(day) DO UPDATE', sql)
        self.assertEqual(database.commits, 2)

    def test_old_days_finalize_before_detail_cleanup_and_sessions_get_grace(self):
        old = date(2026, 10, 1)
        database = MaintenanceDatabase([old])
        AnalyticsMaintenance('postgresql://private', connect=database.connect,
                             now=lambda: NOW).run()
        calls = database.calls
        day_upsert = next(call for call in calls
                          if isinstance(call[0], str)
                          and call[0].startswith('INSERT INTO analytics_aggregation_days'))
        self.assertEqual(day_upsert[1][-1], NOW)
        event_delete = next(call for call in calls
                            if isinstance(call[0], str)
                            and call[0].startswith('DELETE FROM analytics_events'))
        self.assertEqual(event_delete[1][0], datetime(2026, 10, 5, tzinfo=timezone.utc))
        session_delete = next(call for call in calls
                              if isinstance(call[0], str)
                              and call[0].startswith('DELETE FROM analytics_sessions'))
        self.assertEqual(session_delete[1][0], NOW - timedelta(days=30))
        self.assertTrue(any("INTERVAL '13 months'" in call[0] for call in calls
                            if isinstance(call[0], str)))

    def test_cross_midnight_is_grouped_by_event_utc_day_not_session_expiry(self):
        database = MaintenanceDatabase([date(2026, 11, 3)])
        AnalyticsMaintenance('postgresql://private', connect=database.connect,
                             now=lambda: NOW).run()
        aggregate = next(call[0] for call in database.calls
                         if isinstance(call[0], str)
                         and call[0].startswith('INSERT INTO analytics_daily_metrics'))
        self.assertGreaterEqual(aggregate.count("(occurred_at AT TIME ZONE 'UTC')::date"), 6)
        self.assertNotIn('expires_at', aggregate)

    def test_finalized_days_are_excluded_from_backfill_candidates(self):
        database = MaintenanceDatabase()
        AnalyticsMaintenance('postgresql://private', connect=database.connect,
                             now=lambda: NOW).run()
        candidates = next(call[0] for call in database.calls
                          if isinstance(call[0], str) and call[0].startswith('SELECT day FROM'))
        self.assertIn('finalized.finalized_at IS NOT NULL', candidates)

    def test_late_event_is_rejected_and_counted_without_silent_corruption(self):
        cursor = WriterCursor([True, False])
        connection = WriterConnection(cursor)
        writer = PsycopgAnalyticsWriter('postgresql://private', connect=lambda *a, **k: connection)
        events = [
            make_event('website_page_viewed', now=1793491200,
                       dimensions={'product':'oeswebsite','surface':'web','page':'home'}),
            make_event('website_page_viewed', now=1793577600,
                       dimensions={'product':'oeswebsite','surface':'web','page':'home'}),
        ]
        writer.write(events, Counter())
        self.assertIn('pg_advisory_xact_lock', cursor.calls[0][0])
        inserts = [call for call in cursor.calls
                   if call[0].startswith('INSERT INTO analytics_events')]
        self.assertEqual(len(inserts), 1)
        drop = next(call for call in cursor.calls
                    if call[0].startswith('INSERT INTO analytics_dropped_events'))
        self.assertEqual(drop[1][1:], ('late_after_finalization', 1))
        self.assertEqual(connection.commits, 1)

    def test_maintenance_is_disabled_by_default_and_failure_is_content_free(self):
        with patch.dict('os.environ', {}, clear=True), patch('builtins.print') as output:
            self.assertEqual(main(), 0)
            output.assert_called_once_with('Analytics maintenance disabled.')
        with patch.dict('os.environ', {
                'OES_ANALYTICS_MAINTENANCE_ENABLED':'true',
                'OES_ANALYTICS_DATABASE_URL':'postgresql://secret'}, clear=True), \
                patch('persistent_analytics.maintenance.AnalyticsMaintenance.run',
                      side_effect=RuntimeError('private')), \
                patch('persistent_analytics.maintenance.LOG.warning') as warning, \
                patch('builtins.print') as output:
            self.assertEqual(main(), 1)
            warning.assert_called_once_with(
                'analytics maintenance failed category=database_unavailable')
            self.assertNotIn('secret', repr(output.call_args_list))

    def test_earliest_available_date_is_recomputed_after_retention(self):
        database = MaintenanceDatabase([date(2026, 11, 3)])
        AnalyticsMaintenance('postgresql://private', connect=database.connect,
                             now=lambda: NOW).run()
        metadata = next(call for call in database.calls
                        if isinstance(call[0], str)
                        and call[0].startswith('INSERT INTO analytics_metadata'))
        self.assertEqual(metadata[1], ('2026-11-03',))
        self.assertIn('value=EXCLUDED.value', metadata[0])


if __name__ == '__main__':
    unittest.main()
