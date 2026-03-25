"""
repositories/edge_repository.py — Data access for edges.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.network_optimizer.models.orm_models import EdgeModel, NodeModel


class EdgeRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _resolve_node(self, name: str) -> NodeModel:
        row = self._db.execute(
            select(NodeModel).where(NodeModel.name == name)
        ).scalar_one_or_none()
        if row is None:
            raise ValueError(f"Node '{name}' not found.")
        return row

    def create(self, source_name: str, destination_name: str, latency: float) -> dict:
        src = self._resolve_node(source_name)
        dst = self._resolve_node(destination_name)

        edge = EdgeModel(source_id=src.id, destination_id=dst.id, latency=latency)
        self._db.add(edge)
        try:
            self._db.flush()
        except IntegrityError:
            self._db.rollback()
            raise ValueError(
                f"Edge from '{source_name}' to '{destination_name}' already exists."
            )
        return {
            "id": edge.id,
            "source": source_name,
            "destination": destination_name,
            "latency": latency,
            "created_at": edge.created_at,
        }

    def get_all(self) -> list[dict]:
        rows = self._db.execute(
            select(EdgeModel).order_by(EdgeModel.id)
        ).scalars().all()
        result = []
        for e in rows:
            src = self._db.get(NodeModel, e.source_id)
            dst = self._db.get(NodeModel, e.destination_id)
            if src and dst:
                result.append({
                    "id": e.id,
                    "source": src.name,
                    "destination": dst.name,
                    "latency": e.latency,
                    "created_at": e.created_at,
                })
        return result

    def get_all_as_tuples(self) -> list[tuple[str, str, float]]:
        """Used at startup to hydrate the in-memory GraphStore from DB."""
        rows = self._db.execute(select(EdgeModel)).scalars().all()
        result = []
        for e in rows:
            src = self._db.get(NodeModel, e.source_id)
            dst = self._db.get(NodeModel, e.destination_id)
            if src and dst:
                result.append((src.name, dst.name, e.latency))
        return result

    def get_by_id(self, edge_id: int) -> dict | None:
        e = self._db.get(EdgeModel, edge_id)
        if e is None:
            return None
        src = self._db.get(NodeModel, e.source_id)
        dst = self._db.get(NodeModel, e.destination_id)
        if not src or not dst:
            return None
        return {
            "id": e.id,
            "source": src.name,
            "destination": dst.name,
            "latency": e.latency,
            "created_at": e.created_at,
        }

    def delete(self, edge_id: int) -> bool:
        row = self._db.get(EdgeModel, edge_id)
        if row is None:
            return False
        self._db.delete(row)
        self._db.flush()
        return True
