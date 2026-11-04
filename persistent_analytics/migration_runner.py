"""Versioned PostgreSQL migrations for optional persistent analytics."""
from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
import re


MIGRATION_NAME = re.compile(r'^(?P<version>[0-9]{4})_(?P<name>[a-z0-9_]+)\.sql$')
MIGRATION_LOCK_ID = 684320251


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str
    checksum: str


def discover_migrations():
    root = files('persistent_analytics.migrations')
    migrations = []
    for entry in root.iterdir():
        match = MIGRATION_NAME.fullmatch(entry.name)
        if not match:
            continue
        sql = entry.read_text(encoding='utf-8')
        migrations.append(Migration(
            version=int(match.group('version')),
            name=match.group('name'),
            sql=sql,
            checksum=sha256(sql.encode('utf-8')).hexdigest(),
        ))
    migrations.sort(key=lambda item: item.version)
    if len({item.version for item in migrations}) != len(migrations):
        raise ValueError('Duplicate analytics migration version')
    return migrations


def apply_migrations(connection):
    """Apply missing migrations and reject modified migration history."""
    migrations = discover_migrations()
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(%s)', (MIGRATION_LOCK_ID,))
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics_schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('SELECT version, name, checksum FROM analytics_schema_migrations')
        applied = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
        for migration in migrations:
            prior = applied.get(migration.version)
            if prior is not None:
                if prior != (migration.name, migration.checksum):
                    raise RuntimeError('Analytics migration history mismatch')
                continue
            cursor.execute(migration.sql)
            cursor.execute(
                'INSERT INTO analytics_schema_migrations(version, name, checksum) '
                'VALUES(%s, %s, %s)',
                (migration.version, migration.name, migration.checksum),
            )
    connection.commit()
    return tuple(item.version for item in migrations)
