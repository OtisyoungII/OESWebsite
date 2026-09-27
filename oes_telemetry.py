"""Strict content-free telemetry contract shared by Render, worker and OES Core."""
from datetime import datetime, timezone
import json
import re
import secrets
import time

SCHEMA_VERSION = 1
MAX_BATCH_EVENTS = 24
MAX_BATCH_BYTES = 12288
MAX_BUFFER_EVENTS = 512
MAX_ACK_EVENTS = 24

EVENT_TYPES = frozenset({
    'core_started', 'core_stopped', 'core_restarted', 'configuration_checked',
    'ollama_state', 'model_verified', 'worker_connected', 'worker_connection_failed',
    'worker_disconnected',
    'worker_recovered', 'request_accepted', 'request_rejected',
    'situation_classified', 'grounding_required', 'capability_requested',
    'capability_completed', 'worker_job_dispatched', 'inference_attempted',
    'inference_completed', 'inference_failed', 'validation_rejected',
    'correction_attempted', 'response_completed', 'safe_error',
    'request_cancelled', 'telemetry_gap',
})

OUTCOMES = frozenset({'success', 'failure', 'allowed', 'denied', 'accepted',
                      'rejected', 'available', 'unavailable'})
REASONS = frozenset({
    'none', 'ok', 'disabled', 'rate_limited', 'concurrency_limited', 'provider_unavailable',
    'invalid_request', 'same_origin_rejected', 'unavailable', 'timeout',
    'protocol_rejection', 'authentication_rejection', 'transport_failure',
    'provider_failure', 'no_results', 'not_assigned', 'input_message_bounds',
    'context_budget', 'worker_unavailable_busy', 'relay_ownership_lease',
    'job_deadline', 'model_readiness_digest', 'ollama_connect_failure',
    'ollama_cold_start_timeout', 'ollama_read_timeout',
    'ollama_protocol_malformed_event', 'incomplete_ollama_stream',
    'ollama_cleanup_recovery_failure', 'output_limit', 'response_output_limit',
    'provider_event_protocol', 'incomplete_provider_stream', 'grounded_rendering',
    'response_validation_exhausted', 'result_rejection_obsolete',
    'transport_rpc_timeout', 'cancellation', 'buffer_overflow',
    'unsupported_claim', 'false_action', 'false_observation', 'private_authority',
    'oes_authority', 'unapproved_url', 'capability_denial', 'evidence_not_used',
    'identity_explanation', 'customer_service', 'self_introduction', 'repetition',
    'length', 'one_sentence', 'first_person', 'question', 'malformed',
    'false_action_authority', 'generic_explanation', 'sentence_count',
    'visitor_narration',
})

DIMENSIONS = {
    'interaction_kind': frozenset({
        'serious', 'identity_question', 'teasing', 'conversation',
        'hypothetical_oes_design', 'oes_question', 'location_required',
        'current_public_information', 'unknown_visitor_reason', 'character_banter',
        'character_followup', 'unclear',
    }),
    'response_action': frozenset({
        'grounded_answer', 'explain_identity', 'playful_reply', 'answer',
        'reason_hypothetically', 'request_location', 'answer_with_public_evidence',
        'clarify', 'character_reply',
    }),
    'grounding_mode': frozenset({
        'approved_fact_selection', 'truthful_identity', 'character_no_new_facts',
        'truthful_no_new_oes_facts', 'hypothetical_no_current_state_claims',
        'approved_public_context', 'authorized_location_required', 'public_evidence',
        'no_assumptions',
    }),
    'capability': frozenset({'public_world_lookup'}),
    'component': frozenset({'core', 'worker', 'relay', 'ollama', 'model', 'tavily'}),
    'state': frozenset({'starting', 'online', 'stopped', 'connected', 'disconnected',
                        'reconnecting', 'ready', 'unavailable', 'verified', 'invalid',
                        'active', 'idle'}),
}

