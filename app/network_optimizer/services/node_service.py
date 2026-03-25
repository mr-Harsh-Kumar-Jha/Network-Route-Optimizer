"""
services/node_service.py — Node business logic.

Coordinates between NodeRepository (DB) and GraphStore (in-memory).
Write-through strategy: DB first → then sync memory.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.network_optimizer.graph.store import GraphStore
from app.network_optimizer.repositories.node_repository import NodeRepository


class NodeService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = NodeRepository(db)
        self._graph = GraphStore()

    def add_node(self, name: str) -> dict:
        """
        Persist node to DB, commit, then add to in-memory graph.
        Raises ValueError if name already exists.
        """
        node = self._repo.create(name)
        self._db.commit()
        self._graph.add_node(name)
        return node

    def get_all_nodes(self) -> list[dict]:
        return self._repo.get_all()

    def delete_node(self, node_id: int) -> bool:
        """
        Delete from DB (cascades to edges), commit,
        then remove from in-memory graph.
        """
        node = self._repo.get_by_id(node_id)
        if node is None:
            return False
        self._repo.delete(node_id)
        self._db.commit()
        self._graph.remove_node(node["name"])
        return True
