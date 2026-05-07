"""
api/v1/payments.py
------------------
Payment API — Version 1  (DEPRECATED)

Known limitations that drove the v2 redesign
---------------------------------------------
* `amount` is a floating-point number  →  precision loss for large values
* `currency` is hard-coded to VND      →  no multi-currency support
* No idempotency support               →  duplicate charges on retry
* No `payment_method` field
* Pagination not supported on list endpoint
* Status transitions not validated server-side

All endpoints in this module carry the @deprecated("v1") decorator which
automatically attaches RFC 8594 Deprecation / Sunset / Link headers to
every response.
"""

from flask import Blueprint, request

from utils.database import (
    PAYMENT_STATUS_MACHINE, append_audit, new_id, now_iso, payments_db,
)
from utils.responses import (
    created, err, not_found, ok, validation_error,
)
from utils.validators import collect_errors, validate_amount_float
from utils.versioning import deprecated

v1_bp = Blueprint("v1", __name__, url_prefix="/api/v1")


# ── Serialiser ────────────────────────────────────────────────────────────

def _serialise(p: dict) -> dict:
    """
    V1 wire format.
    NOTE: amount returned as float — the known precision bug.
    """
    return {
        "id":          p["id"],
        "amount":      round(p["amount_cents"] / 100, 2),   # ⚠ float
        "status":      p["status"],
        "description": p.get("description", ""),
        "created_at":  p["created_at"],
        # ── Missing in v1 (added in v2) ───────────────────────────────
        # "currency":         p["currency"],
        # "payment_method":   p["payment_method"],
        # "idempotency_key":  p["idempotency_key"],
        # "metadata":         p["metadata"],
        # "updated_at":       p["updated_at"],
    }


# ── Endpoints ─────────────────────────────────────────────────────────────

@v1_bp.route("/payments", methods=["GET"])
@deprecated("v1")
def list_payments():
    """
    [V1 · DEPRECATED]  List all payments.

    Query params:
      status  — filter by status string

    Response shape (v1):
      { data: { payments: [ {id, amount(float), status, description,
                              created_at} ] } }

    Migration note:
      Use GET /api/v2/payments which adds pagination, currency filter,
      and richer payment objects.
    ---
    tags:
      - Payments (v1 — deprecated)
    parameters:
      - name: status
        in: query
        schema:
          type: string
    responses:
      200:
        description: List of payments
    """
    status_filter = request.args.get("status")
    payments = list(payments_db.values())
    if status_filter:
        payments = [p for p in payments if p["status"] == status_filter]

    return ok({"payments": [_serialise(p) for p in payments]})


@v1_bp.route("/payments", methods=["POST"])
@deprecated("v1")
def create_payment():
    """
    [V1 · DEPRECATED]  Create a payment.

    Request body (v1):
      { amount: <float>, description?: <string> }

    Breaking changes in v2:
      • amount  →  integer (cents)
      • currency  →  required
      • Idempotency-Key header supported
    ---
    tags:
      - Payments (v1 — deprecated)
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [amount]
            properties:
              amount:
                type: number
                example: 150000.50
              description:
                type: string
    responses:
      201:
        description: Payment created
      422:
        description: Validation error
    """
    body = request.get_json(silent=True) or {}

    # ── Validation (v1 style — minimal) ───────────────────────────────
    field_errors = collect_errors({
        "amount": (body.get("amount"), validate_amount_float),
    })
    if field_errors:
        return validation_error(field_errors)

    pid = new_id("pay_")
    record = {
        "id":               pid,
        "amount_cents":     int(float(body["amount"]) * 100),
        "currency":         "VND",      # ⚠ hard-coded in v1
        "description":      body.get("description", ""),
        "payment_method":   "card",     # ⚠ hard-coded in v1
        "status":           "pending",
        "idempotency_key":  None,       # ⚠ not supported in v1
        "metadata":         {},
        "created_at":       now_iso(),
        "updated_at":       now_iso(),
    }
    payments_db[pid] = record
    append_audit("create", "payment", pid, metadata={"version": "v1"})

    return created(_serialise(record))


@v1_bp.route("/payments/<payment_id>", methods=["GET"])
@deprecated("v1")
def get_payment(payment_id: str):
    """
    [V1 · DEPRECATED]  Retrieve a single payment.
    ---
    tags:
      - Payments (v1 — deprecated)
    parameters:
      - name: payment_id
        in: path
        required: true
        schema:
          type: string
    responses:
      200:
        description: Payment detail
      404:
        description: Not found
    """
    p = payments_db.get(payment_id)
    if not p:
        return not_found("Payment", payment_id)
    return ok(_serialise(p))


@v1_bp.route("/payments/<payment_id>", methods=["DELETE"])
@deprecated("v1")
def delete_payment(payment_id: str):
    """
    [V1 · DEPRECATED]  Hard-delete a payment (removed in v2 — use PATCH status=cancelled).
    ---
    tags:
      - Payments (v1 — deprecated)
    parameters:
      - name: payment_id
        in: path
        required: true
        schema:
          type: string
    responses:
      204:
        description: Deleted
      404:
        description: Not found
    """
    p = payments_db.get(payment_id)
    if not p:
        return not_found("Payment", payment_id)
    del payments_db[payment_id]
    append_audit("delete", "payment", payment_id, metadata={"version": "v1"})
    return "", 204