# Network Route Optimizer

> A production-quality backend service for computing shortest network paths using Dijkstra's algorithm.
> Built with **FastAPI + PostgreSQL + SQLAlchemy**, following a **Django-inspired MVC architecture**.

---

## Table of Contents

1. [Folder Structure](#1-folder-structure)
2. [Project Folders — Detailed Explanation](#2-project-folders--detailed-explanation)
3. [Technology Decisions](#3-technology-decisions)
4. [Software Architecture Decisions](#4-software-architecture-decisions)
5. [Setting Up the Project](#5-setting-up-the-project)

---

## 1. Folder Structure

```
app/
├── config/                         # Global project configuration
│   ├── urls.py                     # Root URL dispatcher
│   ├── database.py                 # DB engine, session factory, get_db()
│   ├── router.py                   # NetworkRouter — add_view() utility
│   └── settings/
│       ├── base.py                 # Base settings via pydantic-settings
│       ├── dev.py                  # Development environment overrides
│       └── prod.py                 # Production environment overrides
│
└── network_optimizer/              # Core application module
    ├── main.py                     # FastAPI app entry point
    ├── urls.py                     # App-level URL registrations
    │
    ├── models/
    │   └── orm_models.py           # SQLAlchemy ORM models
    │
    ├── serializers/
    │   └── serializers.py          # Pydantic serializers (input validation + output shaping)
    │
    ├── views/                      # HTTP layer — class-based views
    │   ├── node_view.py            # NodeListView, NodeDetailView
    │   ├── edge_view.py            # EdgeListView, EdgeDetailView
    │   └── route_view.py           # RouteShortestView, RouteHistoryView
    │
    ├── services/                   # Business logic layer
    │   ├── node_service.py
    │   ├── edge_service.py
    │   └── route_service.py
    │
    ├── repositories/               # Data access layer
    │   ├── node_repository.py
    │   ├── edge_repository.py
    │   └── route_repository.py
    │
    ├── graph/                      # In-memory graph engine
    │   ├── store.py                # GraphStore singleton
    │   └── algorithms/
    │       └── dijkstra.py         # Dijkstra's algorithm (pure function)
    │
    ├── events/                     # Pub/sub event system
    │   ├── bus.py                  # EventBus + RouteComputedEvent
    │   └── observers.py            # HistoryObserver, AnalyticsObserver, LoggingObserver
    │
    ├── migrations/                 # Alembic migration scripts
    │   └── env.py
    │
    └── tests/
        ├── unit/                   # Pure logic tests — no DB required
        └── integration/            # Full API tests — requires Postgres
```

---

## 2. Project Folders — Detailed Explanation

### `config/`
The global project configuration directory — equivalent to Django's project-level package.

| File | Purpose |
|------|---------|
| `urls.py` | **Root URL dispatcher.** Imports all app-level routers and mounts them under their prefixes (`/nodes`, `/edges`, `/routes`). This is the single source of truth for all API routes. |
| `database.py` | **Database connection.** Creates the SQLAlchemy engine, `SessionLocal` factory, `Base` (declarative base for all ORM models), and the `get_db()` FastAPI dependency that yields a DB session per request and always closes it. |
| `router.py` | **NetworkRouter utility.** A custom class that enables `add_view()` — Django REST Framework-style route registration. Instantiates the view class, extracts bound methods (`get`, `post`, `delete`), strips `self` from the signature, then registers each one with FastAPI using the correct HTTP verb and status code. |
| `settings/base.py` | **Application settings.** Uses `pydantic-settings` to read environment variables from `.env`. Defines `database_url`, `app_host`, `app_port`, `log_level`, `route_cache_ttl_seconds`, and more. Exposed via a cached `get_settings()` singleton. |

---

### `network_optimizer/`
The main application module — equivalent to a Django app.

#### `main.py`
FastAPI application entry point. Responsibilities:
- **Lifespan startup**: ensures DB tables exist, initialises the `EventBus` with all observers, hydrates the `GraphStore` from Postgres.
- Registers CORS middleware (permissive in dev, restrict in prod).
- Includes all API routes from `config/urls.py`.
- Provides the `/health` endpoint.

#### `models/orm_models.py`
SQLAlchemy ORM models — equivalent to Django's `models.py`. Defines three tables:
- `NodeModel` — represents a server/endpoint vertex.
- `EdgeModel` — directed connection between two nodes with a latency weight. Has a `UNIQUE(source_id, destination_id)` constraint.
- `RouteQueryModel` — immutable audit log of every shortest-path computation. Never updated; only inserted.

#### `serializers/serializers.py`
Pydantic models that handle **both input validation and output serialization** (named "serializers" following Django REST Framework convention). Each request body and response shape has its own serializer class, e.g. `NodeCreateSerializer`, `NodeSerializer`, `RouteRequestSerializer`, `RouteHistorySerializer`.

#### `views/`
The HTTP layer — **class-based views** where each class handles one URL and implements relevant HTTP methods:

```python
class NodeListView:
    def get(self, service=Depends(get_node_service)):   # GET /nodes
        ...
    def post(self, body: NodeCreateSerializer, ...):    # POST /nodes
        ...

class NodeDetailView:
    def delete(self, node_id: int, ...):                # DELETE /nodes/{node_id}
        ...
```

Views **only** handle HTTP concerns (parsing, status codes, error mapping). All logic is delegated to services.

#### `services/`
Business logic layer. Each service coordinates between the repository (DB) and the GraphStore (memory):
- `NodeService` — creates/deletes nodes, writes to DB first, then syncs the in-memory graph.
- `EdgeService` — creates/deletes edges with the same write-through pattern.
- `RouteService` — validates nodes exist → runs Dijkstra → publishes `RouteComputedEvent` (which triggers history persistence via the observer, keeping the service decoupled from DB writes).

#### `repositories/`
Data access layer — the **only** layer that reads/writes the database directly. Returns plain `dict` objects (not ORM instances) so upper layers never depend on SQLAlchemy types. Each repository takes a `Session` in its constructor (injected by FastAPI `Depends`).

#### `graph/`
The in-memory graph engine.
- `store.py` — `GraphStore` is a **singleton** adjacency list (`dict[str, dict[str, float]]`) protected by a read-write lock. Loaded from Postgres at startup. Supports `add_node`, `remove_node`, `add_edge`, `remove_edge`, `has_node`, `has_edge`, `neighbors`.
- `algorithms/dijkstra.py` — a pure function `dijkstra(graph, source, destination)` using a min-heap (`heapq`). Raises `NoPathError` if no route exists. No class hierarchy, no strategy abstraction — just a function.

#### `events/`
A lightweight in-process pub/sub system.
- `bus.py` — `EventBus` stores a map of `event_type → [list of handlers]`. Publishing an event calls all handlers. Observer failures are caught and logged — they must never crash the request pipeline. `setup_event_bus()` registers all observers at startup. `get_event_bus()` returns the singleton for use in services.
- `observers.py` — three observers react to every `RouteComputedEvent`:
  - `HistoryObserver` — opens a new DB session, writes the query record, closes the session.
  - `AnalyticsObserver` — increments in-memory route counters (no DB hit per query).
  - `LoggingObserver` — emits a structured JSON log line.

#### `migrations/`
Alembic migration environment. `env.py` imports settings and `Base.metadata` so `alembic autogenerate` picks up all ORM model changes automatically.

#### `tests/`
- `unit/` — tests for pure logic (Dijkstra, GraphStore). No DB connection required; runs in milliseconds.
- `integration/` — tests for the full HTTP stack using FastAPI `TestClient`. Requires a live Postgres instance.

---

## 3. Technology Decisions

| Technology | Version | Why |
|------------|---------|-----|
| **FastAPI** | ≥ 0.111 | Async-ready, automatic OpenAPI docs, excellent DI system via `Depends`, best-in-class performance. |
| **SQLAlchemy 2.0** | ≥ 2.0 | Modern ORM with `Mapped` + `mapped_column` type-safe column definitions. Clean session management. |
| **Alembic** | ≥ 1.13 | Autogenerate DB migrations from ORM model changes. Industry standard for SQLAlchemy projects. |
| **PostgreSQL 16** | 16+ | Reliable, ACID-compliant. `JSONB` for storing route paths. Cascading deletes for referential integrity. |
| **Pydantic v2** | ≥ 2.7 | Blazing-fast validation (Rust core), native FastAPI integration, automatic OpenAPI schema generation. |
| **pydantic-settings** | ≥ 2.2 | Type-safe `.env` parsing — settings are just a Pydantic model, validated at startup. |
| **psycopg2-binary** | ≥ 2.9 | Mature, reliable PostgreSQL driver. Binary wheel — no compilation needed. |
| **uvicorn** | ≥ 0.29 | Production-grade ASGI server. `[standard]` installs `uvloop` for high-throughput event loop. |
| **pytest + httpx** | Latest | `pytest-asyncio` for async test support. `httpx` powers FastAPI's `TestClient`. |

---

## 4. Software Architecture Decisions

### MVC — Django-Inspired, Adapted for FastAPI

The project deliberately mirrors Django's project layout to maximise readability for teams familiar with Django REST Framework, while using FastAPI under the hood.

| Django / DRF Concept | This Project |
|----------------------|-------------|
| `project/settings.py` | `config/settings/base.py` |
| `project/urls.py` | `config/urls.py` |
| `app/urls.py` | `network_optimizer/urls.py` |
| `app/models.py` | `models/orm_models.py` |
| `app/serializers.py` | `serializers/serializers.py` |
| `app/views.py` (CBV) | `views/node_view.py`, `views/route_view.py`, … |
| `router.register()` | `NetworkRouter.add_view()` |
| Django service layer | `services/` |
| Django repository layer | `repositories/` |

---

### Class-Based Views (CBVs)
Views are plain Python classes — no decorator clutter, easy to read and test:

```python
class NodeListView:
    def get(self, service=Depends(get_node_service)):
        return [NodeSerializer(**n) for n in service.get_all_nodes()]

    def post(self, body: NodeCreateSerializer, service=Depends(get_node_service)):
        return NodeSerializer(**service.add_node(body.name))
```

The `NetworkRouter` in `config/router.py` introspects these classes and wires them to FastAPI automatically.

---

### Write-Through Caching (DB ↔ Memory Sync)
Every mutation goes **DB first, then memory**. This ensures:
1. If the DB write fails, the graph is never updated (consistency).
2. If the server restarts, the lifespan handler rehydrates GraphStore from Postgres.
3. Reads hit memory (O(1) adjacency lookup), not the DB.

```
POST /nodes → NodeService.add_node()
  1. NodeRepository.create()  → INSERT INTO nodes
  2. db.commit()              → transaction committed
  3. GraphStore.add_node()    → in-memory update
```

---

### Observer / EventBus Pattern
Route computations publish a `RouteComputedEvent`. This decouples the pathfinding core from history persistence, analytics, and logging:

```
RouteService.find_shortest_path()
  → EventBus.publish(RouteComputedEvent)
      → HistoryObserver  (writes to route_queries table)
      → AnalyticsObserver (increments in-memory counters)
      → LoggingObserver   (JSON log line)
```

Adding a new side-effect (e.g. send a webhook) requires **zero changes** to `RouteService` — just register a new observer.

---

### Repository Pattern
No ORM objects leak out of the repository layer. Repositories return plain `dict` objects:

```python
def get_by_id(self, node_id: int) -> dict | None:
    row = self._db.get(NodeModel, node_id)
    return {"id": row.id, "name": row.name, "created_at": row.created_at}
```

This means services and views are completely independent of SQLAlchemy — they can be unit-tested with simple mocks.

---

### Dependency Injection (Scoped Sessions)
Every request gets its own DB session via `get_db()`:

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()   # always closes, even on exception
```

Services are created per-request using FastAPI `Depends` — no global state, no session leaks.

---

### Dijkstra — Pure Function, No Abstractions
The pathfinding algorithm is a plain function in `graph/algorithms/dijkstra.py`:

```python
def dijkstra(graph: GraphStore, source: str, destination: str) -> tuple[list[str], float]:
    ...
```

No strategy pattern, no class hierarchy. If a different algorithm is needed (A*, Bellman-Ford), it becomes a new function in the same package — simple and readable.

---

## 5. Setting Up the Project

### Prerequisites
- **Python 3.11+**
- **PostgreSQL 14+** running locally (or via Docker)
- `pip` / `uv`

---

### Option A — One-command setup (recommended)

```bash
# From the app/ directory
chmod +x script.sh && ./script.sh
```

This script:
1. Creates `.env` from `.env.example` (if not already present)
2. Creates a Python virtual environment at `.venv/`
3. Installs all dependencies (`pip install -e ".[dev]"`)
4. Runs Alembic migrations (`alembic upgrade head`)
5. Starts the server on `http://localhost:8001`

---

### Option B — Manual step-by-step

```bash
# 1. Enter the app directory
cd network_route_optimizer/app

# 2. Copy environment config
cp .env.example .env
# → Edit DATABASE_URL if your Postgres credentials differ

# 3. Create and activate virtualenv
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# 4. Install dependencies
pip install -e ".[dev]"

# 5. Run database migrations
alembic upgrade head

# 6. Start the development server
uvicorn app.network_optimizer.main:app --host 0.0.0.0 --port 8001 --reload
```

---

### Environment Variables (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/network_route_optimizer` | PostgreSQL connection string |
| `APP_ENV` | `development` | Environment flag (`development` / `production`) |
| `APP_HOST` | `0.0.0.0` | Server bind host |
| `APP_PORT` | `8001` | Server port |
| `LOG_LEVEL` | `info` | Log verbosity (`debug`, `info`, `warning`, `error`) |
| `ROUTE_CACHE_ENABLED` | `true` | Enable in-memory route result cache |
| `ROUTE_CACHE_TTL_SECONDS` | `60` | Cache TTL in seconds |
| `ROUTE_CACHE_MAX_SIZE` | `256` | Max number of cached route results |

---

### Verify the Setup

```bash
# Health check
curl http://localhost:8001/health
# → {"status": "ok", "nodes": 0, "edges": 0}

# Swagger UI
open http://localhost:8001/docs

# ReDoc
open http://localhost:8001/redoc
```

---

### Running Tests

```bash
# Unit tests only (no DB needed — runs in < 1 second)
.venv/bin/pytest app/tests/unit/ -v

# Integration tests (requires Postgres running)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/nro_test \
  .venv/bin/pytest app/tests/integration/ -v

# All tests with coverage report
.venv/bin/pytest app/tests/ --cov=app --cov-report=term-missing
```

---

## 📡 API Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check + live graph stats |
| `POST` | `/nodes` | Add a server node |
| `GET` | `/nodes` | List all nodes |
| `DELETE` | `/nodes/{id}` | Delete a node (cascades to edges) |
| `POST` | `/edges` | Add a directed edge with latency (ms) |
| `GET` | `/edges` | List all edges |
| `DELETE` | `/edges/{id}` | Delete an edge |
| `POST` | `/routes/shortest` | Compute shortest path (Dijkstra) |
| `GET` | `/routes/history` | Query history — supports `?source=`, `?destination=`, `?limit=`, `?date_from=`, `?date_to=` |

> Import `network_route_optimizer.postman_collection.json` into Postman for all requests pre-configured.
