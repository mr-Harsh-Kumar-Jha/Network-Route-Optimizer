"""
RouteShortestView →  POST /routes/shortest/   (compute shortest path)
RouteHistoryView  →  GET  /routes/history/    (query history)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.router import view_config
from app.network_optimizer.events.bus import get_event_bus
from app.network_optimizer.graph.algorithms.dijkstra import NoPathError
from app.network_optimizer.serializers.serializers import (
    ErrorSerializer,
    RouteHistorySerializer,
    RouteRequestSerializer,
    RouteResponseSerializer,
)
from app.network_optimizer.services.route_service import RouteService
from app.config.database import get_db


def get_route_service(db: Session = Depends(get_db)) -> RouteService:
    return RouteService(db=db, event_bus=get_event_bus())


class RouteShortestView:
    """
    Computes the minimum-latency route between two nodes using Dijkstra.
    Registered at:  /routes/shortest/
    """

    @view_config(
        response_model=RouteResponseSerializer,
        status_code=200,
        summary="Find the shortest (minimum latency) route between two nodes",
        responses={
            400: {"model": ErrorSerializer, "description": "Invalid or non-existent nodes"},
            404: {"model": ErrorSerializer, "description": "No path exists"},
        },
    )
    def post(
        self,
        body: RouteRequestSerializer,
        service: RouteService = Depends(get_route_service),
    ):
        try:
            result = service.find_shortest_path(body.source, body.destination)
            return RouteResponseSerializer(**result)
        except NoPathError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


class RouteHistoryView:
    """
    Returns a paginated, filterable list of all past route computations.
    Registered at:  /routes/history/
    """

    @view_config(
        response_model=list[RouteHistorySerializer],
        status_code=200,
        summary="Get route query history with optional filters",
    )
    def get(
        self,
        source: Optional[str] = Query(None, description="Filter by source node name"),
        destination: Optional[str] = Query(None, description="Filter by destination node name"),
        limit: int = Query(50, ge=1, le=500, description="Max records to return"),
        date_from: Optional[datetime] = Query(None, description="Start of time range (ISO 8601)"),
        date_to: Optional[datetime] = Query(None, description="End of time range (ISO 8601)"),
        service: RouteService = Depends(get_route_service),
    ):
        records = service.get_history(
            source=source,
            destination=destination,
            limit=limit,
            date_from=date_from,
            date_to=date_to,
        )
        return [RouteHistorySerializer(**r) for r in records]
