import json
from contextlib import closing
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

from chat.worker_relay import TelemetryBuffer, WorkerRelay, RelayError
from oes_core_launcher.controller import CoreStatus
from oes_core_launcher.telemetry import (TelemetryStore, activity_text, console_view,
                                         copy_text, format_diagnostics, format_tab)
from oes_core_launcher.ui import telemetry_refresh_allowed
from oes_telemetry import (MAX_ACK_EVENTS, MAX_BATCH_BYTES, MAX_BATCH_EVENTS,
                           EVENT_TYPES, make_event, validate_batch, validate_event)
from worker.client import OutboundWorker


CONFIG = {'OES_CHAT_PROVIDER': 'outbound_worker', 'OES_WORKER_ENABLED': 'true',
          'OES_WORKER_ID': 'test-worker', 'OES_WORKER_KEY_ID': 'test-key',
          'OES_WORKER_SHARED_KEY': 'ab' * 32, 'OES_AI_CHAT_ENABLED': 'true',
          'OES_EYEBALL_ENABLED': 'true', 'OES_PROACTIVE_ENABLED': 'false',
          'OES_WORKER_RELAY_URL': 'https://example.com',
          'OES_WORKER_MODEL_DIGEST': 'cd' * 32, 'OLLAMA_MODEL': 'llama3.2'}


class Clock:
    def __init__(self, value=1800000000): self.value = value
    def __call__(self): return self.value


class SchemaTests(unittest.TestCase):
    def test_every_approved_event_type_is_accepted(self):
        for event_type in EVENT_TYPES:
            fields = ({'reason': 'buffer_overflow', 'value': 1}
                      if event_type == 'telemetry_gap' else {})
            with self.subTest(event_type=event_type):
                self.assertEqual(validate_event(make_event(event_type, **fields))['event_type'],
                                 event_type)

    def test_unknown_fields_types_dimensions_and_content_are_rejected(self):
        base = make_event('request_accepted', outcome='accepted')
        prohibited = ('message', 'response', 'prompt', 'query', 'evidence', 'url',
                      'ip_address', 'headers', 'cookies', 'credential', 'secret',
                      'signature', 'nonce', 'epoch', 'lease', 'path')
        changes = [{key: 'private'} for key in prohibited]
        changes.extend(({'event_type': 'unknown'}, {'reason': 'raw exception text'},
                        {'dimensions': {'query': 'private'}}, {'request_id': 'not-valid'}))
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    validate_event({**base, **change})

    def test_numbers_batch_count_and_batch_bytes_are_bounded(self):
        with self.assertRaises(ValueError):
            make_event('response_completed', duration_ms=600001)
        events = [make_event('request_accepted') for _ in range(MAX_BATCH_EVENTS + 1)]
        with self.assertRaises(ValueError): validate_batch(events)
        self.assertLessEqual(len(json.dumps(validate_batch(events[:-1])).encode()), MAX_BATCH_BYTES)


