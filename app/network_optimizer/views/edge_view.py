"""
EdgeListView  →  GET /edges/    (list all)
              →  POST /edges/   (create)
EdgeDetailView → DELETE /edges/{edge_id}/
"""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.router import view_config
from app.network_optimizer.serializers.serializers import (
    EdgeCreateSerializer,
    EdgeSerializer,
    ErrorSerializer,
)
from app.network_optimizer.services.edge_service import EdgeService
from app.config.database import get_db


def get_edge_service(db: Session = Depends(get_db)) -> EdgeService:
    return EdgeService(db)


class EdgeListView:
    """
    Handles collection-level edge operations.
    Registered at:  /edges/
    """

    @view_config(
        response_model=list[EdgeSerializer],
        status_code=200,
        summary="List all directed edges in the network",
    )
    def get(self, service: EdgeService = Depends(get_edge_service)):
        return [EdgeSerializer(**e) for e in service.get_all_edges()]

    @view_config(
        response_model=EdgeSerializer,
        status_code=201,
        summary="Add a directed edge (latency in ms) between two nodes",
        responses={400: {"model": ErrorSerializer}},
    )
    def post(
        self,
        body: EdgeCreateSerializer,
        service: EdgeService = Depends(get_edge_service),
    ):
        try:
            edge = service.add_edge(body.source, body.destination, body.latency)
            return EdgeSerializer(**edge)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


class EdgeDetailView:
    """
    Handles single-edge operations.
    Registered at:  /edges/{edge_id}/
    """

    @view_config(
        status_code=204,
        summary="Delete an edge by ID",
        responses={404: {"model": ErrorSerializer}},
    )
    def delete(
        self,
        edge_id: int,
        service: EdgeService = Depends(get_edge_service),
    ):
        if not service.delete_edge(edge_id):
            raise HTTPException(status_code=404, detail=f"Edge id={edge_id} not found.")
