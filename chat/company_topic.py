"""Process-local, one-use conversation topic markers. No prose or fact payloads."""
from dataclasses import dataclass
import re
import secrets
import threading
import time


COMPANY_ENTITIES = ('oes', 'otis execution systems', 'chaseingreen', 'lottovate',
                    'sportfolio', 'drinks with friendz')
CONVERSATION_ID = re.compile(r'[0-9a-f]{32}')
TOPIC_TOKEN = re.compile(r'[0-9a-f]{64}')


@dataclass(frozen=True)
class TopicRecord:
    entity: str
    expires: float


class CompanyTopicStore:
    TTL_SECONDS = 180
    MAX_RECORDS = 512

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.records = {}
        self.lock = threading.Lock()

    def _expire(self, now):
        for key, (_, topic) in tuple(self.records.items()):
            if topic.expires <= now:
                del self.records[key]

    def issue(self, conversation, entity, previous=None):
        if (not isinstance(conversation, str) or not CONVERSATION_ID.fullmatch(conversation)
                or entity not in COMPANY_ENTITIES):
            return None
        now = self.clock()
        expiry = previous.expires if previous and previous.entity == entity else now + self.TTL_SECONDS
        with self.lock:
            self._expire(now)
            if expiry <= now or (conversation not in self.records
                                 and len(self.records) >= self.MAX_RECORDS):
                return None
            token = secrets.token_hex(32)
            self.records[conversation] = token, TopicRecord(entity, expiry)
            return token

    def consume(self, conversation, token):
        if (not isinstance(conversation, str) or not CONVERSATION_ID.fullmatch(conversation)
                or not isinstance(token, str) or not TOPIC_TOKEN.fullmatch(token)):
            return None
        with self.lock:
            self._expire(self.clock())
            record = self.records.get(conversation)
            if record and secrets.compare_digest(record[0], token):
                return self.records.pop(conversation)[1]
        return None
