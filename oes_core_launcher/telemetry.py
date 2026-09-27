"""Bounded local SQLite telemetry store and content-free console projections."""
from datetime import datetime, timezone
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import threading
import time

from oes_telemetry import (DIMENSIONS, REASONS, iso_day, make_event, validate_batch,
                           validate_event)
from .config import local_data_dir

RETENTION_SECONDS = 30 * 24 * 60 * 60
DATABASE_CEILING = 50 * 1024 * 1024
RUNTIME_KEYS = frozenset({'last_relay_contact', 'worker_started_at', 'core_started_at',
                          'active_inference', 'last_inference_success', 'last_failure_at'})

ACTIVITY_LABELS = {
    'request_accepted': 'Request received',
    'request_rejected': 'Request rejected',
    'situation_classified': 'Request classified',
    'grounding_required': 'Grounding required',
    'capability_requested': 'Capability requested',
    'capability_completed': 'Capability completed',
    'worker_job_dispatched': 'Worker job dispatched',
    'inference_attempted': 'Inference started',
    'inference_completed': 'Inference completed',
    'inference_failed': 'Inference failed',
    'validation_rejected': 'Response validation rejected',
    'correction_attempted': 'Correction attempted',
    'response_completed': 'Response stream completed',
    'safe_error': 'SAFE_ERROR returned',
    'request_cancelled': 'Request cancelled',
    'worker_connected': 'Worker connected',
    'worker_connection_failed': 'Worker connection failed',
    'worker_disconnected': 'Worker disconnected',
    'worker_recovered': 'Worker recovered',
    'ollama_state': 'Ollama state changed',
    'model_verified': 'Model verification changed',
    'core_started': 'OES Core started',
    'core_stopped': 'OES Core stopped',
    'core_restarted': 'OES Core restarted',
    'configuration_checked': 'Configuration checked',
    'telemetry_gap': 'Telemetry gap detected',
}

AUDIT_TYPES = frozenset({
    'capability_requested', 'capability_completed', 'grounding_required',
    'validation_rejected', 'correction_attempted', 'safe_error',
    'worker_connected', 'worker_connection_failed', 'worker_disconnected',
    'worker_recovered', 'core_started', 'core_stopped', 'core_restarted',
    'model_verified', 'configuration_checked', 'telemetry_gap',
})

TAB_METRICS = {
    'Overview': (
        ('telemetry_start', 'Telemetry since'), ('gap', 'Telemetry gaps'),
        ('requests', 'Accepted requests'), ('responses', 'Completed response streams'),
        ('safe_errors', 'SAFE_ERROR'), ('lookups', 'Public lookups'),
        ('latency', 'Latency p50 / p95'), ('last_inference', 'Last successful inference'),
        ('active_job', 'Active inference'), ('last_failure', 'Last failure/recovery')),
    'Eyeball': (
        ('visitor_sessions', 'Visitor sessions'), ('conversations', 'Conversations'),
        ('new_returning', 'New / returning'), ('turns', 'Accepted requests / turns'),
        ('eyeball_responses', 'Completed streams'), ('eyeball_safe', 'SAFE_ERROR'),
        ('attempts', 'Inference attempts'), ('corrections', 'Correction attempts'),
        ('capabilities', 'Capability invocations'),
        ('lookup_outcomes', 'Public lookup success / failure'),
        ('grounding', 'Grounding events'),
        ('eyeball_latency', 'Latency p50 / p95 / samples'),
        ('busiest', 'Busiest period')),
    'Health': (
        ('health_core', 'Core / worker / relay'), ('health_ollama', 'Ollama / model'),
        ('relay_contact', 'Last authenticated relay contact'),
        ('heartbeat_age', 'Relay contact age'), ('health_active', 'Active inference'),
        ('inference_outcomes', 'Inference success / failure'),
        ('health_failures', 'Timeout / cancellation / protocol failures'),
        ('provider_health', 'Public lookup success / failure'),
        ('uptime', 'Core / worker uptime'),
        ('health_latency', 'Latency p50 / p95 / samples')),
}


def _when(value):
    return (datetime.fromtimestamp(value).astimezone().strftime('%Y-%m-%d %H:%M:%S')
            if value else 'Not yet recorded')


def _status_value(value, allowed, fallback='Unknown'):
    return value if value in allowed else fallback


