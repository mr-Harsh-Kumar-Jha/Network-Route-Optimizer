"""
All application-level startup, middleware, and URL wiring happens here.
"""
from __future__ import annotations

import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure the project root (where /app lives) is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config.settings.base import get_settings

settings = get_settings()

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup/shutdown lifecycle.

    1. Verify DB tables exist.
    2. Initialize EventBus with all observers.
    3. Hydrate in-memory GraphStore from Postgres.
    """
    from app.config.database import Base, SessionLocal, engine
    from app.network_optimizer.events.bus import setup_event_bus
    from app.network_optimizer.graph.store import GraphStore
    from app.network_optimizer.repositories.node_repository import NodeRepository
    from app.network_optimizer.repositories.edge_repository import EdgeRepository

    # 1. Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified.")

    # 2. Event system
    setup_event_bus(SessionLocal)
    logger.info("EventBus ready.")

    # 3. Hydrate in-memory graph
    db = SessionLocal()
    try:
        graph = GraphStore()
        nodes = NodeRepository(db).get_all_names()
        edges = EdgeRepository(db).get_all_as_tuples()
        graph.load(nodes=nodes, edges=edges)
        logger.info("GraphStore loaded: %d nodes, %d edges", graph.node_count(), graph.edge_count())
    finally:
        db.close()

    logger.info("Server ready at http://%s:%d", settings.app_host, settings.app_port)
    yield
    logger.info("Server shutting down.")


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Network Route Optimizer",
    description="Weighted directed graph engine — Django-inspired MVC with FastAPI.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── URL Registration (config/urls.py) ─────────────────────────────────────────

from app.config.urls import api_router  # noqa: E402
app.include_router(api_router)

# ── Global Error Handler ──────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled: %s", exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})

# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"], summary="Service health + graph stats")
def health():
    from app.network_optimizer.graph.store import GraphStore
    g = GraphStore()
    return {"status": "ok", "nodes": g.node_count(), "edges": g.edge_count()}
