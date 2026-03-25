"""
Enables class-based view (CBV) registration:

    router = NetworkRouter()
    router.add_view("/nodes/",           NodeListView,      tags=["Nodes"])
    router.add_view("/nodes/{node_id}/", NodeDetailView,    tags=["Nodes"])
    router.add_view("/routes/shortest/", RouteShortestView, tags=["Routes"])

The router introspects each class for get/post/put/patch/delete methods
and registers them automatically with FastAPI.

KEY IMPLEMENTATION DETAIL
--------------------------
FastAPI reads a function's signature at registration time to discover:
  - Path params   (e.g. node_id: int)
  - Query params  (e.g. limit: int = 50)
  - Request body  (e.g. body: NodeCreateSerializer)
  - Dependencies  (Depends(...))

An *unbound* class method still has `self` as its first parameter.
FastAPI would misinterpret `self` as a required query parameter.

FIX: Instantiate the view class and pass the bound method to FastAPI.
Bound methods in Python automatically drop `self` from their signature.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

_HTTP_METHODS = ["get", "post", "put", "patch", "delete"]

_DEFAULT_STATUS = {
    "get": 200,
    "post": 201,
    "put": 200,
    "patch": 200,
    "delete": 204,
}


class NetworkRouter:
    """
    Django-REST-Framework-inspired router for FastAPI.

    Usage:
        node_router = NetworkRouter()
        node_router.add_view("/",           NodeListView,   tags=["Nodes"])
        node_router.add_view("/{node_id}/", NodeDetailView, tags=["Nodes"])

        # In config/urls.py:
        api_router.include_router(node_router.get_router(), prefix="/nodes")
    """

    def __init__(self, prefix: str = "") -> None:
        self._router = APIRouter(prefix=prefix)

    def add_view(
        self,
        path: str,
        view_class: type,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Register all implemented HTTP methods from view_class at the given path.

        - path:       e.g. "/", "/{node_id}/"
        - view_class: class with get/post/put/patch/delete methods
        - tags:       OpenAPI tag group
        """
        clean_path = path.rstrip("/") or "/"

        # Instantiate the view — bound methods have no `self` in their signature
        instance = view_class()

        for method_name in _HTTP_METHODS:
            if not hasattr(view_class, method_name):
                continue

            bound_fn = getattr(instance, method_name)

            status_code    = getattr(bound_fn, "_status_code",    _DEFAULT_STATUS[method_name])
            response_model = getattr(bound_fn, "_response_model", None)
            summary        = getattr(bound_fn, "_summary",        f"{method_name.upper()} {clean_path}")
            responses      = getattr(bound_fn, "_responses",      {})

            decorator = getattr(self._router, method_name)
            decorator(
                clean_path,
                status_code=status_code,
                response_model=response_model,
                tags=tags or [],
                summary=summary,
                responses=responses,
                **kwargs,
            )(bound_fn)

    def get_router(self) -> APIRouter:
        """Return the underlying FastAPI APIRouter for use with include_router."""
        return self._router


def view_config(
    response_model=None,
    status_code: int | None = None,
    summary: str | None = None,
    responses: dict | None = None,
):
    """
    Optional decorator to annotate CBV methods with route metadata.
    NetworkRouter reads these attributes during add_view().

    Example:
        class NodeListView:
            @view_config(response_model=NodeSerializer, status_code=201, summary="Create node")
            def post(self, body: NodeCreateSerializer, service=Depends(get_node_service)):
                ...
    """
    def decorator(fn):
        if response_model is not None:
            fn._response_model = response_model
        if status_code is not None:
            fn._status_code = status_code
        if summary is not None:
            fn._summary = summary
        if responses is not None:
            fn._responses = responses
        return fn
    return decorator
