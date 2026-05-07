"""
core/database.py
----------------
In-memory database shared across all API versions.
In production, replace with SQLAlchemy + PostgreSQL.
"""

import uuid
import datetime
from typing import Optional

# ── Shared in-memory stores ────────────────────────────────────────────────
payments_db: dict[str, dict] = {}          # payment_id → payment record
idempotency_store: dict[str, str] = {}     # idempotency_key → payment_id
users_db: dict[str, dict] = {}            # user_id → user record
audit_log: list[dict] = []                # append-only audit trail


# ── Constants ─────────────────────────────────────────────────────────────
SUPPORTED_CURRENCIES = {"VND", "USD", "EUR", "SGD", "JPY", "GBP"}

PAYMENT_STATUS_MACHINE = {
    "pending":    ["processing", "cancelled"],
    "processing": ["completed", "failed"],
    "completed":  [],
    "failed":     ["pending"],   # allow retry
    "cancelled":  [],
}

PAYMENT_METHODS = {"card", "bank_transfer", "e_wallet", "qr_code"}


# ── Helpers ───────────────────────────────────────────────────────────────
def now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def append_audit(action: str, resource: str, resource_id: str,
                 actor: str = "system", metadata: dict = None):
    audit_log.append({
        "id":          new_id("audit_"),
        "timestamp":   now_iso(),
        "action":      action,
        "resource":    resource,
        "resource_id": resource_id,
        "actor":       actor,
        "metadata":    metadata or {},
    })


# ── Seed data so demos work out-of-the-box ────────────────────────────────
def seed():
    if payments_db:
        return  # already seeded

    samples = [
        {"amount_cents": 5000000, "currency": "VND",
         "description": "Order #1001", "method": "card",
         "status": "completed"},
        {"amount_cents": 1200,    "currency": "USD",
         "description": "Subscription renewal", "method": "bank_transfer",
         "status": "pending"},
        {"amount_cents": 8500000, "currency": "VND",
         "description": "Order #1002", "method": "e_wallet",
         "status": "processing"},
        {"amount_cents": 2500,    "currency": "EUR",
         "description": "Service fee", "method": "card",
         "status": "failed"},
        {"amount_cents": 300000,  "currency": "VND",
         "description": "Top-up", "method": "qr_code",
         "status": "completed"},
    ]
    for s in samples:
        pid = new_id("pay_")
        payments_db[pid] = {
            "id":               pid,
            "amount_cents":     s["amount_cents"],
            "currency":         s["currency"],
            "description":      s["description"],
            "payment_method":   s["method"],
            "status":           s["status"],
            "idempotency_key":  None,
            "metadata":         {},
            "created_at":       now_iso(),
            "updated_at":       now_iso(),
        }

    # Seed one user
    uid = new_id("usr_")
    users_db[uid] = {
        "id":         uid,
        "name":       "Demo User",
        "email":      "demo@example.com",
        "created_at": now_iso(),
    }