EVENT_DIMENSIONS = {
    'situation_classified': frozenset({'interaction_kind', 'response_action', 'grounding_mode'}),
    'grounding_required': frozenset({'grounding_mode'}),
    'capability_requested': frozenset({'capability'}),
    'capability_completed': frozenset({'capability'}),
    'configuration_checked': frozenset({'component', 'state'}),
    'ollama_state': frozenset({'component', 'state'}),
    'model_verified': frozenset({'component', 'state'}),
    'worker_connected': frozenset({'component', 'state'}),
    'worker_connection_failed': frozenset({'component', 'state'}),
    'worker_disconnected': frozenset({'component', 'state'}),
    'worker_recovered': frozenset({'component', 'state'}),
}

_HEX32 = re.compile(r'^[0-9a-f]{32}$')


def utc_seconds(now=None):
    return int(time.time() if now is None else now)


def make_event(event_type, *, request_id=None, attempt=None, duration_ms=None,
               outcome=None, reason=None, dimensions=None, value=None, now=None,
               event_id=None):
    event = {'schema_version': SCHEMA_VERSION,
             'event_id': event_id or secrets.token_hex(16),
             'occurred_at': utc_seconds(now), 'event_type': event_type}
    for key, item in (('request_id', request_id), ('attempt', attempt),
                      ('duration_ms', duration_ms), ('outcome', outcome),
                      ('reason', reason), ('dimensions', dimensions), ('value', value)):
        if item is not None:
            event[key] = item
    return validate_event(event)


def validate_event(event):
    allowed = {'schema_version', 'event_id', 'occurred_at', 'event_type', 'request_id',
               'attempt', 'duration_ms', 'outcome', 'reason', 'dimensions', 'value'}
    if not isinstance(event, dict) or set(event) - allowed:
        raise ValueError('Invalid telemetry fields')
    if event.get('schema_version') != SCHEMA_VERSION or event.get('event_type') not in EVENT_TYPES:
        raise ValueError('Invalid telemetry type')
    if not _HEX32.fullmatch(event.get('event_id', '')):
        raise ValueError('Invalid telemetry event identifier')
    occurred = event.get('occurred_at')
    if type(occurred) is not int or occurred < 1577836800 or occurred > 4102444800:
        raise ValueError('Invalid telemetry timestamp')
    if 'request_id' in event and not _HEX32.fullmatch(event['request_id']):
        raise ValueError('Invalid telemetry request identifier')
    for key, maximum in (('attempt', 2), ('duration_ms', 600000), ('value', 1000000)):
        if key in event and (type(event[key]) is not int or not 0 <= event[key] <= maximum):
            raise ValueError('Invalid telemetry number')
    if 'attempt' in event and event['attempt'] not in (1, 2):
        raise ValueError('Invalid telemetry attempt')
    if 'outcome' in event and event['outcome'] not in OUTCOMES:
        raise ValueError('Invalid telemetry outcome')
    if 'reason' in event and event['reason'] not in REASONS:
        raise ValueError('Invalid telemetry reason')
    dimensions = event.get('dimensions', {})
    allowed_dimensions = EVENT_DIMENSIONS.get(event['event_type'], frozenset())
    if not isinstance(dimensions, dict) or set(dimensions) - allowed_dimensions:
        raise ValueError('Invalid telemetry dimensions')
    for key, value in dimensions.items():
        if value not in DIMENSIONS[key]:
            raise ValueError('Invalid telemetry dimension value')
    if (event['event_type'] == 'telemetry_gap'
            and (event.get('reason') != 'buffer_overflow' or 'value' not in event)):
        raise ValueError('Invalid telemetry gap')
    return event


def validate_batch(events):
    if not isinstance(events, list) or len(events) > MAX_BATCH_EVENTS:
        raise ValueError('Invalid telemetry batch')
    result = [validate_event(event) for event in events]
    if len(json.dumps(result, separators=(',', ':'), ensure_ascii=True).encode('ascii')) > MAX_BATCH_BYTES:
        raise ValueError('Telemetry batch too large')
    return result


def iso_day(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