class BufferTests(unittest.TestCase):
    def test_ack_dedup_batch_bounds_and_overflow_gap(self):
        buffer = TelemetryBuffer(capacity=3)
        for _ in range(5): buffer.emit('request_accepted', outcome='accepted')
        batch = buffer.batch()
        self.assertLessEqual(len(batch), 3)
        self.assertTrue(any(event['event_type'] == 'telemetry_gap' for event in batch))
        gap = next(event for event in batch if event['event_type'] == 'telemetry_gap')
        self.assertGreaterEqual(gap['value'], 1)
        first = batch[-1]['event_id']
        buffer.acknowledge([first, first])
        self.assertNotIn(first, {event['event_id'] for event in buffer.batch()})
        with self.assertRaises(RelayError):
            buffer.acknowledge(['x'] * (MAX_ACK_EVENTS + 1))

    def test_negotiated_transport_ack_only_removes_persisted_ids(self):
        relay = WorkerRelay(CONFIG)
        relay.emit('request_accepted', outcome='accepted')
        connected = relay.dispatch('connect', {'boot':'boot', 'ollama':'ready',
                                                'telemetry_version':1})
        self.assertEqual(len(connected['telemetry']), 1)
        event_id = connected['telemetry'][0]['event_id']
        owner = {'epoch': connected['epoch'], 'boot':'boot', 'lease':connected['lease']}
        heartbeat = relay.dispatch('heartbeat', {**owner, 'job':None, 'ollama':'ready',
                                                  'telemetry_ack':[event_id]})
        self.assertEqual(heartbeat['telemetry'], [])
        self.assertEqual(relay.telemetry.batch(), [])
        with self.assertRaises(RelayError):
            relay.dispatch('heartbeat', {**owner, 'job':None, 'ollama':'ready',
                                          'telemetry_ack':['not-an-event-id']})

    def test_legacy_worker_negotiation_remains_operational(self):
        relay = WorkerRelay(CONFIG)
        connected = relay.dispatch('connect', {'boot':'legacy', 'ollama':'ready'})
        self.assertNotIn('telemetry', connected)
        owner = {'epoch':connected['epoch'], 'lease':connected['lease'], 'boot':'legacy'}
        heartbeat = relay.dispatch('heartbeat', {**owner, 'job':None, 'ollama':'ready'})
        self.assertNotIn('telemetry', heartbeat)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.clock = Clock()
        self.path = Path(self.temp.name) / 'telemetry.db'
        self.store = TelemetryStore(self.path, now=self.clock)

    def tearDown(self): self.temp.cleanup()

    def test_atomic_insert_dedup_aggregates_and_start_timestamp(self):
        event = make_event('response_completed', duration_ms=120, outcome='success',
                           now=self.clock())
        self.assertEqual(self.store.insert_events([event]), [event['event_id']])
        self.store.insert_events([event])
        snapshot = self.store.snapshot('all time')
        self.assertEqual(snapshot['metrics']['response_completed']['count'], 1)
        self.assertEqual(snapshot['latency']['samples'], 1)
        self.assertEqual(snapshot['telemetry_started_at'], self.clock.value)

    def test_concurrent_read_and_write(self):
        failures = []
        def writer():
            try:
                for _ in range(20): self.store.record('request_accepted', outcome='accepted')
            except Exception as error: failures.append(error)
        thread = threading.Thread(target=writer); thread.start()
        for _ in range(5): self.store.snapshot('today')
        thread.join()
        self.assertEqual(failures, [])
        self.assertEqual(self.store.snapshot('today')['metrics']['request_accepted']['count'], 20)

    def test_retention_removes_details_but_preserves_daily_aggregates(self):
        old = make_event('request_accepted', outcome='accepted',
                         now=self.clock.value - 31 * 86400)
        self.store.insert_events([old])
        self.clock.value += 86401
        self.store.record('request_accepted', outcome='accepted', now=self.clock.value)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events WHERE event_id=?',
                                       (old['event_id'],)).fetchone()[0], 0)
            self.assertGreaterEqual(db.execute('SELECT SUM(count) FROM daily_metrics').fetchone()[0], 2)

    def test_range_percentiles_gap_and_fixed_renderer(self):
        self.store.record('response_completed', duration_ms=100, outcome='success')
        self.store.record('response_completed', duration_ms=300, outcome='success')
        self.store.record('telemetry_gap', reason='buffer_overflow', value=3)
        snapshot = self.store.snapshot('today')
        self.assertEqual(snapshot['latency']['samples'], 2)
        self.assertEqual(snapshot['telemetry_gaps'], 3)
        self.assertNotIn('private', activity_text(snapshot['events'][0]))
        with self.assertRaises(ValueError): self.store.snapshot('invalid')

    def test_empty_state_and_hidden_ui_refresh_policy(self):
        snapshot = self.store.snapshot('today')
        self.assertEqual(snapshot['metrics'], {})
        self.assertEqual(snapshot['latency']['samples'], 0)
        self.assertFalse(telemetry_refresh_allowed('withdrawn'))
        self.assertFalse(telemetry_refresh_allowed('iconic'))
        self.assertTrue(telemetry_refresh_allowed('normal'))

    def test_database_ceiling_discards_details_not_aggregates(self):
        tiny = TelemetryStore(Path(self.temp.name) / 'tiny.db', now=self.clock, ceiling=1)
        tiny.record('request_accepted', outcome='accepted')
        self.clock.value += 86401
        tiny.record('response_completed', outcome='success')
        snapshot = tiny.snapshot('all time')
        self.assertEqual(snapshot['metrics']['request_accepted']['count'], 1)
        self.assertEqual(snapshot['metrics']['response_completed']['count'], 1)
        self.assertEqual(snapshot['events'], [])

    def test_unavailable_store_does_not_break_worker_telemetry_handling(self):
        broken = Mock()
        broken.insert_events.side_effect = sqlite3.DatabaseError('private path')
        worker = OutboundWorker(CONFIG, telemetry_store=broken)
        response = worker._telemetry_response({'active':False, 'health':{},
            'telemetry':[make_event('request_accepted', outcome='accepted')]})
        self.assertEqual(response, {'active':False, 'health':{}})
        self.assertEqual(worker.telemetry_ack, [])

    def test_ack_advances_only_after_successful_persistence(self):
        good = Mock()
        event = make_event('request_accepted', outcome='accepted')
        good.insert_events.return_value = [event['event_id']]
        worker = OutboundWorker(CONFIG, telemetry_store=good)
        worker._telemetry_response({'telemetry':[event]})
        self.assertEqual(worker.telemetry_ack, [event['event_id']])


