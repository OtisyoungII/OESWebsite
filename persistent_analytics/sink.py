"""Bounded, nonblocking persistence for already-validated telemetry events."""
import atexit
from collections import Counter
from datetime import datetime, timezone
import logging
import os
from queue import Empty, Full, Queue
import threading
import time
from uuid import UUID

from oes_telemetry import DIMENSIONS, validate_event
from .constants import MAINTENANCE_LOCK_ID
from .database import AnalyticsTarget
from .sessions import DisabledSessionStore, PsycopgSessionStore


LOG = logging.getLogger('oes.analytics')
DEFAULT_QUEUE_CAPACITY = 512
DEFAULT_BATCH_SIZE = 24
DROP_REASONS = frozenset({
    'queue_overflow', 'database_unavailable', 'shutdown', 'late_after_finalization'})
DIMENSION_COLUMNS = tuple(DIMENSIONS)
EVENT_COLUMNS = (
    'event_id', 'occurred_at', 'event_type', 'request_id', 'attempt', 'duration_ms',
    'outcome', 'reason', 'value', *DIMENSION_COLUMNS,
)
INSERT_SQL = f'''INSERT INTO analytics_events ({', '.join(EVENT_COLUMNS)})
    VALUES ({', '.join(['%s'] * len(EVENT_COLUMNS))})
    ON CONFLICT (event_id) DO NOTHING'''
DROP_SQL = '''INSERT INTO analytics_dropped_events(day, reason, count)
    VALUES(%s, %s, %s)
    ON CONFLICT(day, reason) DO UPDATE SET count=analytics_dropped_events.count+EXCLUDED.count'''


def enabled(value):
    return str(value).strip().lower() == 'true'


def event_row(event):
    """Validate again at the storage boundary and project fixed columns only."""
    event = validate_event(event)
    dimensions = event.get('dimensions', {})
    occurred_at = datetime.fromtimestamp(event['occurred_at'], timezone.utc)
    values = {
        'event_id': UUID(hex=event['event_id']),
        'occurred_at': occurred_at,
        'event_type': event['event_type'],
        'request_id': (UUID(hex=event['request_id']) if event.get('request_id') else None),
        'attempt': event.get('attempt'),
        'duration_ms': event.get('duration_ms'),
        'outcome': event.get('outcome'),
        'reason': event.get('reason'),
        'value': event.get('value'),
        **{key: dimensions.get(key) for key in DIMENSION_COLUMNS},
    }
    return tuple(values[column] for column in EVENT_COLUMNS)


class PsycopgAnalyticsWriter:
    """Small batch writer; connections exist only on the background thread."""
    def __init__(self, database_url, *, connect=None, target=None):
        self.database_url = database_url
        self._connect = connect
        self.target = target or AnalyticsTarget()

    def _connection(self):
        if self._connect is None:
            import psycopg
            self._connect = psycopg.connect
        kwargs = {'connect_timeout': 2}
        options = self.target.options()
        if options:
            kwargs['options'] = options
        return self._connect(self.database_url, **kwargs)

    def write(self, events, dropped):
        rows = [event_row(event) for event in events]
        with self._connection() as connection:
            with connection.cursor() as cursor:
                # Serialize the finalization boundary with offline maintenance.
                cursor.execute('SELECT pg_advisory_xact_lock(%s)',
                               (MAINTENANCE_LOCK_ID,))
                late = 0
                for row in rows:
                    cursor.execute(
                        "SELECT EXISTS(SELECT 1 FROM analytics_aggregation_days "
                        "WHERE day=(%s AT TIME ZONE 'UTC')::date AND finalized_at IS NOT NULL)",
                        (row[1],))
                    if cursor.fetchone() == (True,):
                        late += 1
                    else:
                        cursor.execute(INSERT_SQL, row)
                if late:
                    dropped = Counter(dropped)
                    dropped['late_after_finalization'] += late
                day = datetime.now(timezone.utc).date()
                for reason, count in dropped.items():
                    if reason not in DROP_REASONS or type(count) is not int or count <= 0:
                        raise ValueError('Invalid analytics drop count')
                    cursor.execute(DROP_SQL, (day, reason, count))
            connection.commit()


class DisabledAnalyticsSink:
    enabled = False
    dropped = 0

    def enqueue(self, event):
        return False

    def close(self, timeout=0):
        return True


