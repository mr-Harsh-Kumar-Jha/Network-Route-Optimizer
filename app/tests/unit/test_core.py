"""
tests/unit/test_core.py — Unit tests for graph engine and Dijkstra.
No database needed. All tests run in pure memory.
"""
import pytest

from graph.algorithms.dijkstra import NoPathError, dijkstra
from graph.store import GraphStore


@pytest.fixture(autouse=True)
def fresh_graph():
    g = GraphStore()
    g.reset()
    yield g
    g.reset()


# ── Dijkstra happy path ───────────────────────────────────────────────────────

class TestDijkstra:
    def test_single_hop(self, fresh_graph):
        g = fresh_graph
        g.add_node("A"); g.add_node("B")
        g.add_edge("A", "B", 10.0)
        path, latency = dijkstra(g, "A", "B")
        assert path == ["A", "B"]
        assert latency == 10.0

    def test_shortest_of_two_paths(self, fresh_graph):
        g = fresh_graph
        for n in ["A", "B", "C", "D"]:
            g.add_node(n)
        g.add_edge("A", "B", 10.0)
        g.add_edge("B", "D", 13.4)
        g.add_edge("A", "C", 25.0)
        g.add_edge("C", "D", 5.0)
        path, latency = dijkstra(g, "A", "D")
        assert path == ["A", "B", "D"]
        assert abs(latency - 23.4) < 1e-4

    def test_path_starts_at_source_ends_at_dest(self, fresh_graph):
        g = fresh_graph
        for n in ["S", "M", "E"]:
            g.add_node(n)
        g.add_edge("S", "M", 5.0); g.add_edge("M", "E", 7.0)
        path, _ = dijkstra(g, "S", "E")
        assert path[0] == "S" and path[-1] == "E"

    def test_no_path_raises(self, fresh_graph):
        g = fresh_graph
        g.add_node("A"); g.add_node("B")
        with pytest.raises(NoPathError):
            dijkstra(g, "A", "B")

    def test_directed_no_reverse(self, fresh_graph):
        g = fresh_graph
        g.add_node("A"); g.add_node("B")
        g.add_edge("A", "B", 5.0)
        with pytest.raises(NoPathError):
            dijkstra(g, "B", "A")

    def test_isolated_node_unreachable(self, fresh_graph):
        g = fresh_graph
        for n in ["A", "B", "C"]:
            g.add_node(n)
        g.add_edge("A", "B", 3.0)
        with pytest.raises(NoPathError):
            dijkstra(g, "A", "C")


# ── GraphStore ────────────────────────────────────────────────────────────────

class TestGraphStore:
    def test_singleton(self):
        assert GraphStore() is GraphStore()

    def test_add_has_node(self, fresh_graph):
        fresh_graph.add_node("X")
        assert fresh_graph.has_node("X")
        assert not fresh_graph.has_node("Y")

    def test_add_has_edge(self, fresh_graph):
        fresh_graph.add_node("A"); fresh_graph.add_node("B")
        fresh_graph.add_edge("A", "B", 5.0)
        assert fresh_graph.has_edge("A", "B")
        assert not fresh_graph.has_edge("B", "A")

    def test_remove_node_removes_edges(self, fresh_graph):
        fresh_graph.add_node("A"); fresh_graph.add_node("B")
        fresh_graph.add_edge("A", "B", 3.0)
        fresh_graph.remove_node("B")
        assert not fresh_graph.has_node("B")
        assert not fresh_graph.has_edge("A", "B")

    def test_edge_upsert(self, fresh_graph):
        fresh_graph.add_node("A"); fresh_graph.add_node("B")
        fresh_graph.add_edge("A", "B", 10.0)
        fresh_graph.add_edge("A", "B", 5.0)  # upsert — should replace
        latencies = [w for _, w in fresh_graph.neighbors("A") if _ == "B"]
        assert latencies == [5.0]

    def test_bulk_load(self, fresh_graph):
        fresh_graph.load(nodes=["X","Y","Z"], edges=[("X","Y",1.0),("Y","Z",2.0)])
        assert fresh_graph.node_count() == 3
        assert fresh_graph.edge_count() == 2
