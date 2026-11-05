"""Explicit migration command; never runs as part of a public request."""
import os

from .migration_runner import apply_migrations
from .database import AnalyticsTarget


def main():
    database_url = os.environ.get('OES_ANALYTICS_DATABASE_URL', '').strip()
    if not database_url:
        raise SystemExit('OES_ANALYTICS_DATABASE_URL is required')
    try:
        import psycopg
    except ImportError as error:
        raise SystemExit('PostgreSQL analytics dependency is unavailable') from error
    target = AnalyticsTarget(os.environ.get('OES_ANALYTICS_EXPECTED_DATABASE', ''),
                             os.environ.get('OES_ANALYTICS_SCHEMA', ''))
    if not target.isolated:
        raise SystemExit('Analytics database isolation configuration is required')
    with psycopg.connect(database_url, connect_timeout=5,
                         options=target.options('statement_timeout=30000')) as connection:
        target.verify(connection)
        versions = apply_migrations(connection)
    print('Applied analytics migrations:', ', '.join(str(value) for value in versions))


if __name__ == '__main__':
    main()
