"""Optional, failure-isolated PostgreSQL analytics persistence."""
from .sink import DisabledAnalyticsSink, PersistentAnalyticsSink, init_persistent_analytics
from .sessions import DisabledSessionStore, PsycopgSessionStore, SessionResult

__all__ = (
    'DisabledAnalyticsSink',
    'PersistentAnalyticsSink',
    'DisabledSessionStore',
    'PsycopgSessionStore',
    'SessionResult',
    'init_persistent_analytics',
)
