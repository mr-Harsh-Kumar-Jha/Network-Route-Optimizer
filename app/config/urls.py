"""
app/config/urls.py — Root URL configuration.

The Django manage.py equivalent entry point for all URL routing.
main.py includes api_router from this file.

Each app has its own urls.py; this file aggregates them all.
"""
from fastapi import APIRouter

from app.network_optimizer.urls import edge_router, node_router, route_router

# Root router — included by main.py with app.include_router(api_router)
api_router = APIRouter()

api_router.include_router(node_router.get_router(),  prefix="/nodes")
api_router.include_router(edge_router.get_router(),  prefix="/edges")
api_router.include_router(route_router.get_router(), prefix="/routes")