def _status_view(status):
    core = _status_value(status.core, {'Starting', 'Online', 'Needs Attention', 'Stopped'})
    worker = _status_value(status.worker, {'Starting', 'Running', 'Stopped'})
    relay = _status_value(status.relay,
                          {'Connecting', 'Connected', 'Reconnecting', 'Disconnected', 'Unknown'})
    ollama, model = 'Unknown', 'Unknown'
    if status.ollama == 'Unavailable':
        ollama, model = 'Unavailable', 'Unknown'
    elif status.ollama == 'Available; llama3.2 loaded':
        ollama, model = 'Available', 'llama3.2 loaded'
    elif status.ollama == 'Available; llama3.2 unloaded':
        ollama, model = 'Available', 'llama3.2 unloaded'
    elif status.ollama == 'Available; required model or digest missing':
        ollama, model = 'Available', 'Required model unavailable'
    return {'Core': core, 'Worker': worker, 'Ollama': ollama,
            'Model': model, 'Relay': relay}


def console_view(snapshot, status):
    """Build the only copyable/UI projection from bounded, validated telemetry."""
    count = lambda key: snapshot['metrics'].get(key, {}).get('count', 0)
    latency = snapshot['latency']
    if latency['p50_ms'] is not None:
        latency_text = f"{latency['p50_ms']} / {latency['p95_ms']} ms"
    elif latency['average_ms'] is not None:
        latency_text = f"{latency['average_ms']} ms average"
    else:
        latency_text = 'Insufficient samples'
    runtime, now = snapshot['runtime'], snapshot['generated_at']
    failures = [event for event in snapshot['events'] if event['event_type'] in
                ('inference_failed', 'worker_recovered', 'safe_error')]
    busiest = snapshot['busiest_period']
    contact = runtime.get('last_relay_contact')
    core_up = max(0, now-runtime['core_started_at']) if runtime.get('core_started_at') else None
    worker_up = max(0, now-runtime['worker_started_at']) if runtime.get('worker_started_at') else None
    failure_total = sum(value['count'] for key, value in snapshot['metrics'].items()
                        if ':reason:' in key and any(word in key for word in
                        ('timeout', 'cancellation', 'protocol', 'incomplete')))
    status_values = _status_view(status)
    values = {
        'telemetry_start': _when(snapshot['telemetry_started_at']),
        'gap': snapshot['telemetry_gaps'], 'requests': count('request_accepted'),
        'responses': count('response_completed'), 'safe_errors': count('safe_error'),
        'lookups': count('capability_requested:capability:public_world_lookup'),
        'latency': latency_text,
        'last_inference': _when(runtime.get('last_inference_success')),
        'active_job': 'Active' if runtime.get('active_inference') else 'Idle',
        'last_failure': activity_text(failures[0]) if failures else 'None recorded',
        'visitor_sessions': 'Not measured', 'conversations': 'Not measured',
        'new_returning': 'Not measured', 'turns': count('request_accepted'),
        'eyeball_responses': count('response_completed'),
        'eyeball_safe': count('safe_error'), 'attempts': count('inference_attempted'),
        'corrections': count('correction_attempted'),
        'capabilities': count('capability_requested'),
        'lookup_outcomes': (f"{count('capability_completed:success')} / "
                            f"{count('capability_completed:failure')}"),
        'grounding': count('grounding_required'),
        'eyeball_latency': f"{latency_text} / {latency['samples']} samples",
        'busiest': (f"{busiest['period_utc']} UTC · {busiest['count']} requests"
                    if busiest else 'Not available for this range'),
        'health_core': f"{status_values['Core']} / {status_values['Worker']} / {status_values['Relay']}",
        'health_ollama': f"{status_values['Ollama']}; {status_values['Model']}",
        'relay_contact': _when(contact),
        'heartbeat_age': f"{max(0, now-contact)} s" if contact else 'Unknown',
        'health_active': 'Active' if runtime.get('active_inference') else 'Idle',
        'inference_outcomes': f"{count('inference_completed')} / {count('inference_failed')}",
        'health_failures': failure_total,
        'provider_health': (f"{count('capability_completed:success')} / "
                            f"{count('capability_completed:failure')}"),
        'uptime': f"{core_up or 0} s / {worker_up or 0} s",
        'health_latency': f"{latency_text} / {latency['samples']} samples",
    }
    rows = lambda tab: [(label, str(values[key])) for key, label in TAB_METRICS[tab]]
    event_rows = [(_when(event['occurred_at']), activity_text(event))
                  for event in snapshot['events'][:100]]
    audit_rows = [row for event, row in zip(snapshot['events'][:100], event_rows)
                  if event['event_type'] in AUDIT_TYPES]
    return {'range': snapshot['range'], 'status': status_values, 'values': values,
            'Overview': rows('Overview'), 'Eyeball': rows('Eyeball'),
            'Health': rows('Health'), 'Activity': event_rows, 'Audit': audit_rows}


