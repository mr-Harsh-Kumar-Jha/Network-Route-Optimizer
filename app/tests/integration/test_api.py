"""
tests/integration/test_api.py — Integration tests for all API endpoints.
Requires a running Postgres (see conftest.py / .env).
"""
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_graph():
    from graph.store import GraphStore
    GraphStore().reset()
    yield
    GraphStore().reset()


class TestNodesAPI:
    def test_add_node(self, client):
        r = client.post("/nodes", json={"name": "ServerA"})
        assert r.status_code == 201
        assert r.json()["name"] == "ServerA"

    def test_duplicate_node_400(self, client):
        client.post("/nodes", json={"name": "Dup"})
        assert client.post("/nodes", json={"name": "Dup"}).status_code == 400

    def test_blank_name_422(self, client):
        assert client.post("/nodes", json={"name": "   "}).status_code == 422

    def test_list_nodes(self, client):
        client.post("/nodes", json={"name": "N1"})
        r = client.get("/nodes")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestEdgesAPI:
    def _nodes(self, client, *names):
        for n in names:
            client.post("/nodes", json={"name": n})

    def test_add_edge(self, client):
        self._nodes(client, "A", "B")
        r = client.post("/edges", json={"source": "A", "destination": "B", "latency": 12.5})
        assert r.status_code == 201
        assert r.json()["latency"] == 12.5

    def test_zero_latency_422(self, client):
        self._nodes(client, "C", "D")
        assert client.post("/edges", json={"source":"C","destination":"D","latency":0}).status_code == 422

    def test_negative_latency_422(self, client):
        self._nodes(client, "E", "F")
        assert client.post("/edges", json={"source":"E","destination":"F","latency":-1}).status_code == 422

    def test_unknown_node_400(self, client):
        assert client.post("/edges", json={"source":"Ghost","destination":"A","latency":5}).status_code == 400

    def test_same_src_dest_422(self, client):
        self._nodes(client, "G")
        assert client.post("/edges", json={"source":"G","destination":"G","latency":5}).status_code == 422


class TestRoutesAPI:
    def _setup(self, client):
        for n in ["SA","SB","SC","SD"]:
            client.post("/nodes", json={"name": n})
        client.post("/edges", json={"source":"SA","destination":"SB","latency":10.0})
        client.post("/edges", json={"source":"SB","destination":"SD","latency":13.4})
        client.post("/edges", json={"source":"SA","destination":"SC","latency":25.0})
        client.post("/edges", json={"source":"SC","destination":"SD","latency":5.0})

    def test_shortest_path(self, client):
        self._setup(client)
        r = client.post("/routes/shortest", json={"source":"SA","destination":"SD"})
        assert r.status_code == 200
        d = r.json()
        assert d["path"] == ["SA","SB","SD"]
        assert abs(d["total_latency"] - 23.4) < 0.001
        assert d["hops"] == 2

    def test_no_path_404(self, client):
        for n in ["X1","X2"]:
            client.post("/nodes", json={"name": n})
        assert client.post("/routes/shortest", json={"source":"X1","destination":"X2"}).status_code == 404

    def test_unknown_node_400(self, client):
        assert client.post("/routes/shortest", json={"source":"Ghost","destination":"Also"}).status_code == 400

    def test_same_src_dest_400(self, client):
        client.post("/nodes", json={"name": "Same"})
        assert client.post("/routes/shortest", json={"source":"Same","destination":"Same"}).status_code == 400

    def test_history_logged(self, client):
        self._setup(client)
        client.post("/routes/shortest", json={"source":"SA","destination":"SD"})
        r = client.get("/routes/history")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_history_filter(self, client):
        self._setup(client)
        client.post("/routes/shortest", json={"source":"SA","destination":"SD"})
        r = client.get("/routes/history", params={"source": "SA"})
        assert all(rec["source"] == "SA" for rec in r.json())
