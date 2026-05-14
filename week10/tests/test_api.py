import json
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app


@pytest.fixture
def app():
    app = create_app("development")
    app.config["TESTING"] = True
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def get_token(client, username="alice", password="alice123"):
    resp = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    return resp.get_json()["token"]


def get_admin_token(client):
    return get_token(client, username="admin", password="admin123")


class TestHealth:
    def test_liveness(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.get_json()["status"] == "healthy"

    def test_readiness(self, client):
        r = client.get("/ready")
        assert r.status_code == 200
        assert r.get_json()["ready"] is True

    def test_status(self, client):
        r = client.get("/status")
        data = r.get_json()
        assert r.status_code == 200
        assert "uptime_seconds" in data
        assert "circuit_breakers" in data

    def test_metrics_endpoint(self, client):
        r = client.get("/metrics")
        assert r.status_code == 200
        assert b"http_requests_total" in r.data


class TestAuth:
    def test_login_success(self, client):
        r = client.post("/api/auth/login", json={"username": "alice", "password": "alice123"})
        assert r.status_code == 200
        data = r.get_json()
        assert "token" in data
        assert data["role"] == "user"

    def test_login_invalid_password(self, client):
        r = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
        assert r.status_code == 401

    def test_login_missing_fields(self, client):
        r = client.post("/api/auth/login", json={})
        assert r.status_code == 400

    def test_verify_valid_token(self, client):
        token = get_token(client)
        r = client.get("/api/auth/verify", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.get_json()["valid"] is True

    def test_verify_no_token(self, client):
        r = client.get("/api/auth/verify")
        assert r.status_code == 400


class TestProducts:
    def test_list_products_public(self, client):
        r = client.get("/api/products")
        assert r.status_code == 200
        assert "products" in r.get_json()

    def test_get_product_exists(self, client):
        r = client.get("/api/products/1")
        assert r.status_code == 200
        assert r.get_json()["id"] == 1

    def test_get_product_not_found(self, client):
        r = client.get("/api/products/9999")
        assert r.status_code == 404

    def test_create_product_requires_auth(self, client):
        r = client.post("/api/products", json={"name": "X", "price": 10})
        assert r.status_code == 401

    def test_create_product_user_forbidden(self, client):
        token = get_token(client)   # user role
        r = client.post(
            "/api/products",
            json={"name": "X", "price": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403

    def test_create_product_admin_success(self, client):
        token = get_admin_token(client)
        r = client.post(
            "/api/products",
            json={"name": "Test Widget", "price": 9.99, "stock": 10},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201
        data = r.get_json()
        assert data["name"] == "Test Widget"

    def test_create_product_missing_fields(self, client):
        token = get_admin_token(client)
        r = client.post(
            "/api/products",
            json={"name": "No Price"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400


class TestSecurityHeaders:
    def test_security_headers_present(self, client):
        r = client.get("/health")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"
        assert r.headers.get("X-Frame-Options") == "DENY"
        assert r.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "X-Request-ID" in r.headers

    def test_server_header_hidden(self, client):
        r = client.get("/health")
        assert "Server" not in r.headers or r.headers.get("Server") != "Werkzeug"


class TestWAF:
    def test_waf_blocks_sql_injection(self, client):
        r = client.get("/api/products?name=1%20SELECT%20*%20FROM%20users")
        assert r.status_code == 400
        assert "WAF" in r.get_json()["error"]

    def test_waf_blocks_xss(self, client):
        r = client.get("/api/products?q=<script>alert(1)</script>")
        assert r.status_code == 400
