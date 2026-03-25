"""
repositories/route_repository.py — Data access for route query history.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.network_optimizer.models.orm_models import RouteQueryModel


class RouteRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def save(
        self,
        source: str,
        destination: str,
        path: list[str],
        total_latency: float | None,
        success: bool,
        algorithm_used: str = "dijkstra",
    ) -> dict:
        row = RouteQueryModel(
            source=source,
            destination=destination,
            path=path,
            total_latency=total_latency,
            success=success,
            algorithm_used=algorithm_used,
        )
        self._db.add(row)
        self._db.flush()
        return {
            "id": row.id,
            "source": row.source,
            "destination": row.destination,
            "path": row.path,
            "total_latency": row.total_latency,
            "success": row.success,
            "algorithm_used": row.algorithm_used,
            "created_at": row.created_at,
        }

    def get_history(
        self,
        source: str | None = None,
        destination: str | None = None,
        limit: int = 50,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict]:
        stmt = select(RouteQueryModel).order_by(RouteQueryModel.created_at.desc())

        if source:
            stmt = stmt.where(RouteQueryModel.source == source)
        if destination:
            stmt = stmt.where(RouteQueryModel.destination == destination)
        if date_from:
            stmt = stmt.where(RouteQueryModel.created_at >= date_from)
        if date_to:
            stmt = stmt.where(RouteQueryModel.created_at <= date_to)

        stmt = stmt.limit(max(1, min(limit, 500)))
        rows = self._db.execute(stmt).scalars().all()

        return [
            {
                "id": r.id,
                "source": r.source,
                "destination": r.destination,
                "path": r.path or [],
                "total_latency": r.total_latency,
                "success": r.success,
                "algorithm_used": r.algorithm_used,
                "created_at": r.created_at,
            }
            for r in rows
        ]
