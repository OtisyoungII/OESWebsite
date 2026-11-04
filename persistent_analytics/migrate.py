"""Explicit migration command; never runs as part of a public request."""
import os

from .migration_runner import apply_migrations


def main():
    database_url = os.environ.get('OES_ANALYTICS_DATABASE_URL', '').strip()
    if not database_url:
        raise SystemExit('OES_ANALYTICS_DATABASE_URL is required')
    try:
        import psycopg
    except ImportError as error:
        raise SystemExit('PostgreSQL analytics dependency is unavailable') from error
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        versions = apply_migrations(connection)
    print('Applied analytics migrations:', ', '.join(str(value) for value in versions))


if __name__ == '__main__':
    main()
