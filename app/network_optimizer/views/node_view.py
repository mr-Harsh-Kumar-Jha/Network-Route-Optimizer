"""
NodeListView  →  GET /nodes/    (list all)
              →  POST /nodes/   (create)
NodeDetailView → DELETE /nodes/{node_id}/  (remove)

Each view is a plain class.  The NetworkRouter in config/router.py
auto-discovers the get/post/delete methods and registers them with FastAPI.
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.router import view_config
from app.network_optimizer.serializers.serializers import (
    ErrorSerializer,
    NodeCreateSerializer,
    NodeSerializer,
)
from app.network_optimizer.services.node_service import NodeService
from app.config.database import get_db


def get_node_service(db: Session = Depends(get_db)) -> NodeService:
    """FastAPI Dependency — provides a NodeService scoped to the current request."""
    return NodeService(db)


# ── NodeListView ──────────────────────────────────────────────────────────────

class NodeListView:
    """
    Handles collection-level node operations.
    Registered at:  /nodes/
    """

    @view_config(
        response_model=list[NodeSerializer],
        status_code=200,
        summary="List all nodes in the network",
    )
    def get(self, service: NodeService = Depends(get_node_service)):
        return [NodeSerializer(**n) for n in service.get_all_nodes()]

    @view_config(
        response_model=NodeSerializer,
        status_code=201,
        summary="Add a new node (server) to the network",
        responses={400: {"model": ErrorSerializer}},
    )
    def post(
        self,
        body: NodeCreateSerializer,
        service: NodeService = Depends(get_node_service),
    ):
        try:
            node = service.add_node(body.name)
            return NodeSerializer(**node)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


# ── NodeDetailView ────────────────────────────────────────────────────────────

class NodeDetailView:
    """
    Handles single-node operations.
    Registered at:  /nodes/{node_id}/
    """

    @view_config(
        status_code=204,
        summary="Delete a node and all its incident edges",
        responses={404: {"model": ErrorSerializer}},
    )
    def delete(
        self,
        node_id: int,
        service: NodeService = Depends(get_node_service),
    ):
        if not service.delete_node(node_id):
            raise HTTPException(status_code=404, detail=f"Node id={node_id} not found.")
