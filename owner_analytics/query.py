"""Fixed aggregate-only owner dashboard queries."""
from datetime import datetime, timedelta, timezone

from persistent_analytics.database import AnalyticsTarget


RANGES = {'7d':7, '30d':30, '90d':90, '13m':396}
METRICS = (
    'sessions', 'visits', 'page_views', 'product_activations',
    'eyeball_interactions', 'response_successes', 'safe_errors',
    'cancelled_requests', 'response_latency', 'analytics_drops', 'telemetry_gaps',
)


class AnalyticsQuery:
    def __init__(self, database_url, *, connect=None, now=None, target=None):
        self.database_url, self._connect = database_url, connect
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.target = target or AnalyticsTarget()

    def _connection(self):
        if self._connect is None:
            import psycopg
            self._connect = psycopg.connect
        return self._connect(
            self.database_url, connect_timeout=2,
            options=self.target.options('statement_timeout=3000',
                                        'default_transaction_read_only=on'))

    def snapshot(self, selected='30d'):
        days = RANGES.get(selected)
        if days is None:
            raise ValueError('Invalid analytics date range')
        end = self.now().date()
        start = end - timedelta(days=days - 1)
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT day,metric,count,duration_count,duration_sum '
                    'FROM analytics_daily_metrics WHERE day BETWEEN %s AND %s '
                    'AND metric=ANY(%s) ORDER BY day,metric',
                    (start, end, list(METRICS)))
                rows = cursor.fetchall()
                cursor.execute(
                    'SELECT day,source_event_count,source_drop_count,telemetry_gap_count,'
                    'aggregated_at,finalized_at FROM analytics_aggregation_days '
                    'WHERE day BETWEEN %s AND %s ORDER BY day', (start, end))
                statuses = cursor.fetchall()
                cursor.execute(
                    "SELECT value FROM analytics_metadata WHERE key='earliest_available_date'")
                earliest = cursor.fetchone()
                cursor.execute('SELECT MAX(occurred_at) FROM analytics_events')
                latest_event = cursor.fetchone()[0]
                cursor.execute('SELECT MAX(aggregated_at) FROM analytics_aggregation_days')
                latest_aggregate = cursor.fetchone()[0]
        totals = {metric: 0 for metric in METRICS if metric != 'response_latency'}
        latency_samples = latency_sum = 0
        trend = {}
        for day, metric, count, duration_count, duration_sum in rows:
            trend.setdefault(day.isoformat(), {})[metric] = count
            if metric == 'response_latency':
                latency_samples += duration_count
                latency_sum += duration_sum
            else:
                totals[metric] += count
        status = {row[0].isoformat(): {
            'events': row[1], 'drops': row[2], 'gaps': row[3],
            'aggregated_at': row[4], 'finalized': row[5] is not None,
        } for row in statuses}
        provisional = sum(not value['finalized'] for value in status.values())
        return {
            'range': selected, 'start': start, 'end': end, 'timezone': 'UTC',
            'totals': totals,
            'latency': {
                'samples': latency_samples,
                'average_ms': (round(latency_sum / latency_samples)
                               if latency_samples else None),
            },
            'trend': trend, 'status': status, 'provisional_days': provisional,
            'finalized_days': len(status) - provisional,
            'known_gap_count': sum(value['gaps'] for value in status.values()),
            'drop_count': sum(value['drops'] for value in status.values()),
            'earliest_available': earliest[0] if earliest else None,
            'latest_event': latest_event, 'latest_aggregate': latest_aggregate,
        }
