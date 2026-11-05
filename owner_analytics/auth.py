"""Independent password, TOTP, CSRF and server-side owner sessions."""
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import re
import secrets
import struct
import threading
import time

from persistent_analytics.database import AnalyticsTarget


PASSWORD = re.compile(r'^pbkdf2_sha256\$(\d{6,9})\$([A-Za-z0-9_-]{16,64})\$([A-Za-z0-9_-]{32,64})$')
SESSION_SECONDS = 30 * 60
ABSOLUTE_SECONDS = 8 * 60 * 60
COOKIE = 'oes_owner_analytics'
CSRF_COOKIE = 'oes_owner_csrf'


def _b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode('ascii')


def _decode(value):
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def password_hash(password, *, iterations=600_000, salt=None):
    if not isinstance(password, str) or len(password) < 14:
        raise ValueError('Owner password does not meet minimum length')
    salt = salt or secrets.token_bytes(18)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return f'pbkdf2_sha256${iterations}${_b64(salt)}${_b64(digest)}'


def verify_password(password, encoded):
    match = PASSWORD.fullmatch(str(encoded))
    if not match or not isinstance(password, str):
        return False
    iterations, salt, expected = int(match[1]), _decode(match[2]), _decode(match[3])
    if not 300_000 <= iterations <= 2_000_000:
        return False
    actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return hmac.compare_digest(actual, expected)


def totp_counter(secret, code, now=None):
    try:
        key = base64.b32decode(str(secret).strip().upper(), casefold=True)
    except Exception:
        return None
    if len(key) < 20 or not re.fullmatch(r'\d{6}', str(code)):
        return None
    counter = int(time.time() if now is None else now) // 30
    for candidate in range(counter - 1, counter + 2):
        digest = hmac.new(key, struct.pack('>Q', candidate), hashlib.sha1).digest()
        offset = digest[-1] & 15
        value = (struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff) % 1_000_000
        if hmac.compare_digest(f'{value:06d}', str(code)):
            return candidate
    return None


@dataclass(frozen=True)
class OwnerSession:
    token: str
    csrf: str


class LoginLimiter:
    """Bounded in-memory defense; deployment edge limiting remains additive."""
    def __init__(self, maximum=5, window=900, clock=time.monotonic):
        self.maximum, self.window, self.clock = maximum, window, clock
        self.lock = threading.Lock()
        self.attempts = defaultdict(deque)

    def allow(self, key):
        now = self.clock()
        with self.lock:
            values = self.attempts[key]
            while values and values[0] <= now - self.window:
                values.popleft()
            if len(values) >= self.maximum:
                return False
            values.append(now)
            if len(self.attempts) > 2048:
                self.attempts = defaultdict(deque, {key: values})
            return True

    def clear(self, key):
        with self.lock:
            self.attempts.pop(key, None)


class OwnerAuthStore:
    def __init__(self, database_url, secret, *, connect=None, now=None, target=None):
        if len(str(secret)) < 32:
            raise ValueError('Invalid owner session secret')
        self.database_url, self.secret = database_url, str(secret).encode('utf-8')
        self._connect = connect
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.target = target or AnalyticsTarget()

    def _connection(self):
        if self._connect is None:
            import psycopg
            self._connect = psycopg.connect
        return self._connect(self.database_url, connect_timeout=2,
                             options=self.target.options('statement_timeout=2000'))

    def digest(self, value):
        return hmac.new(self.secret, value.encode('ascii'), hashlib.sha256).digest()

    def consume_totp(self, counter):
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE analytics_owner_auth_state SET last_totp_counter=%s "
                    "WHERE owner_id='owner' AND last_totp_counter < %s RETURNING owner_id",
                    (counter, counter))
                accepted = cursor.fetchone() is not None
            connection.commit()
        return accepted

    def allow_login(self, fingerprint, maximum=5, window_seconds=15 * 60):
        if (not isinstance(fingerprint, bytes) or len(fingerprint) != 32
                or type(maximum) is not int or not 1 <= maximum <= 20
                or type(window_seconds) is not int or not 60 <= window_seconds <= 3600):
            raise ValueError('Invalid owner login limit')
        now = self.now()
        window = timedelta(seconds=window_seconds)
        with self._connection() as connection:
            row = connection.execute(
                'INSERT INTO analytics_owner_login_attempts '
                '(fingerprint_digest,window_started_at,attempts,expires_at) '
                'VALUES(%s,%s,1,%s) ON CONFLICT(fingerprint_digest) DO UPDATE SET '
                'window_started_at=CASE WHEN '
                'analytics_owner_login_attempts.window_started_at<=%s THEN %s '
                'ELSE analytics_owner_login_attempts.window_started_at END, '
                'attempts=CASE WHEN analytics_owner_login_attempts.window_started_at<=%s '
                'THEN 1 ELSE analytics_owner_login_attempts.attempts+1 END, '
                'expires_at=%s RETURNING attempts',
                (fingerprint, now, now + window * 2, now - window, now,
                 now - window, now + window * 2)).fetchone()
            connection.commit()
        return row is not None and row[0] <= maximum

    def clear_login(self, fingerprint):
        if not isinstance(fingerprint, bytes) or len(fingerprint) != 32:
            return
        with self._connection() as connection:
            connection.execute(
                'DELETE FROM analytics_owner_login_attempts WHERE fingerprint_digest=%s',
                (fingerprint,))
            connection.commit()

    def create(self):
        now = self.now()
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        absolute = now + timedelta(seconds=ABSOLUTE_SECONDS)
        with self._connection() as connection:
            connection.execute(
                'DELETE FROM analytics_owner_sessions WHERE expires_at <= %s', (now,))
            connection.execute(
                'INSERT INTO analytics_owner_sessions '
                '(token_digest,csrf_digest,created_at,last_seen_at,expires_at,absolute_expires_at) '
                'VALUES(%s,%s,%s,%s,%s,%s)',
                (self.digest(token), self.digest(csrf), now, now,
                 now + timedelta(seconds=SESSION_SECONDS), absolute))
            connection.commit()
        return OwnerSession(token, csrf)

    def validate(self, token, csrf=None, *, touch=True):
        if not isinstance(token, str) or len(token) > 128:
            return False
        now = self.now()
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT csrf_digest,absolute_expires_at FROM analytics_owner_sessions '
                    'WHERE token_digest=%s AND expires_at>%s AND absolute_expires_at>%s FOR UPDATE',
                    (self.digest(token), now, now))
                row = cursor.fetchone()
                if row is None or (csrf is not None and (
                        not isinstance(csrf, str) or
                        not hmac.compare_digest(row[0], self.digest(csrf)))):
                    return False
                if touch:
                    expires = min(now + timedelta(seconds=SESSION_SECONDS), row[1])
                    cursor.execute(
                        'UPDATE analytics_owner_sessions SET last_seen_at=%s,expires_at=%s '
                        'WHERE token_digest=%s', (now, expires, self.digest(token)))
            connection.commit()
        return True

    def delete(self, token):
        if not isinstance(token, str) or len(token) > 128:
            return
        with self._connection() as connection:
            connection.execute('DELETE FROM analytics_owner_sessions WHERE token_digest=%s',
                               (self.digest(token),))
            connection.commit()
