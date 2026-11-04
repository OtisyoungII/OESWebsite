"""Optional, failure-isolated PostgreSQL analytics persistence."""
from .sink import DisabledAnalyticsSink, PersistentAnalyticsSink, init_persistent_analytics

__all__ = (
    'DisabledAnalyticsSink',
    'PersistentAnalyticsSink',
    'init_persistent_analytics',
)
