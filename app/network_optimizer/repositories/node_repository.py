"""
repositories/node_repository.py — Data access for nodes.

The ONLY layer that reads/writes the nodes table.
Returns plain dicts (or you can use dataclasses) — no ORM objects leave this layer.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.network_optimizer.models.orm_models import NodeModel


class NodeRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, name: str) -> dict:
        """Persist a new node. Raises ValueError on duplicate name."""
        node = NodeModel(name=name)
        self._db.add(node)
        try:
            self._db.flush()
        except IntegrityError:
            self._db.rollback()
            raise ValueError(f"Node '{name}' already exists.")
        return {"id": node.id, "name": node.name, "created_at": node.created_at}

    def get_by_id(self, node_id: int) -> dict | None:
        row = self._db.get(NodeModel, node_id)
        if row is None:
            return None
        return {"id": row.id, "name": row.name, "created_at": row.created_at}

    def get_by_name(self, name: str) -> dict | None:
        row = self._db.execute(
            select(NodeModel).where(NodeModel.name == name)
        ).scalar_one_or_none()
        if row is None:
            return None
        return {"id": row.id, "name": row.name, "created_at": row.created_at}

    def get_all(self) -> list[dict]:
        rows = self._db.execute(
            select(NodeModel).order_by(NodeModel.id)
        ).scalars().all()
        return [{"id": r.id, "name": r.name, "created_at": r.created_at} for r in rows]

    def get_all_names(self) -> list[str]:
        return list(self._db.execute(select(NodeModel.name)).scalars().all())

    def delete(self, node_id: int) -> bool:
        row = self._db.get(NodeModel, node_id)
        if row is None:
            return False
        self._db.delete(row)
        self._db.flush()
        return True
