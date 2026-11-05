import time
import threading
import unittest
from unittest.mock import Mock, patch

from flask import Flask

from app import app as website_app
from chat.worker_relay import WorkerRelay
from oes_telemetry import make_event
from persistent_analytics.migration_runner import apply_migrations, discover_migrations
from persistent_analytics.database import AnalyticsTarget, connection_options
from persistent_analytics.sink import (
    DIMENSION_COLUMNS,
    DisabledAnalyticsSink,
    EVENT_COLUMNS,
    INSERT_SQL,
    PersistentAnalyticsSink,
    PsycopgAnalyticsWriter,
    event_row,
    init_persistent_analytics,
)


CONFIG = {
    'OES_CHAT_PROVIDER': 'outbound_worker',
    'OES_WORKER_ENABLED': 'true',
    'OES_WORKER_ID': 'test-worker',
    'OES_WORKER_KEY_ID': 'test-key',
    'OES_WORKER_SHARED_KEY': 'ab' * 32,
    'OES_AI_CHAT_ENABLED': 'true',
    'OES_EYEBALL_ENABLED': 'true',
    'OES_PROACTIVE_ENABLED': 'false',
}


class CapturingWriter:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []
        self.ids = set()

    def write(self, events, dropped):
        if self.fail:
            raise RuntimeError('private database detail')
        for event in events:
            self.ids.add(event['event_id'])
        self.calls.append((list(events), dict(dropped)))


def wait_for(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.01)
    return False


