"""
services/route_service.py — Route business logic.

Orchestrates:
  - GraphStore  (in-memory pathfinding)
  - dijkstra()  (shortest path algorithm)
  - RouteRepository (history persistence, done via EventBus observer)
  - EventBus    (fires RouteComputedEvent after every query)
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.network_optimizer.events.bus import EventBus, RouteComputedEvent
from app.network_optimizer.graph.algorithms.dijkstra import NoPathError, dijkstra
from app.network_optimizer.graph.store import GraphStore
from app.network_optimizer.repositories.route_repository import RouteRepository


class RouteService:
    def __init__(self, db: Session, event_bus: EventBus) -> None:
        self._db = db
        self._graph = GraphStore()
        self._bus = event_bus
        self._repo = RouteRepository(db)

    def find_shortest_path(self, source: str, destination: str) -> dict:
        """
        Validate nodes, run Dijkstra, publish event (triggers DB history via observer),
        and return the result.

        Returns dict with keys: path, total_latency, hops
        Raises ValueError for invalid/missing nodes.
        Raises NoPathError if no path exists.
        """
        # ── 1. Validate ───────────────────────────────────────────────────────
        if source == destination:
            raise ValueError("Source and destination must be different.")
        if not self._graph.has_node(source):
            raise ValueError(f"Node '{source}' does not exist.")
        if not self._graph.has_node(destination):
            raise ValueError(f"Node '{destination}' does not exist.")

        # ── 2. Pathfind ───────────────────────────────────────────────────────
        try:
            path, total_latency = dijkstra(self._graph, source, destination)
            success = True
        except NoPathError:
            # Publish failure event so history is still logged
            self._bus.publish(RouteComputedEvent(
                source=source,
                destination=destination,
                path=[],
                total_latency=None,
                success=False,
                algorithm_used="dijkstra",
            ))
            raise

        # ── 3. Publish success event ──────────────────────────────────────────
        self._bus.publish(RouteComputedEvent(
            source=source,
            destination=destination,
            path=path,
            total_latency=total_latency,
            success=True,
            algorithm_used="dijkstra",
        ))

        return {
            "path": path,
            "total_latency": total_latency,
            "hops": len(path) - 1,
        }

    def get_history(
        self,
        source: str | None = None,
        destination: str | None = None,
        limit: int = 50,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict]:
        return self._repo.get_history(
            source=source,
            destination=destination,
            limit=limit,
            date_from=date_from,
            date_to=date_to,
        )