class ClipboardTests(unittest.TestCase):
    @staticmethod
    def snapshot(events=None):
        return {
            'range':'today', 'telemetry_started_at':1800000000, 'metrics':{},
            'latency':{'samples':0, 'p50_ms':None, 'p95_ms':None, 'average_ms':None},
            'events':events or [], 'telemetry_gaps':0, 'runtime':{},
            'busiest_period':None, 'generated_at':1800000100,
        }

    def view(self, events=None):
        status = CoreStatus(core='Online', worker='Running',
                            ollama='Available; llama3.2 unloaded', relay='Connected')
        return console_view(self.snapshot(events), status)

    def test_copy_tab_contains_only_selected_tab(self):
        output = format_tab(self.view(), 'Overview')
        self.assertIn('OVERVIEW', output)
        self.assertIn('Accepted requests: 0', output)
        self.assertNotIn('EYEBALL', output)
        self.assertNotIn('HEALTH', output)
        self.assertNotIn('RECENT ACTIVITY', output)

    def test_full_diagnostics_has_all_sections_and_empty_states(self):
        output = format_diagnostics(self.view())
        for section in ('OES CORE DIAGNOSTICS', 'STATUS', 'OVERVIEW', 'EYEBALL',
                        'HEALTH', 'RECENT ACTIVITY', 'RECENT AUDIT'):
            self.assertIn(section, output)
        self.assertIn('Range: Today', output)
        self.assertIn('Visitor sessions: Not measured', output)
        self.assertIn('No events recorded', output)
        self.assertIn('Model: llama3.2 unloaded', output)

    def test_events_use_fixed_renderer_and_forbidden_fields_cannot_escape(self):
        forbidden = ('private prompt response query evidence https://secret.example '
                     '127.0.0.1 request-id event-id boot epoch lease nonce signature credential '
                     'C:\\private\\path')
        event = {'occurred_at':1800000001, 'event_type':'situation_classified',
                 'attempt':None, 'duration_ms':None, 'outcome':'success',
                 'reason':forbidden, 'dimensions':{'interaction_kind':forbidden},
                 'request_id':forbidden, 'event_id':forbidden}
        output = format_diagnostics(self.view([event]))
        self.assertIn('Request classified', output)
        self.assertNotIn(forbidden, output)
        for fragment in ('https://', '127.0.0.1', 'C:\\private'):
            self.assertNotIn(fragment, output)

    def test_clipboard_failure_is_bounded(self):
        clipboard = Mock()
        clipboard.clipboard_clear.side_effect = RuntimeError('private clipboard failure')
        self.assertFalse(copy_text(clipboard, 'safe fixed text'))
        clipboard.clipboard_append.assert_not_called()


if __name__ == '__main__': unittest.main()
