"""
Tests for the CORTEX REST API server.

Uses FastAPI's TestClient (httpx-based) for synchronous testing.
"""

import os
import pytest
from fastapi.testclient import TestClient

# Use in-memory DB for tests
os.environ["CORTEX_DB_PATH"] = ":memory:"

from server.cortex_server import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.4.0"
        assert "uptime" in data


class TestMemoryStore:
    def test_store_semantic(self, client):
        resp = client.post("/memory/store", json={
            "type": "semantic",
            "content": "Paris is the capital of France",
            "importance": 0.8,
            "tags": ["geography", "facts"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "semantic"
        assert "id" in data
        assert "stored_at" in data

    def test_store_episodic(self, client):
        resp = client.post("/memory/store", json={
            "type": "episodic",
            "content": "Had a meeting about CORTEX integration",
        })
        assert resp.status_code == 200
        assert resp.json()["type"] == "episodic"

    def test_store_working(self, client):
        resp = client.post("/memory/store", json={
            "type": "working",
            "content": "Current task: build REST API",
        })
        assert resp.status_code == 200
        assert resp.json()["type"] == "working"

    def test_store_invalid_type(self, client):
        resp = client.post("/memory/store", json={
            "type": "invalid_type",
            "content": "This should fail",
        })
        assert resp.status_code == 400


class TestMemoryRecall:
    def test_store_and_recall(self, client):
        # Store first
        client.post("/memory/store", json={
            "type": "semantic",
            "content": "Python is a programming language created by Guido van Rossum",
            "importance": 0.9,
        })
        client.post("/memory/store", json={
            "type": "semantic",
            "content": "FastAPI is a modern Python web framework",
            "importance": 0.7,
        })

        # Recall
        resp = client.post("/memory/recall", json={
            "query": "Python programming",
            "limit": 5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        # Should find at least one match
        assert len(data["results"]) >= 1

    def test_recall_with_type_filter(self, client):
        client.post("/memory/store", json={
            "type": "episodic",
            "content": "Deployed CORTEX v0.4.0 today",
        })
        resp = client.post("/memory/recall", json={
            "query": "CORTEX deployment",
            "types": ["episodic"],
        })
        assert resp.status_code == 200


class TestConsolidate:
    def test_consolidate(self, client):
        # Store some working memories first
        for i in range(3):
            client.post("/memory/store", json={
                "type": "working",
                "content": f"Working memory item {i}",
            })
        resp = client.post("/memory/consolidate")
        assert resp.status_code == 200
        data = resp.json()
        assert "consolidated" in data
        assert "promoted" in data
        assert "forgotten" in data
        assert "duration_ms" in data


class TestEvolve:
    def test_evolve(self, client):
        resp = client.post("/memory/evolve", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "generation" in data
        assert "best_fitness" in data
        assert "strategy" in data

    def test_evolve_with_feedback(self, client):
        # Store something first
        store_resp = client.post("/memory/store", json={
            "type": "semantic",
            "content": "Test content for evolution feedback",
        })
        mid = store_resp.json()["id"]

        resp = client.post("/memory/evolve", json={
            "feedback": [
                {"query": "test", "result_id": mid, "score": 0.9},
            ],
        })
        assert resp.status_code == 200


class TestPromptAssemble:
    def test_assemble_basic(self, client):
        resp = client.post("/prompt/assemble", json={
            "query": "Explain how memory consolidation works",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "system_prompt" in data
        assert "user_prompt" in data
        assert "techniques" in data
        assert "complexity" in data
        assert "confidence" in data

    def test_assemble_with_role(self, client):
        resp = client.post("/prompt/assemble", json={
            "query": "Write a function to sort a list",
            "role": "coder",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["confidence"] > 0


class TestStats:
    def test_stats(self, client):
        resp = client.get("/memory/stats")
        assert resp.status_code == 200
        data = resp.json()
        for key in ["working", "episodic", "semantic", "procedural", "total", "evolution_generation"]:
            assert key in data


class TestGaps:
    def test_gaps(self, client):
        resp = client.get("/memory/gaps")
        assert resp.status_code == 200
        data = resp.json()
        assert "gaps" in data


class TestMCP:
    def test_mcp_tools_list(self, client):
        resp = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data
        tools = data["result"]["tools"]
        assert len(tools) >= 6
        tool_names = [t["name"] for t in tools]
        assert "cortex_store" in tool_names
        assert "cortex_recall" in tool_names

    def test_mcp_tools_call_store(self, client):
        resp = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "cortex_store",
                "arguments": {
                    "content": "MCP test memory",
                    "type": "semantic",
                },
            },
            "id": 2,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data
        assert "content" in data["result"]

    def test_mcp_resources_list(self, client):
        resp = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "resources/list",
            "params": {},
            "id": 3,
        })
        assert resp.status_code == 200
        data = resp.json()
        resources = data["result"]["resources"]
        assert len(resources) == 4

    def test_mcp_unknown_method(self, client):
        resp = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "unknown/method",
            "params": {},
            "id": 4,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
