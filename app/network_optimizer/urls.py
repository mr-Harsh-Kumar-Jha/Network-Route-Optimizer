from app.config.router import NetworkRouter
from app.network_optimizer.views.node_view import NodeDetailView, NodeListView
from app.network_optimizer.views.edge_view import EdgeDetailView, EdgeListView
from app.network_optimizer.views.route_view import RouteHistoryView, RouteShortestView

# ── Node URLs ─────────────────────────────────────────────────────────────────
node_router = NetworkRouter()
node_router.add_view("/",           NodeListView,   tags=["Nodes"])
node_router.add_view("/{node_id}/", NodeDetailView, tags=["Nodes"])

# ── Edge URLs ─────────────────────────────────────────────────────────────────
edge_router = NetworkRouter()
edge_router.add_view("/",           EdgeListView,   tags=["Edges"])
edge_router.add_view("/{edge_id}/", EdgeDetailView, tags=["Edges"])

# ── Route URLs ────────────────────────────────────────────────────────────────
route_router = NetworkRouter()
route_router.add_view("/shortest/", RouteShortestView, tags=["Routes"])
route_router.add_view("/history/",  RouteHistoryView,  tags=["Routes"])
