"""Real PostgreSQL acceptance tests; skipped without an explicit disposable URL."""
from datetime import date, datetime, timedelta, timezone
import os
import threading
import time
import unittest
from uuid import UUID

from oes_telemetry import make_event
from persistent_analytics.maintenance import AnalyticsMaintenance, MAINTENANCE_LOCK_ID
from persistent_analytics.migration_runner import apply_migrations
from persistent_analytics.sessions import PsycopgSessionStore, SESSION_SECONDS, VISIT_SECONDS
from persistent_analytics.sink import PersistentAnalyticsSink, PsycopgAnalyticsWriter
from owner_analytics.auth import OwnerAuthStore, SESSION_SECONDS as OWNER_SESSION_SECONDS


DATABASE_URL = os.environ.get('OES_ANALYTICS_TEST_DATABASE_URL', '').strip()
DIGEST_KEY = '12' * 32
TOKEN = 'ab' * 16


@unittest.skipUnless(DATABASE_URL, 'disposable PostgreSQL URL not configured')
class PostgreSQLAnalyticsIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.psycopg = psycopg
        with psycopg.connect(DATABASE_URL) as connection:
            apply_migrations(connection)

    def setUp(self):
        with self.psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'TRUNCATE analytics_events, analytics_sessions, '
                    'analytics_daily_metrics, analytics_dropped_events, '
                    'analytics_aggregation_days, analytics_metadata, analytics_owner_sessions')
                cursor.execute(
                    "UPDATE analytics_owner_auth_state SET last_totp_counter=-1 "
                    "WHERE owner_id='owner'")
            connection.commit()

    def scalar(self, sql, params=None):
        with self.psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()[0]

    def test_real_migrations_are_repeatable_and_complete(self):
        with self.psycopg.connect(DATABASE_URL) as connection:
            self.assertEqual(apply_migrations(connection), (1, 2, 3, 4))
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM analytics_schema_migrations'), 4)
        self.assertEqual(self.scalar(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' "
            "AND table_name IN ('analytics_sessions','analytics_events',"
            "'analytics_daily_metrics','analytics_dropped_events',"
            "'analytics_aggregation_days','analytics_metadata','analytics_owner_sessions',"
            "'analytics_owner_auth_state')"), 8)
        with self.psycopg.connect(DATABASE_URL) as connection:
            privileges = connection.execute(
                'SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication '
                'FROM pg_roles WHERE rolname=current_user').fetchone()
        self.assertEqual(privileges, (False, False, False, False))

    def test_migration_history_failure_rolls_back_without_schema_damage(self):
        with self.psycopg.connect(DATABASE_URL) as connection:
            original = connection.execute(
                'SELECT checksum FROM analytics_schema_migrations WHERE version=4').fetchone()[0]
            connection.execute(
                "UPDATE analytics_schema_migrations SET checksum=%s WHERE version=4",
                ('0' * 64,))
            with self.assertRaisesRegex(RuntimeError, 'history mismatch'):
                apply_migrations(connection)
            connection.rollback()
        self.assertEqual(self.scalar(
            'SELECT checksum FROM analytics_schema_migrations WHERE version=4'), original)
        self.assertEqual(self.scalar(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name="
            "'analytics_owner_sessions'"), 1)

    def test_actual_insert_and_duplicate_event_id_are_idempotent(self):
        writer = PsycopgAnalyticsWriter(DATABASE_URL)
        event = make_event('website_page_viewed', now=1793743200,
                           dimensions={'product':'oeswebsite','surface':'web','page':'home'})
        writer.write([event], {})
        writer.write([event], {})
        self.assertEqual(self.scalar(
            'SELECT COUNT(*) FROM analytics_events WHERE event_id=%s',
            (UUID(event['event_id']),)), 1)

    def test_session_restart_expiration_and_concurrent_visit_boundary(self):
        start = 1793743200
        first = PsycopgSessionStore(DATABASE_URL, DIGEST_KEY)
        self.assertTrue(first.open(TOKEN, start).created)
        restarted = PsycopgSessionStore(DATABASE_URL, DIGEST_KEY)
        self.assertFalse(restarted.open(TOKEN, start + 10).created)
        results = []
        threads = [threading.Thread(
            target=lambda: results.append(restarted.open(
                TOKEN, start + VISIT_SECONDS + 11))) for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(sum(result.visit_started for result in results), 1)
        self.assertEqual(self.scalar('SELECT visit_count FROM analytics_sessions'), 2)
        expired = restarted.open(TOKEN, start + VISIT_SECONDS + 11 + SESSION_SECONDS + 1)
        self.assertTrue(expired.created)
        self.assertEqual(self.scalar('SELECT visit_count FROM analytics_sessions'), 1)

    def test_writer_and_finalizer_use_one_real_advisory_lock(self):
        blocker = self.psycopg.connect(DATABASE_URL)
        blocker.execute('SELECT pg_advisory_xact_lock(%s)', (MAINTENANCE_LOCK_ID,))
        completed = threading.Event()
        writer = PsycopgAnalyticsWriter(DATABASE_URL)
        event = make_event('request_accepted', outcome='accepted', now=1793743200)
        thread = threading.Thread(target=lambda: (writer.write([event], {}), completed.set()))
        thread.start()
        time.sleep(.2)
        self.assertFalse(completed.is_set())
        blocker.commit()
        blocker.close()
        thread.join(3)
        self.assertTrue(completed.is_set())
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM analytics_events'), 1)

    def test_daily_utc_aggregation_finalization_late_event_and_retention(self):
        now = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
        writer = PsycopgAnalyticsWriter(DATABASE_URL)
        day = datetime(2026, 11, 3, tzinfo=timezone.utc)
        events = [
            make_event('website_session_started', now=day.timestamp() + 86390,
                       dimensions={'product':'oeswebsite','surface':'web',
                                   'platform':'desktop','language':'en'}),
            make_event('website_visit_started', now=day.timestamp() + 86391,
                       dimensions={'product':'oeswebsite','surface':'web',
                                   'platform':'desktop','language':'en'}),
            make_event('website_page_viewed', now=day.timestamp() + 86392,
                       dimensions={'product':'oeswebsite','surface':'web','page':'home'}),
            make_event('product_card_activated', now=day.timestamp() + 86393,
                       dimensions={'product':'oeswebsite','surface':'web',
                                   'product_target':'sportfolio'}),
            make_event('eyeball_opened', now=(day + timedelta(days=1)).timestamp() + 2,
                       dimensions={'product':'eyeball','surface':'web',
                                   'platform':'desktop','language':'en'}),
            make_event('telemetry_gap', now=day.timestamp() + 86394,
                       reason='buffer_overflow', value=3),
        ]
        writer.write(events, {})
        with self.psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "INSERT INTO analytics_dropped_events(day,reason,count) "
                "VALUES(%s,'queue_overflow',2)", (date(2026, 11, 3),))
            connection.commit()
        job = AnalyticsMaintenance(DATABASE_URL, now=lambda: now)
        self.assertEqual(job.run()['status'], 'completed')
        with self.psycopg.connect(DATABASE_URL) as connection:
            rows = dict(connection.execute(
                'SELECT metric,count FROM analytics_daily_metrics WHERE day=%s',
                (date(2026, 11, 3),)).fetchall())
        self.assertEqual(rows, {
            'sessions':1, 'visits':1, 'page_views':1, 'product_activations':1,
            'eyeball_interactions':0, 'response_successes':0, 'safe_errors':0,
            'cancelled_requests':0, 'response_latency':0,
            'analytics_drops':2, 'telemetry_gaps':3})
        self.assertEqual(self.scalar(
            "SELECT count FROM analytics_daily_metrics WHERE day=%s "
            "AND metric='eyeball_interactions'", (date(2026, 11, 4),)), 1)

        old_day = date(2026, 9, 1)
        old_time = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)
        old_event = make_event('website_page_viewed', now=old_time.timestamp(),
                               dimensions={'product':'oeswebsite','surface':'web','page':'home'})
        writer.write([old_event], {})
        self.assertEqual(job.run()['status'], 'completed')
        self.assertIsNotNone(self.scalar(
            'SELECT finalized_at FROM analytics_aggregation_days WHERE day=%s', (old_day,)))
        self.assertEqual(self.scalar(
            'SELECT COUNT(*) FROM analytics_events WHERE occurred_at::date=%s', (old_day,)), 0)
        writer.write([make_event('website_page_viewed', now=old_time.timestamp() + 1,
                                 dimensions={'product':'oeswebsite','surface':'web',
                                             'page':'home'})], {})
        self.assertEqual(self.scalar(
            "SELECT count FROM analytics_dropped_events "
            "WHERE reason='late_after_finalization'"), 1)
        self.assertEqual(self.scalar(
            "SELECT count FROM analytics_daily_metrics WHERE day=%s AND metric='page_views'",
            (old_day,)), 1)

        with self.psycopg.connect(DATABASE_URL) as connection:
            connection.execute(
                "INSERT INTO analytics_daily_metrics(day,metric,count) "
                "VALUES(DATE '2025-01-01','sessions',1)")
            connection.execute(
                "INSERT INTO analytics_aggregation_days "
                "(day,source_event_count,source_drop_count,telemetry_gap_count,"
                "aggregated_at,finalized_at) VALUES(DATE '2025-01-01',0,0,0,%s,%s)",
                (now, now))
            connection.execute(
                "INSERT INTO analytics_sessions "
                "(id,token_digest,started_at,last_seen_at,expires_at,event_count,visit_count) "
                "VALUES(gen_random_uuid(),decode('01','hex'),%s,%s,%s,0,1),"
                "(gen_random_uuid(),decode('02','hex'),%s,%s,%s,0,1)",
                (now - timedelta(days=50), now - timedelta(days=40), now - timedelta(days=31),
                 now - timedelta(days=40), now - timedelta(days=30), now - timedelta(days=29)))
            connection.commit()
        job.run()
        self.assertEqual(self.scalar(
            "SELECT COUNT(*) FROM analytics_daily_metrics WHERE day=DATE '2025-01-01'"), 0)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM analytics_sessions'), 1)

    def test_privacy_schema_and_values_exclude_forbidden_content(self):
        store = PsycopgSessionStore(DATABASE_URL, DIGEST_KEY)
        store.open(TOKEN, 1793743200)
        self.assertNotEqual(self.scalar(
            'SELECT encode(token_digest,\'hex\') FROM analytics_sessions'), TOKEN)
        columns = self.scalar(
            "SELECT string_agg(column_name,',') FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name LIKE 'analytics_%'")
        for forbidden in ('ip_address', 'user_agent', 'chat', 'message', 'password', 'secret'):
            self.assertNotIn(forbidden, columns)
        with self.assertRaises(ValueError):
            make_event('website_page_viewed', dimensions={'message':'private chat content'})

    def test_database_outage_recovery_public_health_and_drop_accounting(self):
        from app import app
        unavailable = 'postgresql://127.0.0.1:1/oes_analytics_unavailable'
        writer = PsycopgAnalyticsWriter(unavailable)
        sink = PersistentAnalyticsSink(writer, retry_seconds=.05)
        event = make_event('request_accepted', outcome='accepted')
        self.assertTrue(sink.enqueue(event))
        deadline = time.time() + 3
        while sink.dropped < 1 and time.time() < deadline:
            time.sleep(.02)
        self.assertGreaterEqual(sink.dropped, 1)
        with app.test_client() as client:
            self.assertEqual(client.get('/').status_code, 200)
            self.assertEqual(client.get('/healthz').status_code, 200)
        writer.database_url = DATABASE_URL
        deadline = time.time() + 3
        while self.scalar(
                "SELECT COALESCE(SUM(count),0) FROM analytics_dropped_events "
                "WHERE reason='database_unavailable'") < 1 and time.time() < deadline:
            time.sleep(.05)
        self.assertGreaterEqual(self.scalar(
            "SELECT SUM(count) FROM analytics_dropped_events "
            "WHERE reason='database_unavailable'"), 1)
        self.assertTrue(sink.close())
        before = sink.dropped
        self.assertFalse(sink.enqueue(make_event('request_accepted', outcome='accepted')))
        self.assertEqual(sink.dropped, before + 1)

        graceful = PersistentAnalyticsSink(PsycopgAnalyticsWriter(DATABASE_URL))
        completed = make_event('response_completed', outcome='success')
        self.assertTrue(graceful.enqueue(completed))
        self.assertTrue(graceful.close())
        self.assertEqual(self.scalar(
            'SELECT COUNT(*) FROM analytics_events WHERE event_id=%s',
            (UUID(completed['event_id']),)), 1)

    def test_owner_session_creation_uses_only_token_and_csrf_digests(self):
        current = [datetime(2026, 11, 4, 12, tzinfo=timezone.utc)]
        store = OwnerAuthStore(DATABASE_URL, 'owner-test-session-secret-' + 'x' * 24,
                               now=lambda: current[0])
        session = store.create()
        self.assertTrue(store.validate(session.token, session.csrf, touch=False))
        with self.psycopg.connect(DATABASE_URL) as connection:
            row = connection.execute(
                'SELECT token_digest,csrf_digest FROM analytics_owner_sessions').fetchone()
        self.assertEqual(row[0], store.digest(session.token))
        self.assertEqual(row[1], store.digest(session.csrf))
        rendered = repr(row)
        self.assertNotIn(session.token, rendered)
        self.assertNotIn(session.csrf, rendered)

    def test_owner_session_idle_and_absolute_expiry_fail_closed(self):
        current = [datetime(2026, 11, 4, 12, tzinfo=timezone.utc)]
        store = OwnerAuthStore(DATABASE_URL, 'owner-test-session-secret-' + 'x' * 24,
                               now=lambda: current[0])
        idle = store.create()
        current[0] += timedelta(seconds=OWNER_SESSION_SECONDS + 1)
        self.assertFalse(store.validate(idle.token))
        current[0] = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
        absolute = store.create()
        for _ in range(15):
            current[0] += timedelta(minutes=29)
            store.validate(absolute.token)
        current[0] = datetime(2026, 11, 4, 20, tzinfo=timezone.utc)
        self.assertFalse(store.validate(absolute.token))

    def test_owner_session_revocation_is_immediate(self):
        store = OwnerAuthStore(DATABASE_URL, 'owner-test-session-secret-' + 'x' * 24)
        session = store.create()
        self.assertTrue(store.validate(session.token, touch=False))
        store.delete(session.token)
        self.assertFalse(store.validate(session.token, touch=False))
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM analytics_owner_sessions'), 0)

    def test_totp_counter_replay_is_atomic_across_connections(self):
        store = OwnerAuthStore(DATABASE_URL, 'owner-test-session-secret-' + 'x' * 24)
        results = []
        threads = [threading.Thread(target=lambda: results.append(store.consume_totp(12345)))
                   for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(sum(results), 1)
        self.assertFalse(store.consume_totp(12345))
        self.assertFalse(store.consume_totp(12344))
        self.assertTrue(store.consume_totp(12346))

    def test_csrf_digest_must_match_owning_owner_session(self):
        store = OwnerAuthStore(DATABASE_URL, 'owner-test-session-secret-' + 'x' * 24)
        first, second = store.create(), store.create()
        self.assertTrue(store.validate(first.token, first.csrf, touch=False))
        self.assertFalse(store.validate(first.token, second.csrf, touch=False))
        self.assertFalse(store.validate('invalid-token', first.csrf, touch=False))


if __name__ == '__main__':
    unittest.main()