class PersistentAnalyticsSink:
    """Best-effort bounded queue. It can lose data, never website availability."""
    enabled = True

    def __init__(self, writer, *, capacity=DEFAULT_QUEUE_CAPACITY,
                 batch_size=DEFAULT_BATCH_SIZE, retry_seconds=1.0, start=True):
        if type(capacity) is not int or capacity < 1:
            raise ValueError('Invalid analytics queue capacity')
        if type(batch_size) is not int or not 1 <= batch_size <= 24:
            raise ValueError('Invalid analytics batch size')
        self.writer = writer
        self.queue = Queue(maxsize=capacity)
        self.batch_size = batch_size
        self.retry_seconds = retry_seconds
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.lifecycle_lock = threading.Lock()
        self.pending_drops = Counter()
        self.dropped = 0
        self.thread = None
        if start:
            self.thread = threading.Thread(target=self._run, daemon=True,
                                           name='oes-persistent-analytics')
            self.thread.start()

    def _drop(self, reason, count=1):
        if reason not in DROP_REASONS:
            raise ValueError('Invalid analytics drop reason')
        with self.lock:
            self.pending_drops[reason] += count
            self.dropped += count

    def enqueue(self, event):
        try:
            validated = validate_event(event)
            with self.lifecycle_lock:
                if self.stop.is_set():
                    self._drop('shutdown')
                    return False
                self.queue.put_nowait(validated)
            return True
        except Full:
            self._drop('queue_overflow')
        except (TypeError, ValueError):
            # Invalid content never enters persistence and is not an operational drop.
            return False
        return False

    def _take_drops(self):
        with self.lock:
            result = Counter(self.pending_drops)
            self.pending_drops.clear()
            return result

    def _restore_drops(self, values):
        with self.lock:
            self.pending_drops.update(values)

    def _batch(self):
        events = []
        try:
            events.append(self.queue.get(timeout=0.25))
        except Empty:
            return events
        while len(events) < self.batch_size:
            try:
                events.append(self.queue.get_nowait())
            except Empty:
                break
        return events

    def _run(self):
        while True:
            events = self._batch()
            drops = self._take_drops()
            if not events and not drops:
                if self.stop.is_set() and self.queue.empty():
                    break
                continue
            try:
                self.writer.write(events, drops)
            except Exception:
                # Never log exception text, URLs, credentials, or event content.
                self._restore_drops(drops)
                if events:
                    self._drop('database_unavailable', len(events))
                LOG.warning('persistent analytics write failed category=database_unavailable')
                if self.stop.is_set():
                    break
                self.stop.wait(self.retry_seconds)
            finally:
                for _ in events:
                    self.queue.task_done()

    def close(self, timeout=2.0):
        with self.lifecycle_lock:
            self.stop.set()
        if self.thread is not None:
            self.thread.join(timeout=max(0, timeout))
            # The writer thread owns its queue until it exits. Never race it here.
            return not self.thread.is_alive()
        remaining = 0
        while True:
            try:
                self.queue.get_nowait()
                self.queue.task_done()
                remaining += 1
            except Empty:
                break
        if remaining:
            self._drop('shutdown', remaining)
        return True


def init_persistent_analytics(app):
    """Attach the optional sink without changing public startup availability."""
    for key, default in (
            ('OES_PERSISTENT_ANALYTICS_ENABLED', 'false'),
            ('OES_ANALYTICS_DATABASE_URL', ''),
            ('OES_ANALYTICS_SESSION_DIGEST_KEY', ''),
            ('OES_ANALYTICS_EXPECTED_DATABASE', ''),
            ('OES_ANALYTICS_SCHEMA', '')):
        app.config.setdefault(key, os.environ.get(key, default))
    sink = DisabledAnalyticsSink()
    sessions = DisabledSessionStore()
    if enabled(app.config['OES_PERSISTENT_ANALYTICS_ENABLED']):
        database_url = str(app.config['OES_ANALYTICS_DATABASE_URL']).strip()
        if database_url:
            try:
                target = AnalyticsTarget(
                    app.config['OES_ANALYTICS_EXPECTED_DATABASE'],
                    app.config['OES_ANALYTICS_SCHEMA'])
                if not target.isolated:
                    raise ValueError('Analytics database isolation is required')
                digest_key = str(app.config['OES_ANALYTICS_SESSION_DIGEST_KEY']).strip()
                candidate_sessions = PsycopgSessionStore(
                    database_url, digest_key, target=target)
                candidate_sink = PersistentAnalyticsSink(
                    PsycopgAnalyticsWriter(database_url, target=target))
                sessions, sink = candidate_sessions, candidate_sink
                atexit.register(sink.close)
            except Exception:
                LOG.warning('persistent analytics disabled category=initialization_failure')
        else:
            LOG.warning('persistent analytics disabled category=configuration_missing')
    app.extensions['persistent_analytics'] = sink
    app.extensions['persistent_analytics_sessions'] = sessions
    app.extensions['worker_relay'].persistent_analytics = sink
    return sink