class SinkTests(unittest.TestCase):
    def test_disabled_by_default_and_missing_configuration_fails_closed(self):
        app = Flask(__name__)
        relay = Mock()
        app.extensions['worker_relay'] = relay
        sink = init_persistent_analytics(app)
        self.assertIsInstance(sink, DisabledAnalyticsSink)
        self.assertEqual(app.config['OES_PERSISTENT_ANALYTICS_ENABLED'], 'false')
        self.assertIs(relay.persistent_analytics, sink)

        app.config['OES_PERSISTENT_ANALYTICS_ENABLED'] = 'true'
        app.config['OES_ANALYTICS_DATABASE_URL'] = ''
        with self.assertLogs('oes.analytics', 'WARNING') as logs:
            sink = init_persistent_analytics(app)
        self.assertIsInstance(sink, DisabledAnalyticsSink)
        self.assertNotIn('postgresql://', '\n'.join(logs.output))

    def test_server_environment_can_enable_without_exposing_database_url(self):
        app = Flask(__name__)
        relay = Mock()
        app.extensions['worker_relay'] = relay
        writer = Mock()
        with patch.dict('os.environ', {
                'OES_PERSISTENT_ANALYTICS_ENABLED': 'true',
                'OES_ANALYTICS_DATABASE_URL': 'postgresql://private',
                'OES_ANALYTICS_EXPECTED_DATABASE': 'oes_website_analytics',
                'OES_ANALYTICS_SESSION_DIGEST_KEY': '12' * 32}, clear=False), \
                patch('persistent_analytics.sink.PsycopgAnalyticsWriter', return_value=writer), \
                patch('persistent_analytics.sink.PersistentAnalyticsSink') as sink_type, \
                patch('persistent_analytics.sink.PsycopgSessionStore') as session_type, \
                patch('persistent_analytics.sink.atexit.register') as register:
            sink_type.return_value = Mock(enabled=True)
            sink = init_persistent_analytics(app)
        self.assertIs(sink, sink_type.return_value)
        sink_type.assert_called_once_with(writer)
        session_type.assert_called_once_with(
            'postgresql://private', '12' * 32,
            target=AnalyticsTarget('oes_website_analytics'))
        register.assert_called_once_with(sink.close)
        self.assertIs(relay.persistent_analytics, sink)

    def test_graceful_close_flushes_queue_and_pending_drop_counts(self):
        writer = CapturingWriter()
        sink = PersistentAnalyticsSink(writer)
        sink._drop('queue_overflow', 2)
        self.assertTrue(sink.enqueue(make_event('request_accepted', outcome='accepted')))
        self.assertTrue(sink.close())
        self.assertTrue(any(len(events) == 1 and drops.get('queue_overflow') == 2
                            for events, drops in writer.calls))

    def test_enqueue_after_close_is_rejected_and_counted(self):
        sink = PersistentAnalyticsSink(CapturingWriter(), start=False)
        self.assertTrue(sink.close())
        self.assertFalse(sink.enqueue(make_event('request_accepted', outcome='accepted')))
        self.assertEqual(sink.pending_drops['shutdown'], 1)

    def test_close_never_drains_queue_while_writer_thread_is_alive(self):
        entered = threading.Event()
        release = threading.Event()

        class BlockingWriter:
            def write(self, events, dropped):
                entered.set()
                release.wait(2)

        sink = PersistentAnalyticsSink(BlockingWriter())
        sink.enqueue(make_event('request_accepted', outcome='accepted'))
        self.assertTrue(entered.wait(1))
        sink.enqueue(make_event('response_completed', outcome='success'))
        self.assertFalse(sink.close(timeout=.01))
        self.assertEqual(sink.queue.qsize(), 1)
        release.set()
        self.assertTrue(wait_for(lambda: not sink.thread.is_alive()))

    def test_relay_preserves_existing_buffer_and_copies_same_server_event(self):
        relay = WorkerRelay(CONFIG)
        sink = Mock()
        relay.persistent_analytics = sink
        self.assertTrue(relay.emit('request_accepted', outcome='accepted'))
        buffered = relay.telemetry.batch()
        self.assertEqual(len(buffered), 1)
        copied = sink.enqueue.call_args.args[0]
        self.assertEqual(copied['event_id'], buffered[0]['event_id'])
        self.assertEqual(copied, buffered[0])

    def test_sink_failure_never_breaks_existing_relay(self):
        relay = WorkerRelay(CONFIG)
        relay.persistent_analytics = Mock()
        relay.persistent_analytics.enqueue.side_effect = RuntimeError('private failure')
        self.assertTrue(relay.emit('request_accepted', outcome='accepted'))
        self.assertEqual(len(relay.telemetry.batch()), 1)

    def test_sink_outage_cannot_break_public_pages_or_health(self):
        relay = website_app.extensions['worker_relay']
        prior = relay.persistent_analytics
        broken = Mock()
        broken.enqueue.side_effect = RuntimeError('private database detail')
        relay.persistent_analytics = broken
        try:
            client = website_app.test_client()
            self.assertEqual(client.get('/healthz').status_code, 200)
            self.assertEqual(client.get('/').status_code, 200)
            self.assertTrue(relay.emit('request_accepted', outcome='accepted'))
        finally:
            relay.persistent_analytics = prior

    def test_fixed_projection_revalidates_and_has_no_free_text_columns(self):
        event = make_event('eyeball_opened', outcome='accepted', dimensions={
            'product': 'eyeball', 'surface': 'web', 'platform': 'mobile', 'language': 'en'})
        row = event_row(event)
        self.assertEqual(len(row), 9 + len(DIMENSION_COLUMNS))
        for forbidden in ('message', 'prompt', 'response', 'ip_address', 'user_agent',
                          'fingerprint', 'url', 'credential', 'secret'):
            self.assertNotIn(forbidden, EVENT_COLUMNS)
            with self.assertRaises(ValueError):
                event_row({**event, forbidden: 'private'})

    def test_queue_overflow_is_bounded_and_counted(self):
        sink = PersistentAnalyticsSink(CapturingWriter(), capacity=1, start=False)
        first = make_event('request_accepted', outcome='accepted')
        second = make_event('response_completed', outcome='success')
        self.assertTrue(sink.enqueue(first))
        self.assertFalse(sink.enqueue(second))
        self.assertEqual(sink.queue.qsize(), 1)
        self.assertEqual(sink.dropped, 1)
        self.assertEqual(sink.pending_drops['queue_overflow'], 1)
        sink.close()

    def test_database_outage_drops_batch_without_propagating_and_reports_after_recovery(self):
        writer = CapturingWriter(fail=True)
        sink = PersistentAnalyticsSink(writer, retry_seconds=.01)
        self.assertTrue(sink.enqueue(make_event('request_accepted', outcome='accepted')))
        self.assertTrue(wait_for(lambda: sink.dropped >= 1))
        self.assertEqual(sink.pending_drops['database_unavailable'], 1)
        writer.fail = False
        self.assertTrue(sink.enqueue(make_event('response_completed', outcome='success')))
        self.assertTrue(wait_for(lambda: any(call[1].get('database_unavailable') == 1
                                             for call in writer.calls)))
        self.assertTrue(sink.close())

    def test_duplicate_event_ids_are_idempotent_by_contract(self):
        event = make_event('request_accepted', outcome='accepted')
        writer = CapturingWriter()
        sink = PersistentAnalyticsSink(writer, start=False)
        sink.enqueue(event)
        sink.enqueue(event)
        events = [sink.queue.get_nowait(), sink.queue.get_nowait()]
        writer.write(events, {})
        self.assertEqual(writer.ids, {event['event_id']})
        self.assertIn('ON CONFLICT (event_id) DO NOTHING', INSERT_SQL)


