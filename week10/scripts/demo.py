#!/usr/bin/env python3
import json
import time
import requests

BASE = "http://localhost:5000"
DIVIDER = "─" * 60


def section(title):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print('═' * 60)


def show(label, resp):
    print(f"\n[{resp.status_code}] {label}")
    print(DIVIDER)
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text[:300])
    for h in ["X-RateLimit-Remaining", "X-RateLimit-Limit", "Retry-After"]:
        if h in resp.headers:
            print(f"  Header  {h}: {resp.headers[h]}")


section("1. Health & Observability")
show("Liveness probe", requests.get(f"{BASE}/health"))
show("Readiness probe", requests.get(f"{BASE}/ready"))
show("Status dashboard", requests.get(f"{BASE}/status"))

section("2. Prometheus Metrics (first 15 lines)")
resp = requests.get(f"{BASE}/metrics")
lines = resp.text.splitlines()
for line in lines[:15]:
    print(line)
print("  ... (truncated)")

section("3. Authentication")
show("Login — valid user", requests.post(f"{BASE}/api/auth/login",
    json={"username": "alice", "password": "alice123"}))

token_resp = requests.post(f"{BASE}/api/auth/login",
    json={"username": "admin", "password": "admin123"})
admin_token = token_resp.json()["token"]
user_token_resp = requests.post(f"{BASE}/api/auth/login",
    json={"username": "alice", "password": "alice123"})
user_token = user_token_resp.json()["token"]

show("Login — wrong password", requests.post(f"{BASE}/api/auth/login",
    json={"username": "alice", "password": "wrong"}))
show("Token verify — valid", requests.get(f"{BASE}/api/auth/verify",
    headers={"Authorization": f"Bearer {user_token}"}))
show("Token verify — invalid", requests.get(f"{BASE}/api/auth/verify",
    headers={"Authorization": "Bearer bad.token.here"}))

section("4. Products API — Public Endpoints")
show("List all products", requests.get(f"{BASE}/api/products"))
show("Get product #1 (with circuit breaker)", requests.get(f"{BASE}/api/products/1"))
show("Get non-existent product", requests.get(f"{BASE}/api/products/9999"))

section("5. Products API — Protected Endpoints (JWT + RBAC)")
show("Create product — no token (401)",
    requests.post(f"{BASE}/api/products", json={"name": "X", "price": 1}))
show("Create product — user role (403)",
    requests.post(f"{BASE}/api/products",
        json={"name": "X", "price": 1},
        headers={"Authorization": f"Bearer {user_token}"}))
show("Create product — admin role (201)",
    requests.post(f"{BASE}/api/products",
        json={"name": "Demo Widget", "price": 19.99, "stock": 5},
        headers={"Authorization": f"Bearer {admin_token}"}))

section("6. WAF — Injection Blocking")
show("SQL injection attempt",
    requests.get(f"{BASE}/api/products?name=1 SELECT * FROM users"))
show("XSS attempt",
    requests.get(f"{BASE}/api/products?q=<script>alert(1)</script>"))

section("7. Rate Limiting Demo (10 rapid requests to /api/products)")
for i in range(12):
    r = requests.get(f"{BASE}/api/products")
    remaining = r.headers.get("X-RateLimit-Remaining", "?")
    print(f"  Request {i+1:2d}: HTTP {r.status_code}  remaining={remaining}")
    if r.status_code == 429:
        print(f"  ← Rate limit kicked in!")
        break
    time.sleep(0.05)

section("8. Circuit Breaker Demo (calling flaky inventory service repeatedly)")
success = fail = open_count = 0
for i in range(15):
    r = requests.get(f"{BASE}/api/products/1")
    data = r.json()
    cb = data.get("circuit_breaker", "?")
    src = data.get("stock_info", {}).get("source", "?")
    print(f"  Call {i+1:2d}: HTTP {r.status_code}  circuit={cb}  stock_source={src}")
    if cb == "open":
        open_count += 1
    time.sleep(0.1)

print(f"\n  Circuit opened {open_count} time(s) during the demo.")

print(f"\n\n{'═'*60}")
print("  Demo complete! Check logs/app.log and logs/audit.log")
print('═'*60)
