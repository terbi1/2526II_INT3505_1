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
    }


@v1_bp.route("/payments", methods=["GET"])
@deprecated("v1")
def list_payments():
  
    status_filter = request.args.get("status")
    payments = list(payments_db.values())
    if status_filter:
        payments = [p for p in payments if p["status"] == status_filter]

    return ok({"payments": [_serialise(p) for p in payments]})


@v1_bp.route("/payments", methods=["POST"])
@deprecated("v1")
def create_payment():
    
    body = request.get_json(silent=True) or {}

    field_errors = collect_errors({
        "amount": (body.get("amount"), validate_amount_float),
    })
    if field_errors:
        return validation_error(field_errors)

    pid = new_id("pay_")
    record = {
        "id":               pid,
        "amount_cents":     int(float(body["amount"]) * 100),
        "currency":         "VND",      
        "description":      body.get("description", ""),
        "payment_method":   "card",     
        "status":           "pending",
        "idempotency_key":  None,       
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
    
    p = payments_db.get(payment_id)
    if not p:
        return not_found("Payment", payment_id)
    return ok(_serialise(p))


@v1_bp.route("/payments/<payment_id>", methods=["DELETE"])
@deprecated("v1")
def delete_payment(payment_id: str):
    
    p = payments_db.get(payment_id)
    if not p:
        return not_found("Payment", payment_id)
    del payments_db[payment_id]
    append_audit("delete", "payment", payment_id, metadata={"version": "v1"})
    return "", 204