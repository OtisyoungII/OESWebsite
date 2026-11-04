from datetime import datetime, timezone
import threading
import unittest
from unittest.mock import Mock

from persistent_analytics.sessions import PsycopgSessionStore, SESSION_SECONDS, VISIT_SECONDS
from product_intelligence import ProductIntelligence


KEY = '12' * 32
TOKEN = 'ab' * 16


class SessionDatabase:
    """Strict transaction fixture for the fixed session SQL contract."""
    def __init__(self):
        self.rows = {}
        self.lock = threading.RLock()

    def connect(self, database_url, **kwargs):
        if database_url != 'postgresql://private':
            raise AssertionError('unexpected database destination')
        if kwargs != {'connect_timeout': 1, 'options': '-c statement_timeout=750'}:
            raise AssertionError('unbounded connection settings')
        return SessionConnection(self)


class SessionConnection:
    def __init__(self, database):
        self.database = database

    def __enter__(self):
        self.database.lock.acquire()
        return self

    def __exit__(self, *args):
        self.database.lock.release()
        return False

    def cursor(self):
        return SessionCursor(self.database)

    def commit(self):
        return None


class SessionCursor:
    def __init__(self, database):
        self.database = database
        self.result = None

    def __enter__(self): return self
    def __exit__(self, *args): return False

    def execute(self, sql, params):
        normalized = ' '.join(sql.split())
        if normalized.startswith('SELECT id, expires_at, last_seen_at'):
            row = self.database.rows.get(params[0])
            self.result = ((row['id'], row['expires_at'], row['last_seen_at'])
                           if row else None)
        elif normalized.startswith('INSERT INTO analytics_sessions'):
            identifier, digest, started, last_seen, expires = params
            if digest in self.database.rows:
                self.result = None
            else:
                self.database.rows[digest] = {
                    'id': identifier, 'started_at': started, 'last_seen_at': last_seen,
                    'expires_at': expires, 'event_count': 0, 'visit_count': 1,
                }
                self.result = (identifier,)
        elif normalized.startswith('UPDATE analytics_sessions SET id='):
            identifier, started, last_seen, expires, digest = params
            self.database.rows[digest].update({
                'id': identifier, 'started_at': started, 'last_seen_at': last_seen,
                'expires_at': expires, 'event_count': 0, 'visit_count': 1,
            })
            self.result = None
        elif normalized.startswith('UPDATE analytics_sessions SET last_seen_at='):
            last_seen, expires, increment, digest = params
            self.database.rows[digest]['last_seen_at'] = last_seen
            self.database.rows[digest]['expires_at'] = expires
            self.database.rows[digest]['visit_count'] += increment
            self.result = None
        else:
            raise AssertionError('unexpected session SQL')

    def fetchone(self):
        return self.result


class Clock:
    def __init__(self, value=1800000000): self.value = value
    def __call__(self): return self.value


class PersistentSessionTests(unittest.TestCase):
    def setUp(self):
        self.database = SessionDatabase()
        self.store = PsycopgSessionStore(
            'postgresql://private', KEY, connect=self.database.connect)
        self.now = 1800000000

    def row(self):
        return next(iter(self.database.rows.values()))

    def test_raw_cookie_is_never_stored_and_restart_continuity_survives(self):
        first = self.store.open(TOKEN, self.now)
        restarted = PsycopgSessionStore(
            'postgresql://private', KEY, connect=self.database.connect)
        second = restarted.open(TOKEN, self.now + 10)
        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.token, TOKEN)
        self.assertEqual(second.token, TOKEN)
        self.assertNotIn(TOKEN, repr(self.database.rows))
        self.assertEqual(next(iter(self.database.rows)), self.store.digest(TOKEN))

    def test_product_tracker_restart_does_not_repeat_session_started(self):
        first_emit = Mock()
        first = ProductIntelligence(first_emit, clock=Clock(self.now), session_store=self.store)
        token, created, _, _ = first.open_session(TOKEN)
        self.assertTrue(created)
        self.assertTrue(first.record(token, {
            'event':'website_session_started',
            'dimensions':{'platform':'desktop', 'language':'en'}}))

        second_emit = Mock()
        restarted = ProductIntelligence(
            second_emit, clock=Clock(self.now + 10), session_store=self.store)
        token, created, count, visit = restarted.open_session(TOKEN)
        self.assertFalse(created)
        self.assertFalse(visit)
        self.assertEqual(count, 1)
        self.assertFalse(restarted.record(token, {
            'event':'website_session_started',
            'dimensions':{'platform':'desktop', 'language':'en'}}))
        second_emit.assert_not_called()

    def test_sliding_lifetime_and_expiration_create_new_session(self):
        first = self.store.open(TOKEN, self.now)
        original_id = self.row()['id']
        active = self.store.open(TOKEN, self.now + SESSION_SECONDS - 1)
        self.assertFalse(active.created)
        self.assertEqual(self.row()['expires_at'], datetime.fromtimestamp(
            self.now + SESSION_SECONDS - 1 + SESSION_SECONDS, timezone.utc))
        expired = self.store.open(TOKEN, self.now + 2 * SESSION_SECONDS)
        self.assertTrue(expired.created)
        self.assertNotEqual(self.row()['id'], original_id)
        self.assertEqual(self.row()['visit_count'], 1)

    def test_concurrent_visit_boundary_counts_exactly_once(self):
        self.store.open(TOKEN, self.now)
        results = []

        def open_session():
            results.append(self.store.open(TOKEN, self.now + VISIT_SECONDS + 1))

        threads = [threading.Thread(target=open_session) for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(sum(result.visit_started for result in results), 1)
        self.assertEqual(self.row()['visit_count'], 2)

    def test_concurrent_initial_token_creates_one_session(self):
        results = []
        threads = [threading.Thread(
            target=lambda: results.append(self.store.open(TOKEN, self.now)))
            for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(sum(result.created for result in results), 1)
        self.assertEqual(len(self.database.rows), 1)

    def test_database_outage_preserves_valid_cookie_and_public_fallback(self):
        backend = Mock(enabled=True)
        backend.open.side_effect = RuntimeError('private database outage')
        tracker = ProductIntelligence(Mock(), clock=Clock(self.now), session_store=backend)
        token, created, count, visit = tracker.open_session(TOKEN)
        self.assertEqual(token, TOKEN)
        self.assertTrue(created)
        self.assertTrue(visit)
        self.assertEqual(count, 1)

    def test_invalid_digest_key_is_rejected_without_echoing_it(self):
        with self.assertRaisesRegex(ValueError, '^Invalid analytics session digest key$'):
            PsycopgSessionStore('postgresql://private', 'private-secret')


if __name__ == '__main__':
    unittest.main()
