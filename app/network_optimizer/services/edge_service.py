"""
services/edge_service.py — Edge business logic.

Coordinates between EdgeRepository (DB) and GraphStore (in-memory).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.network_optimizer.graph.store import GraphStore
from app.network_optimizer.repositories.edge_repository import EdgeRepository


class EdgeService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = EdgeRepository(db)
        self._graph = GraphStore()

    def add_edge(self, source: str, destination: str, latency: float) -> dict:
        """
        Validate, persist to DB, commit, then sync in-memory graph.
        Raises ValueError for invalid input or missing nodes.
        """
        if latency <= 0:
            raise ValueError("Latency must be a positive number.")
        if source == destination:
            raise ValueError("Source and destination must be different.")

        edge = self._repo.create(source, destination, latency)
        self._db.commit()
        self._graph.add_edge(source, destination, latency)
        return edge

    def get_all_edges(self) -> list[dict]:
        return self._repo.get_all()

    def delete_edge(self, edge_id: int) -> bool:
        """Delete from DB, commit, then remove from in-memory graph."""
        edge = self._repo.get_by_id(edge_id)
        if edge is None:
            return False
        self._repo.delete(edge_id)
        self._db.commit()
        self._graph.remove_edge(edge["source"], edge["destination"])
        return True
