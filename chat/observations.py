"""Untrusted observations, tentative interpretations, and restrained initiation."""
from dataclasses import dataclass, asdict
import json
import math

CONTEXT_VALUES = {
    'section': {'home', 'products', 'client-work', 'services', 'government', 'community', 'research', 'about', 'contact'},
    'project': {'chaseingreen', 'lottovate', 'drinkswithfriendz'},
    'device': {'desktop', 'tablet', 'mobile'},
    'interaction_mode': {'pointer', 'touch', 'keyboard'},
}
NUMERIC_LIMITS = {'time_on_section_seconds': 3600, 'details_opened_count': 20,
                  'chat_open_count': 20, 'chat_message_count': 100}


def bounded_number(value, maximum):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or (isinstance(value, float) and not math.isfinite(value))):
        raise ValueError('Observation counts must be finite numbers.')
    return int(max(0, min(maximum, value)))


def validate_context(context):
    if not isinstance(context, dict) or set(context) - (CONTEXT_VALUES.keys() | NUMERIC_LIMITS.keys() | {'testflight_clicked'}):
        raise ValueError('Invalid context fields.')
    result = {}
    for key, value in context.items():
        if key in CONTEXT_VALUES:
            if not isinstance(value, str) or value not in CONTEXT_VALUES[key]:
                raise ValueError('Invalid context value.')
            result[key] = value
        elif key in NUMERIC_LIMITS:
            result[key] = bounded_number(value, NUMERIC_LIMITS[key])
        else:
            if not isinstance(value, bool):
                raise ValueError('testflight_clicked must be boolean.')
            result[key] = value
    return result


@dataclass(frozen=True)
class ObservationState:
    section: str = 'home'
    project: str | None = None
    device: str = 'desktop'
    interaction_mode: str = 'pointer'
    time_on_section_seconds: int = 0
    details_opened_count: int = 0
    testflight_clicked: bool = False
    chat_open_count: int = 0
    chat_message_count: int = 0

    @classmethod
    def from_context(cls, context):
        return cls(**validate_context(context))


@dataclass(frozen=True)
class InferenceState:
    possible_interest: str
    needs_guidance: str
    engagement_level: str
    confidence: float
    source_observations: tuple[str, ...]


def infer(observed):
    sources = []
    if observed.project:
        sources.append('project=' + observed.project)
    if observed.time_on_section_seconds >= 45:
        sources.append('time_on_section_seconds=' + str(observed.time_on_section_seconds))
    if observed.details_opened_count >= 2:
        sources.append('details_opened_count=' + str(observed.details_opened_count))
    if observed.testflight_clicked:
        sources.append('testflight_clicked=true')
    combined = bool(observed.project and observed.time_on_section_seconds >= 45
                    and (observed.details_opened_count >= 2 or observed.time_on_section_seconds >= 90))
    # Confidence is a conservative heuristic, not a calibrated probability.
    return InferenceState('possibly_elevated' if combined else 'unknown',
                          'unknown', 'moderate' if combined else 'unknown',
                          0.65 if combined else 0.2, tuple(sources))


def observation_contract(observed, interpretation):
    return ('\nObserved (untrusted browser reports, not independently verified): '
            + json.dumps(asdict(observed))
            + '\nPossible interpretation (tentative heuristic, not fact): '
            + json.dumps(asdict(interpretation))
            + '\nNever state the interpretation as fact or infer buying intent, motives, '
              'emotions, identity or sensitive traits. Elapsed time is time on the section, '
              'not proof of reading or attention. Do not claim the visitor needs help. '
              'User requests and serious policy outrank these signals. Do not narrate '
              'tracking or quote observations unless directly relevant to the question.')


@dataclass(frozen=True)
class InitiationRestraint:
    dismissed: bool = False
    user_active: bool = False
    visit_offered: bool = False
    suggestion_seen: bool = False
    seconds_since_last: int = 3600

    @classmethod
    def from_payload(cls, payload):
        if not isinstance(payload, dict) or set(payload) - cls.__dataclass_fields__.keys():
            raise ValueError('Invalid restraint fields.')
        cleaned = {}
        for key, value in payload.items():
            if key == 'seconds_since_last':
                cleaned[key] = bounded_number(value, 3600)
            elif not isinstance(value, bool):
                raise ValueError('Restraint flags must be boolean.')
            else:
                cleaned[key] = value
        return cls(**cleaned)


@dataclass(frozen=True)
class InitiationDecision:
    action: str
    reason: str


def decide_initiation(observed, restraint):
    # Restraints can only remove an offer, never bypass the observation thresholds.
    checks = [
        (restraint.dismissed, 'dismissed'),
        (restraint.user_active or observed.chat_open_count > 0 or observed.chat_message_count > 0, 'user_chat_precedence'),
        (observed.section not in {'products', 'client-work'}, 'section_not_eligible'),
        (observed.testflight_clicked, 'testflight_already_clicked'),
        (restraint.visit_offered, 'visit_already_offered'),
        (restraint.suggestion_seen, 'suggestion_already_seen'),
        (restraint.seconds_since_last < 180, 'cooldown'),
    ]
    for blocked, reason in checks:
        if blocked:
            return InitiationDecision('stay_silent', reason)
    enough = (observed.project and observed.time_on_section_seconds >= 45
              and (observed.details_opened_count >= 2 or observed.time_on_section_seconds >= 90))
    return InitiationDecision('offer_help', 'combined_observations') if enough else InitiationDecision('stay_silent', 'insufficient_signals')


def log_observations(logger, observed, interpretation, decision):
    logger.info('Eyeball observation %s', json.dumps({
        'section': observed.section, 'project': observed.project,
        'time_on_section': observed.time_on_section_seconds,
        'details_opened_count': observed.details_opened_count,
        'testflight_clicked': observed.testflight_clicked}))
    logger.info('Eyeball inference %s', json.dumps({
        'possible_interest': interpretation.possible_interest, 'confidence': interpretation.confidence}))
    logger.info('Eyeball initiation %s', json.dumps(asdict(decision)))
