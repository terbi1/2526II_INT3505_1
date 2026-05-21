"""
models/database.py
------------------
Database giả lập bằng dict/list để tập trung vào API patterns,
không phải database setup. Trong thực tế thay bằng SQLAlchemy.
"""

from datetime import datetime
import uuid


def new_id():
    return str(uuid.uuid4())[:8]


def now():
    return datetime.utcnow().isoformat() + 'Z'


# ── PRODUCTS (dùng cho CRUD + Query patterns) ──────────────────────────────
products_db = {
    "p001": {"id": "p001", "name": "iPhone 15", "category": "electronics",
             "price": 999.0, "stock": 50, "rating": 4.5, "created_at": now()},
    "p002": {"id": "p002", "name": "MacBook Pro", "category": "electronics",
             "price": 2499.0, "stock": 20, "rating": 4.8, "created_at": now()},
    "p003": {"id": "p003", "name": "Nike Air Max", "category": "shoes",
             "price": 120.0, "stock": 100, "rating": 4.2, "created_at": now()},
    "p004": {"id": "p004", "name": "Python Book", "category": "books",
             "price": 45.0, "stock": 200, "rating": 4.7, "created_at": now()},
    "p005": {"id": "p005", "name": "Desk Chair", "category": "furniture",
             "price": 350.0, "stock": 15, "rating": 4.0, "created_at": now()},
}

# ── ORDERS (dùng cho HATEOAS pattern) ──────────────────────────────────────
# Mỗi order có state machine: pending → paid → shipped → delivered
orders_db = {
    "o001": {"id": "o001", "product_id": "p001", "quantity": 1,
             "status": "pending", "total": 999.0, "user_id": "u001",
             "created_at": now()},
    "o002": {"id": "o002", "product_id": "p002", "quantity": 1,
             "status": "paid", "total": 2499.0, "user_id": "u002",
             "created_at": now()},
    "o003": {"id": "o003", "product_id": "p003", "quantity": 2,
             "status": "shipped", "total": 240.0, "user_id": "u001",
             "created_at": now()},
}

# ── EVENTS (dùng cho Event-driven pattern) ─────────────────────────────────
events_db = []        # event log / event store
event_bus = {}        # topic -> list of subscriber callbacks (in-memory)

# ── WEBHOOKS (dùng cho Webhook pattern) ────────────────────────────────────
webhooks_db = {}      # id -> webhook subscription
webhook_deliveries = []  # lịch sử delivery

# ── NOTIFICATIONS (kết hợp Event + Webhook) ────────────────────────────────
notifications_db = []