class SchemaAndWriterTests(unittest.TestCase):
    def test_initial_schema_is_versioned_fixed_and_privacy_bounded(self):
        migrations = discover_migrations()
        self.assertEqual([migration.version for migration in migrations], [1, 2, 3, 4, 5])
        sql = migrations[0].sql.lower()
        for table in ('analytics_sessions', 'analytics_events', 'analytics_daily_metrics',
                      'analytics_metadata', 'analytics_dropped_events'):
            self.assertIn('create table if not exists ' + table, sql)
        self.assertIn('event_id uuid primary key', sql)
        self.assertIn('token_digest bytea', sql)
        for forbidden in ('raw_message', 'chat_text', 'ip_address', 'user_agent',
                          'browser_fingerprint', 'password', 'api_key'):
            self.assertNotIn(forbidden, sql)
        self.assertIn('add column if not exists page text', migrations[1].sql.lower())
        self.assertIn('analytics_aggregation_days', migrations[2].sql.lower())
        self.assertIn('late_after_finalization', migrations[2].sql.lower())
        self.assertIn('analytics_owner_sessions', migrations[3].sql.lower())

    def test_repeatable_migration_skips_matching_history(self):
        migrations = discover_migrations()

        class Cursor:
            def __init__(self): self.executed = []
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def execute(self, sql, params=None): self.executed.append((sql, params))
            def fetchall(self):
                return [(migration.version, migration.name, migration.checksum)
                        for migration in migrations]

        class Connection:
            def __init__(self): self.value = Cursor(); self.commits = 0
            def cursor(self): return self.value
            def commit(self): self.commits += 1

        connection = Connection()
        self.assertEqual(apply_migrations(connection), (1, 2, 3, 4, 5))
        self.assertEqual(connection.commits, 1)
        self.assertFalse(any(params and params[0] in {1, 2, 3, 4, 5}
                             for _, params in connection.value.executed))

    def test_database_target_isolation_is_strict_and_content_free(self):
        target = AnalyticsTarget('oes_scout', 'oes_website_analytics')
        self.assertEqual(
            connection_options(target.schema, 'statement_timeout=750'),
            '-c search_path=oes_website_analytics,pg_catalog -c statement_timeout=750')
        connection = Mock()
        connection.execute.return_value.fetchone.return_value = (
            'oes_scout', 'oes_website_analytics')
        target.verify(connection)
        connection.execute.return_value.fetchone.return_value = ('oes_scout', 'public')
        with self.assertRaisesRegex(RuntimeError, 'target mismatch'):
            target.verify(connection)
        for value in ('public', 'pg_catalog', 'bad-name', 'x;DROP TABLE scout'):
            with self.assertRaises(ValueError):
                AnalyticsTarget('oes_scout', value)

    def test_migration_history_checksum_mismatch_fails_closed(self):
        migration = discover_migrations()[0]

        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def execute(self, sql, params=None): pass
            def fetchall(self): return [(migration.version, migration.name, '0' * 64)]

        connection = Mock()
        connection.cursor.return_value = Cursor()
        with self.assertRaisesRegex(RuntimeError, 'history mismatch'):
            apply_migrations(connection)
        connection.commit.assert_not_called()

    def test_writer_uses_parameterized_fixed_rows_and_drop_upsert(self):
        operations = []

        class Cursor:
            def __init__(self): self.result = None
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def execute(self, sql, params):
                operations.append(('one', sql, params))
                self.result = ((False,) if sql.strip().startswith('SELECT EXISTS') else None)
            def fetchone(self): return self.result

        class Connection:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def cursor(self): return Cursor()
            def commit(self): operations.append(('commit',))

        connect = Mock(return_value=Connection())
        writer = PsycopgAnalyticsWriter('postgresql://private', connect=connect)
        writer.write([make_event('request_accepted', outcome='accepted')],
                     {'queue_overflow': 2})
        connect.assert_called_once_with('postgresql://private', connect_timeout=2)
        self.assertIn('pg_advisory_xact_lock', operations[0][1])
        self.assertEqual(operations[1][0], 'one')
        self.assertIn('SELECT EXISTS', operations[1][1])
        self.assertIn('INSERT INTO analytics_events', operations[2][1])
        self.assertEqual(operations[-1], ('commit',))
        rendered = repr(operations)
        self.assertNotIn('message', rendered)
        self.assertNotIn('ip_address', rendered)


if __name__ == '__main__':
    unittest.main()
