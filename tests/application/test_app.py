"""
Tests for the Flask application instance in src/application/app.py.

Covers:
- The /healthz endpoint (lightweight Cloud Run liveness probe).
- Basic Dash server configuration.
"""
import json
import pytest

from src.application.app import server


@pytest.fixture
def client():
    """Flask test client."""
    server.config["TESTING"] = True
    with server.test_client() as c:
        yield c


# ══════════════════════════════════════════════
# /healthz endpoint
# ══════════════════════════════════════════════

class TestHealthCheckEndpoint:
    def test_healthz_returns_200(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200

    def test_healthz_body_contains_status_ok(self, client):
        response = client.get("/healthz")
        data = json.loads(response.data)
        assert data.get("status") == "ok"

    def test_healthz_content_type_is_json(self, client):
        response = client.get("/healthz")
        assert "application/json" in response.content_type

    def test_healthz_method_get_only(self, client):
        """POST to /healthz should not succeed (405 or 404)."""
        response = client.post("/healthz")
        assert response.status_code in (404, 405)

    def test_healthz_head_request(self, client):
        """HEAD /healthz should return 200 with no body."""
        response = client.head("/healthz")
        assert response.status_code == 200
        assert response.data == b""


# ══════════════════════════════════════════════
# Dash app configuration
# ══════════════════════════════════════════════

class TestDashAppConfiguration:
    def test_server_is_flask_app(self):
        """server must be the underlying Flask WSGI app, not the Dash instance."""
        from flask import Flask
        assert isinstance(server, Flask)

    def test_tts_adapter_is_exported(self):
        """tts_adapter must be importable from app.py for dependency injection."""
        from src.application.app import tts_adapter
        from src.ports.tts_port import ITTSPort
        assert isinstance(tts_adapter, ITTSPort)
