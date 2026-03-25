"""
graph/algorithms/dijkstra.py — Shortest-path algorithm.

A plain function (no class hierarchy). Takes a GraphStore and returns the
shortest path + total latency using a binary min-heap.

Algorithm: Dijkstra's (optimal for positive-weight directed graphs)
Time:  O((V + E) log V)
Space: O(V + E)
"""
import heapq

from app.network_optimizer.graph.store import GraphStore


class NoPathError(Exception):
    """Raised when no path exists between source and destination."""
    pass


def dijkstra(
    graph: GraphStore,
    source: str,
    destination: str,
) -> tuple[list[str], float]:
    """
    Find the shortest path by total latency.

    Returns:
        (path, total_latency) where path is an ordered list of node names.

    Raises:
        NoPathError: if no path exists between source and destination.

    Steps:
    1. Priority queue: (distance, node) — always expand the closest node first.
    2. Relax each outgoing edge: if new distance < known distance, update.
    3. Reconstruct path by walking `prev` dict backwards from destination.
    """
    INF = float("inf")

    dist: dict[str, float] = {source: 0.0}
    prev: dict[str, str | None] = {source: None}
    visited: set[str] = set()
    heap: list[tuple[float, str]] = [(0.0, source)]

    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)

        if u == destination:
            break

        for neighbor, weight in graph.neighbors(u):
            new_dist = d + weight
            if new_dist < dist.get(neighbor, INF):
                dist[neighbor] = new_dist
                prev[neighbor] = u
                heapq.heappush(heap, (new_dist, neighbor))

    if destination not in visited:
        raise NoPathError(
            f"No path exists between '{source}' and '{destination}'."
        )

    # Reconstruct ordered path
    path: list[str] = []
    node: str | None = destination
    while node is not None:
        path.append(node)
        node = prev.get(node)
    path.reverse()

    return path, round(dist[destination], 4)
