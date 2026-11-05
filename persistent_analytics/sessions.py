"""Durable anonymous sessions without storing raw browser tokens."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import re
import secrets
from uuid import uuid4

from .database import AnalyticsTarget


SESSION_SECONDS = 12 * 60 * 60
VISIT_SECONDS = 30 * 60
TOKEN = re.compile(r'^[0-9a-f]{32}$')
KEY = re.compile(r'^[0-9a-f]{64}$')


@dataclass(frozen=True)
class SessionResult:
    token: str
    created: bool
    visit_started: bool


class DisabledSessionStore:
    enabled = False

    def open(self, token, now):
        return None


class PsycopgSessionStore:
    """Synchronous bounded lookup used only by the lightweight session endpoint."""
    enabled = True

    def __init__(self, database_url, digest_key, *, connect=None, target=None):
        if not KEY.fullmatch(str(digest_key)):
            raise ValueError('Invalid analytics session digest key')
        self.database_url = database_url
        self.digest_key = bytes.fromhex(digest_key)
        self._connect = connect
        self.target = target or AnalyticsTarget()

    def _connection(self):
        if self._connect is None:
            import psycopg
            self._connect = psycopg.connect
        return self._connect(
            self.database_url,
            connect_timeout=1,
            options=self.target.options('statement_timeout=750'),
        )

    def digest(self, token):
        return hmac.new(self.digest_key, token.encode('ascii'), sha256).digest()

    def open(self, token, now):
        token = token if isinstance(token, str) and TOKEN.fullmatch(token) else secrets.token_hex(16)
        digest = self.digest(token)
        current = datetime.fromtimestamp(now, timezone.utc)
        expires = current + timedelta(seconds=SESSION_SECONDS)
        visit_before = current - timedelta(seconds=VISIT_SECONDS)
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT id, expires_at, last_seen_at FROM analytics_sessions '
                    'WHERE token_digest=%s FOR UPDATE', (digest,))
                row = cursor.fetchone()
                if row is None:
                    identifier = uuid4()
                    cursor.execute(
                        'INSERT INTO analytics_sessions '
                        '(id,token_digest,started_at,last_seen_at,expires_at,event_count,visit_count) '
                        'VALUES(%s,%s,%s,%s,%s,0,1) ON CONFLICT(token_digest) DO NOTHING '
                        'RETURNING id',
                        (identifier, digest, current, current, expires))
                    inserted = cursor.fetchone()
                    if inserted is not None:
                        connection.commit()
                        return SessionResult(token, True, True)
                    cursor.execute(
                        'SELECT id, expires_at, last_seen_at FROM analytics_sessions '
                        'WHERE token_digest=%s FOR UPDATE', (digest,))
                    row = cursor.fetchone()
                    if row is None:
                        raise RuntimeError('Analytics session conflict unresolved')

                if row[1] <= current:
                    cursor.execute(
                        'UPDATE analytics_sessions SET id=%s, started_at=%s, last_seen_at=%s, '
                        'expires_at=%s, event_count=0, visit_count=1 WHERE token_digest=%s',
                        (uuid4(), current, current, expires, digest))
                    connection.commit()
                    return SessionResult(token, True, True)

                visit_started = row[2] <= visit_before
                cursor.execute(
                    'UPDATE analytics_sessions SET last_seen_at=%s, expires_at=%s, '
                    'visit_count=visit_count+%s WHERE token_digest=%s',
                    (current, expires, 1 if visit_started else 0, digest))
            connection.commit()
        return SessionResult(token, False, visit_started)
