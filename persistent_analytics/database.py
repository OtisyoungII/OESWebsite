"""Strict PostgreSQL target isolation shared by analytics components."""
from dataclasses import dataclass
import re


IDENTIFIER = re.compile(r'^[a-z][a-z0-9_]{0,62}$')
FORBIDDEN_SCHEMAS = frozenset({'public', 'pg_catalog', 'information_schema'})


def validated_identifier(value, *, schema=False):
    value = str(value or '').strip()
    if not value:
        return ''
    if not IDENTIFIER.fullmatch(value) or (schema and value in FORBIDDEN_SCHEMAS):
        raise ValueError('Invalid analytics database target')
    return value


def connection_options(schema='', *settings):
    """Build fixed libpq options; schema is identifier-only, never arbitrary SQL."""
    schema = validated_identifier(schema, schema=True)
    values = []
    if schema:
        values.extend(('-c', f'search_path={schema},pg_catalog'))
    for setting in settings:
        if setting not in {
                'statement_timeout=750', 'statement_timeout=2000',
                'statement_timeout=3000', 'statement_timeout=30000',
                'lock_timeout=5000', 'default_transaction_read_only=on'}:
            raise ValueError('Invalid analytics database option')
        values.extend(('-c', setting))
    return ' '.join(values)


@dataclass(frozen=True)
class AnalyticsTarget:
    expected_database: str = ''
    schema: str = ''

    def __post_init__(self):
        object.__setattr__(self, 'expected_database',
                           validated_identifier(self.expected_database))
        object.__setattr__(self, 'schema',
                           validated_identifier(self.schema, schema=True))

    @property
    def isolated(self):
        return bool(self.expected_database or self.schema)

    def options(self, *settings):
        return connection_options(self.schema, *settings)

    def verify(self, connection):
        """Fail before DDL unless the connection reached the approved target."""
        database, schema = connection.execute(
            'SELECT current_database(), current_schema()').fetchone()
        if self.expected_database and database != self.expected_database:
            raise RuntimeError('Analytics database target mismatch')
        if self.schema and schema != self.schema:
            raise RuntimeError('Analytics schema target mismatch')
        if not self.isolated:
            raise RuntimeError('Analytics database isolation is required')