def format_tab(view, tab):
    if tab not in ('Overview', 'Eyeball', 'Health', 'Activity', 'Audit'):
        raise ValueError('Invalid console tab')
    lines = [tab.upper()]
    rows = view[tab]
    if tab in ('Activity', 'Audit'):
        lines.extend(f'{stamp} — {text}' for stamp, text in rows[:100])
        if not rows:
            lines.append('No events recorded')
    else:
        lines.extend(f'{label}: {value}' for label, value in rows)
    return '\n'.join(lines)


def format_diagnostics(view):
    range_label = {'today':'Today', '7 days':'7 Days', '30 days':'30 Days',
                   'all time':'All Time'}[view['range']]
    lines = ['OES CORE DIAGNOSTICS', f'Range: {range_label}', '', 'STATUS']
    lines.extend(f'{label}: {value}' for label, value in view['status'].items())
    for tab in ('Overview', 'Eyeball', 'Health'):
        lines.extend(('', format_tab(view, tab)))
    lines.extend(('', 'RECENT ACTIVITY'))
    lines.extend(f'{stamp} — {text}' for stamp, text in view['Activity'][:20])
    if not view['Activity']:
        lines.append('No events recorded')
    lines.extend(('', 'RECENT AUDIT'))
    lines.extend(f'{stamp} — {text}' for stamp, text in view['Audit'][:20])
    if not view['Audit']:
        lines.append('No events recorded')
    return '\n'.join(lines)


def copy_text(clipboard, text):
    """Best-effort clipboard write; operational control must never depend on it."""
    try:
        clipboard.clipboard_clear()
        clipboard.clipboard_append(text)
        clipboard.update_idletasks()
        return True
    except Exception:
        return False


def default_path():
    return local_data_dir() / 'telemetry.db'


def _metric_keys(event):
    keys = [event['event_type']]
    if event.get('outcome'):
        keys.append(f"{event['event_type']}:{event['outcome']}")
    if event.get('reason'):
        keys.append(f"{event['event_type']}:reason:{event['reason']}")
    for key, value in event.get('dimensions', {}).items():
        keys.append(f"{event['event_type']}:{key}:{value}")
    return keys


