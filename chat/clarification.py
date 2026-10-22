"""Bounded typo clarification that grants no capability or authority."""
from collections import OrderedDict
from dataclasses import dataclass
import re
import secrets
import threading
import time

MAX_CANDIDATE_LENGTH = 96
MAX_CANDIDATES = 3
TOKEN_RE = re.compile(r'^[0-9a-f]{64}$')

PROTECTED = ('oes', 'eyeball', 'scout', 'chaseingreen', 'lottovate', 'sportfolio',
             'drinks with friendz')
HIGH_IMPACT = {
    'deploy': 'Deploy the app', 'deployment': 'Ask about deployment',
    'security': 'Ask about security', 'encryption': 'Ask about encryption',
    'credential': 'Ask about credentials', 'credentials': 'Ask about credentials',
    'account': 'Ask about an account change', 'payment': 'Ask about a financial action',
    'delete': 'Ask about deleting something', 'private': 'Ask about private information',
    'privacy': 'Ask about privacy',
    'permission': 'Ask about permissions', 'role': 'Ask about a role change',
    'scout': 'Ask about Scout',
}
AMBIGUOUS_WORDS = ('isle', 'also', 'able', 'sale', 'aisle')
COMMON_SHORT = frozenset({'hi', 'hey', 'hello', 'yes', 'no', 'ok', 'okay', 'thanks',
                          'lame', 'cool', 'help', 'what', 'why', 'who', 'when', 'where'})


def _distance(left, right):
    """Small Damerau-Levenshtein distance; comparison never grants authority."""
    rows = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
    for i in range(len(left) + 1): rows[i][0] = i
    for j in range(len(right) + 1): rows[0][j] = j
    for i in range(1, len(left) + 1):
        for j in range(1, len(right) + 1):
            rows[i][j] = min(rows[i - 1][j] + 1, rows[i][j - 1] + 1,
                             rows[i - 1][j - 1] + (left[i - 1] != right[j - 1]))
            if i > 1 and j > 1 and left[i - 1] == right[j - 2] and left[i - 2] == right[j - 1]:
                rows[i][j] = min(rows[i][j], rows[i - 2][j - 2] + 1)
    return rows[-1][-1]


def validate_candidate(value):
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_CANDIDATE_LENGTH:
        raise ValueError('Invalid clarification candidate')
    if value != value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError('Invalid clarification candidate')
    lowered = value.lower()
    if re.search(r'https?://|www\.|\b[a-z0-9.-]+\.(?:com|net|org)\b', lowered):
        raise ValueError('Invalid clarification candidate')
    if re.search(r'\b(?:api[_ -]?key|password|secret|token)\s*[:=]', lowered):
        raise ValueError('Invalid clarification candidate')
    if re.search(r'(?:^|\s)(?:sudo|powershell|cmd(?:\.exe)?|bash|curl|wget)\b|[;&|`]', lowered):
        raise ValueError('Invalid clarification candidate')
    if re.search(r'\b(?:capability|admin|administrator|authorized role|permission granted)\b', lowered):
        raise ValueError('Invalid clarification candidate')
    return value


@dataclass(frozen=True)
class ClarificationDecision:
    reason: str
    candidates: tuple[str, ...] = ()


class ClarificationAnalyzer:
    def analyze(self, message, locale='en'):
        text, lowered = message.strip(), message.strip().lower()
        # Preserve intentional names, handles, tickers, identifiers and multilingual text.
        if (any(ord(char) > 127 for char in text)
                or any(term in lowered for term in PROTECTED)
                or re.fullmatch(r'[$@]?[A-Z]{1,5}', text)
                or re.search(r'[@_/\\]|\b[A-Za-z]+\d+[A-Za-z0-9-]*\b', text)):
            return None

        words = re.findall(r"[a-z]+", lowered)
        if any(word in HIGH_IMPACT for word in words):
            return None
        for word in words:
            matches = [term for term in HIGH_IMPACT
                       if term != word and _distance(word, term) <= (1 if len(term) < 7 else 2)]
            if matches:
                choices = tuple(dict.fromkeys(HIGH_IMPACT[item] for item in matches))[:MAX_CANDIDATES]
                return ClarificationDecision('high_impact_ambiguity', choices)

        if locale != 'en':
            return None

        # Only short, single-token ambiguity is considered. Longer harmless prose passes unchanged.
        if len(words) == 1 and words[0] not in COMMON_SHORT and 3 <= len(words[0]) <= 8:
            matches = sorted((( _distance(words[0], term), term) for term in AMBIGUOUS_WORDS),
                             key=lambda item: (item[0], item[1]))
            choices = tuple(term for distance, term in matches if distance <= 2)[:MAX_CANDIDATES]
            if len(choices) >= 2:
                return ClarificationDecision('ambiguous_typo', choices)
            if not re.search(r'[aeiouy]', words[0]) and len(words[0]) >= 5:
                return ClarificationDecision('low_confidence')
        return None


class ClarificationStore:
    def __init__(self, clock=time.monotonic, ttl=600, maximum=1024):
        self.clock, self.ttl, self.maximum = clock, ttl, maximum
        self.records, self.lock = OrderedDict(), threading.RLock()

    def issue(self, candidate, reason):
        validate_candidate(candidate)
        now = self.clock()
        with self.lock:
            self._expire(now)
            token = secrets.token_hex(32)
            self.records[token] = (now + self.ttl, candidate, reason)
            while len(self.records) > self.maximum:
                self.records.popitem(last=False)
        return token

    def consume(self, token):
        if not isinstance(token, str) or not TOKEN_RE.fullmatch(token):
            return None
        now = self.clock()
        with self.lock:
            self._expire(now)
            record = self.records.pop(token, None)
        return None if record is None else (record[1], record[2])

    def _expire(self, now):
        for token, record in tuple(self.records.items()):
            if record[0] > now:
                break
            self.records.pop(token, None)
