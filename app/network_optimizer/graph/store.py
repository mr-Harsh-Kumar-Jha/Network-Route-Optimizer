"""
graph/store.py — In-memory graph store (Singleton with read-write lock).

Holds the network graph as an adjacency list in memory for fast pathfinding.
Postgres is the source of truth; this is loaded from DB on startup and kept
in sync on every mutation (add/remove node or edge).

Thread-safety:
  - Multiple concurrent reads (pathfinding) allowed simultaneously.
  - Mutations (add/remove) acquire an exclusive write lock.
"""
from __future__ import annotations

import threading


class _RWLock:
    """Simple readers-writer lock allowing concurrent reads, exclusive writes."""

    def __init__(self) -> None:
        self._read_ready = threading.Condition(threading.Lock())
        self._readers: int = 0

    def acquire_read(self) -> None:
        with self._read_ready:
            self._readers += 1

    def release_read(self) -> None:
        with self._read_ready:
            self._readers -= 1
            if self._readers == 0:
                self._read_ready.notify_all()

    def acquire_write(self) -> None:
        self._read_ready.acquire()
        while self._readers > 0:
            self._read_ready.wait()

    def release_write(self) -> None:
        self._read_ready.release()


class _ReadCtx:
    def __init__(self, lock: _RWLock) -> None:
        self._lock = lock

    def __enter__(self):
        self._lock.acquire_read()

    def __exit__(self, *_):
        self._lock.release_read()


class _WriteCtx:
    def __init__(self, lock: _RWLock) -> None:
        self._lock = lock

    def __enter__(self):
        self._lock.acquire_write()

    def __exit__(self, *_):
        self._lock.release_write()


class GraphStore:
    """
    Thread-safe in-memory adjacency list for the network graph.

    Structure:
        _nodes : set[str]
        _adj   : dict[str, list[tuple[str, float]]]   {node → [(neighbor, latency)]}

    Singleton — one instance across the entire application.
    """

    _instance: "GraphStore | None" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "GraphStore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._nodes: set[str] = set()
                    inst._adj: dict[str, list[tuple[str, float]]] = {}
                    inst._rw = _RWLock()
                    cls._instance = inst
        return cls._instance

    # ── Context helpers ───────────────────────────────────────────────────────
    def _reading(self) -> _ReadCtx:
        return _ReadCtx(self._rw)

    def _writing(self) -> _WriteCtx:
        return _WriteCtx(self._rw)

    # ── Node operations ───────────────────────────────────────────────────────
    def add_node(self, name: str) -> None:
        with self._writing():
            if name not in self._nodes:
                self._nodes.add(name)
                self._adj[name] = []

    def remove_node(self, name: str) -> None:
        with self._writing():
            self._nodes.discard(name)
            self._adj.pop(name, None)
            for src in self._adj:
                self._adj[src] = [(d, w) for d, w in self._adj[src] if d != name]

    def has_node(self, name: str) -> bool:
        with self._reading():
            return name in self._nodes

    def all_nodes(self) -> list[str]:
        with self._reading():
            return list(self._nodes)

    # ── Edge operations ───────────────────────────────────────────────────────
    def add_edge(self, src: str, dst: str, weight: float) -> None:
        with self._writing():
            # Upsert: remove existing edge then re-add
            self._adj[src] = [(d, w) for d, w in self._adj[src] if d != dst]
            self._adj[src].append((dst, weight))

    def remove_edge(self, src: str, dst: str) -> bool:
        with self._writing():
            before = len(self._adj.get(src, []))
            self._adj[src] = [(d, w) for d, w in self._adj.get(src, []) if d != dst]
            return len(self._adj[src]) < before

    def has_edge(self, src: str, dst: str) -> bool:
        with self._reading():
            return any(d == dst for d, _ in self._adj.get(src, []))

    def neighbors(self, node: str) -> list[tuple[str, float]]:
        with self._reading():
            return list(self._adj.get(node, []))

    # ── Bulk load (startup) ───────────────────────────────────────────────────
    def load(self, nodes: list[str], edges: list[tuple[str, str, float]]) -> None:
        """Atomic replace — called once on application startup."""
        with self._writing():
            self._nodes = set(nodes)
            self._adj = {n: [] for n in nodes}
            for src, dst, w in edges:
                if src in self._adj:
                    self._adj[src].append((dst, w))

    def reset(self) -> None:
        """Wipe graph — used in tests to isolate the singleton."""
        with self._writing():
            self._nodes.clear()
            self._adj.clear()

    # ── Stats ─────────────────────────────────────────────────────────────────
    def node_count(self) -> int:
        with self._reading():
            return len(self._nodes)

    def edge_count(self) -> int:
        with self._reading():
            return sum(len(v) for v in self._adj.values())
