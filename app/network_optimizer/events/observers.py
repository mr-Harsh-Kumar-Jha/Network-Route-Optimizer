"""
Three observers subscribe to RouteComputedEvent:
  1. HistoryObserver  — persists every query to Postgres
  2. AnalyticsObserver — in-memory counters for popular routes
  3. LoggingObserver  — structured JSON log line for each query
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime

from app.network_optimizer.events.bus import RouteComputedEvent

logger = logging.getLogger(__name__)


class HistoryObserver:
    """Persists route queries to the database after every computation."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def __call__(self, event: RouteComputedEvent) -> None:
        from app.network_optimizer.repositories.route_repository import RouteRepository

        db = self._session_factory()
        try:
            repo = RouteRepository(db)
            repo.save(
                source=event.source,
                destination=event.destination,
                path=event.path,
                total_latency=event.total_latency,
                success=event.success,
                algorithm_used=event.algorithm_used,
            )
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error("HistoryObserver: failed to persist: %s", exc)
        finally:
            db.close()


class AnalyticsObserver:
    """Maintains in-memory counters for route analytics (no DB hit per query)."""

    def __init__(self) -> None:
        self.route_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.latency_totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.success_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def __call__(self, event: RouteComputedEvent) -> None:
        self.route_counts[event.source][event.destination] += 1
        if event.success and event.total_latency is not None:
            self.latency_totals[event.source][event.destination] += event.total_latency
            self.success_counts[event.source][event.destination] += 1

    def top_routes(self, limit: int = 10) -> list[dict]:
        pairs = [
            {
                "source": src,
                "destination": dst,
                "query_count": count,
                "avg_latency": (
                    round(self.latency_totals[src][dst] / self.success_counts[src][dst], 4)
                    if self.success_counts[src][dst] > 0 else None
                ),
            }
            for src, dsts in self.route_counts.items()
            for dst, count in dsts.items()
        ]
        return sorted(pairs, key=lambda x: x["query_count"], reverse=True)[:limit]


class LoggingObserver:
    """Emits a structured JSON log line for every route computation."""

    def __call__(self, event: RouteComputedEvent) -> None:
        logger.info(json.dumps({
            "event": "route_computed",
            "source": event.source,
            "destination": event.destination,
            "success": event.success,
            "path": event.path,
            "total_latency_ms": event.total_latency,
            "algorithm": event.algorithm_used,
            "timestamp": event.timestamp.isoformat(),
        }))