class TelemetryStore:
    def __init__(self, path=None, *, now=time.time, ceiling=DATABASE_CEILING):
        self.path = Path(path) if path else default_path()
        self.now, self.ceiling = now, ceiling
        self.lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self, readonly=False):
        if readonly:
            connection = sqlite3.connect(f'file:{self.path}?mode=ro', uri=True, timeout=2)
        else:
            connection = sqlite3.connect(self.path, timeout=2)
            connection.execute('PRAGMA synchronous=NORMAL')
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _db(self, readonly=False):
        db = self._connect(readonly)
        try:
            yield db
            if not readonly:
                db.commit()
        except Exception:
            if not readonly:
                db.rollback()
            raise
        finally:
            db.close()

    def _initialize(self):
        with self.lock, self._db() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    occurred_at INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    request_id TEXT,
                    attempt INTEGER,
                    duration_ms INTEGER,
                    outcome TEXT,
                    reason TEXT,
                    dimensions TEXT NOT NULL,
                    value INTEGER
                );
                CREATE INDEX IF NOT EXISTS events_time ON events(occurred_at DESC);
                CREATE INDEX IF NOT EXISTS events_type_time ON events(event_type, occurred_at DESC);
                CREATE TABLE IF NOT EXISTS daily_metrics (
                    day TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    count INTEGER NOT NULL,
                    duration_count INTEGER NOT NULL,
                    duration_sum INTEGER NOT NULL,
                    value_sum INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(day, metric)
                );
            ''')
            columns = {row[1] for row in db.execute('PRAGMA table_info(daily_metrics)')}
            if 'value_sum' not in columns:
                db.execute('ALTER TABLE daily_metrics ADD COLUMN value_sum INTEGER NOT NULL DEFAULT 0')
            started = str(int(self.now()))
            db.execute("INSERT OR IGNORE INTO metadata(key,value) VALUES('telemetry_started_at',?)",
                       (started,))
            db.execute("INSERT OR IGNORE INTO metadata(key,value) VALUES('last_cleanup','0')")

    def record(self, event_type, **fields):
        fields.setdefault('now', self.now())
        return self.insert_events([make_event(event_type, **fields)])

    def set_runtime(self, key, value):
        if key not in RUNTIME_KEYS or type(value) is not int or value < 0:
            raise ValueError('Invalid runtime telemetry state')
        with self.lock, self._db() as db:
            db.execute('INSERT INTO metadata(key,value) VALUES(?,?) '
                       'ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                       (key, str(value)))

    def insert_events(self, events):
        events = validate_batch(events)
        accepted = []
        with self.lock, self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            for event in events:
                row = db.execute(
                    '''INSERT OR IGNORE INTO events
                       (event_id,occurred_at,event_type,request_id,attempt,duration_ms,
                        outcome,reason,dimensions,value) VALUES(?,?,?,?,?,?,?,?,?,?)''',
                    (event['event_id'], event['occurred_at'], event['event_type'],
                     event.get('request_id'), event.get('attempt'), event.get('duration_ms'),
                     event.get('outcome'), event.get('reason'),
                     json.dumps(event.get('dimensions', {}), sort_keys=True,
                                separators=(',', ':')), event.get('value')))
                accepted.append(event['event_id'])
                if row.rowcount:
                    day = iso_day(event['occurred_at'])
                    for metric in _metric_keys(event):
                        duration = event.get('duration_ms')
                        db.execute(
                            '''INSERT INTO daily_metrics(day,metric,count,duration_count,duration_sum,value_sum)
                               VALUES(?,?,1,?,?,?) ON CONFLICT(day,metric) DO UPDATE SET
                               count=count+1,
                               duration_count=duration_count+excluded.duration_count,
                               duration_sum=duration_sum+excluded.duration_sum,
                               value_sum=value_sum+excluded.value_sum''',
                            (day, metric, 1 if duration is not None else 0, duration or 0,
                             event.get('value', 0)))
            self._cleanup_if_due(db)
        return accepted

    def _cleanup_if_due(self, db):
        now = int(self.now())
        last = int(db.execute("SELECT value FROM metadata WHERE key='last_cleanup'").fetchone()[0])
        if now - last < 86400:
            return
        db.execute('DELETE FROM events WHERE occurred_at < ?', (now - RETENTION_SECONDS,))
        db.execute("UPDATE metadata SET value=? WHERE key='last_cleanup'", (str(now),))
        page_size = db.execute('PRAGMA page_size').fetchone()[0]
        pages = db.execute('PRAGMA page_count').fetchone()[0]
        free = db.execute('PRAGMA freelist_count').fetchone()[0]
        while (pages - free) * page_size > self.ceiling:
            removed = db.execute(
                'DELETE FROM events WHERE event_id IN '
                '(SELECT event_id FROM events ORDER BY occurred_at LIMIT 250)').rowcount
            if not removed:
                break
            pages = db.execute('PRAGMA page_count').fetchone()[0]
            free = db.execute('PRAGMA freelist_count').fetchone()[0]

    @staticmethod
    def _since(range_name, now):
        return {'today': int(datetime.fromtimestamp(now, timezone.utc)
                             .replace(hour=0, minute=0, second=0, microsecond=0).timestamp()),
                '7 days': int(now - 7 * 86400),
                '30 days': int(now - 30 * 86400),
                'all time': 0}[range_name]

    def snapshot(self, range_name='today', activity_limit=100):
        if range_name not in ('today', '7 days', '30 days', 'all time'):
            raise ValueError('Invalid telemetry range')
        now, since = int(self.now()), self._since(range_name, self.now())
        with self.lock, self._db(readonly=True) as db:
            started = int(db.execute(
                "SELECT value FROM metadata WHERE key='telemetry_started_at'").fetchone()[0])
            if range_name == 'all time':
                rows = db.execute(
                    'SELECT metric,SUM(count) count,SUM(duration_count) duration_count,'
                    'SUM(duration_sum) duration_sum,SUM(value_sum) value_sum '
                    'FROM daily_metrics GROUP BY metric').fetchall()
            else:
                start_day = iso_day(since)
                rows = db.execute(
                    'SELECT metric,SUM(count) count,SUM(duration_count) duration_count,'
                    'SUM(duration_sum) duration_sum,SUM(value_sum) value_sum '
                    'FROM daily_metrics WHERE day>=? GROUP BY metric',
                    (start_day,)).fetchall()
            metrics = {row['metric']: {'count': row['count'],
                                       'duration_count': row['duration_count'],
                                       'duration_sum': row['duration_sum'],
                                       'value_sum': row['value_sum']} for row in rows}
            durations = ([] if range_name == 'all time' else
                [row[0] for row in db.execute(
                    "SELECT duration_ms FROM events WHERE occurred_at>=? "
                    "AND event_type='response_completed' AND duration_ms IS NOT NULL "
                    'ORDER BY duration_ms', (since,)).fetchall()])
            events = [dict(row) for row in db.execute(
                'SELECT occurred_at,event_type,attempt,duration_ms,outcome,reason,dimensions,value '
                'FROM events WHERE occurred_at>=? ORDER BY occurred_at DESC LIMIT ?',
                (since, min(500, max(1, activity_limit)))).fetchall()]
            busiest = None
            if range_name != 'all time':
                row = db.execute(
                    "SELECT strftime('%H:00', occurred_at, 'unixepoch') period, COUNT(*) count "
                    "FROM events WHERE occurred_at>=? AND event_type='request_accepted' "
                    'GROUP BY period ORDER BY count DESC, period LIMIT 1', (since,)).fetchone()
                if row:
                    busiest = {'period_utc': row['period'], 'count': row['count']}
            runtime = {row['key']: int(row['value']) for row in db.execute(
                'SELECT key,value FROM metadata WHERE key IN (%s)' %
                ','.join('?' for _ in RUNTIME_KEYS), tuple(RUNTIME_KEYS)).fetchall()}
        for event in events:
            event['dimensions'] = json.loads(event['dimensions'])
        percentile = lambda p: (durations[min(len(durations)-1, int((len(durations)-1)*p))]
                                if durations else None)
        aggregate_duration_count = sum(value['duration_count'] for key, value in metrics.items()
                                       if key == 'response_completed')
        aggregate_duration_sum = sum(value['duration_sum'] for key, value in metrics.items()
                                     if key == 'response_completed')
        samples = aggregate_duration_count if range_name == 'all time' else len(durations)
        gaps = metrics.get('telemetry_gap', {}).get('value_sum', 0)
        return {'range': range_name, 'telemetry_started_at': started, 'metrics': metrics,
                'latency': {'samples': samples, 'p50_ms': percentile(.50),
                            'p95_ms': percentile(.95),
                            'average_ms': (aggregate_duration_sum // aggregate_duration_count
                                           if aggregate_duration_count else None)},
                'events': events, 'telemetry_gaps': gaps, 'runtime': runtime,
                'busiest_period': busiest,
                'generated_at': now}


def activity_text(event):
    """Fixed renderer; never displays identifiers or arbitrary data."""
    label = ACTIVITY_LABELS.get(event.get('event_type'), 'Operational event')
    dimensions = event.get('dimensions') or {}
    if event.get('event_type') == 'capability_completed':
        label = 'public_world_lookup ' + ('succeeded' if event.get('outcome') == 'success'
                                          else 'failed')
    elif event.get('event_type') == 'situation_classified':
        kind = dimensions.get('interaction_kind')
        label = (kind.replace('_', ' ').title()
                 if kind in DIMENSIONS['interaction_kind'] else 'Request classified')
    if event.get('attempt'):
        label += f" · attempt {event['attempt']}"
    if event.get('duration_ms') is not None:
        label += f" · {event['duration_ms']} ms"
    if event.get('reason') in REASONS and event.get('event_type') in {
            'safe_error', 'inference_failed', 'validation_rejected', 'telemetry_gap'}:
        label += ' · ' + event['reason'].replace('_', ' ')
    return label
