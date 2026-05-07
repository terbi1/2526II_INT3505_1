"""
api/v2/payments.py
------------------
Payment API — Version 2  (CURRENT / STABLE)

Improvements over v1
--------------------
1.  amount is now an **integer** (smallest currency unit, e.g. cents).
    Example: 50000 = 500.00 USD  |  5000000 = 50,000 VND
2.  currency is a **required** field.  Supported: VND USD EUR SGD JPY GBP
3.  **Idempotency** via Idempotency-Key request header.
    Send the same key twice → receive the same response, no duplicate charge.
4.  payment_method field added: card | bank_transfer | e_wallet | qr_code
5.  **Pagination** on list endpoint (page / per_page query params).
6.  Currency / status / method **filters** on list endpoint.
7.  **Server-side status transitions** validated against a state machine.
8.  metadata object for storing arbitrary key-value pairs.
9.  amount_formatted  — human-readable money string included in every response.
10. Hard-delete removed → use PATCH to set status=cancelled.
"""

import datetime

from flask import Blueprint, request

from utils.database import (
    PAYMENT_STATUS_MACHINE, append_audit, idempotency_store, new_id,
    now_iso, payments_db,
)
from utils.responses import (
    conflict, created, err, not_found, ok, validation_error,
)
from utils.validators import (
    collect_errors, validate_amount_cents, validate_currency,
    validate_idempotency_key, validate_payment_method,
)
from utils.versioning import active_version_headers

v2_bp = Blueprint("v2", __name__, url_prefix="/api/v2")


# ── Money formatter ───────────────────────────────────────────────────────

_CURRENCY_FMT = {
    "VND": ("₫",   0, "suffix"),
    "USD": ("$",   2, "prefix"),
    "EUR": ("€",   2, "prefix"),
    "SGD": ("S$",  2, "prefix"),
    "JPY": ("¥",   0, "prefix"),
    "GBP": ("£",   2, "prefix"),
}


def _fmt_money(cents: int, currency: str) -> str:
    sym, decimals, pos = _CURRENCY_FMT.get(currency, ("", 2, "prefix"))
    amount = cents / (10 ** decimals) if decimals else cents
    formatted = (f"{amount:,.{decimals}f}")
    return f"{formatted} {sym}" if pos == "suffix" else f"{sym}{formatted}"


# ── Serialiser ────────────────────────────────────────────────────────────

def _serialise(p: dict) -> dict:
    """V2 wire format — richer, precise, multi-currency."""
    return {
        "id":               p["id"],
        "amount":           p["amount_cents"],                   # ✅ integer
        "currency":         p["currency"],                       # ✅ present
        "amount_formatted": _fmt_money(p["amount_cents"],
                                       p["currency"]),           # ✅ human-readable
        "status":           p["status"],
        "payment_method":   p.get("payment_method", "card"),    # ✅ present
        "description":      p.get("description", ""),
        "idempotency_key":  p.get("idempotency_key"),           # ✅ present
        "metadata":         p.get("metadata", {}),              # ✅ present
        "created_at":       p["created_at"],
        "updated_at":       p.get("updated_at", p["created_at"]),# ✅ present
    }


# ── Endpoints ─────────────────────────────────────────────────────────────

@v2_bp.route("/payments", methods=["GET"])
@active_version_headers("v2")
def list_payments():
    """
    [V2]  List payments with filtering and pagination.

    Query params
    ------------
    page        int   default=1
    per_page    int   default=10, max=100
    status      str   pending|processing|completed|failed|cancelled
    currency    str   VND|USD|EUR|…
    method      str   card|bank_transfer|e_wallet|qr_code
    ---
    tags:
      - Payments (v2 — current)
    parameters:
      - {name: page,     in: query, schema: {type: integer, default: 1}}
      - {name: per_page, in: query, schema: {type: integer, default: 10}}
      - {name: status,   in: query, schema: {type: string}}
      - {name: currency, in: query, schema: {type: string}}
      - {name: method,   in: query, schema: {type: string}}
    responses:
      200:
        description: Paginated list of payments
    """
    page     = max(1, request.args.get("page",     1,  type=int))
    per_page = min(100, max(1, request.args.get("per_page", 10, type=int)))

    status_f   = request.args.get("status")
    currency_f = (request.args.get("currency") or "").upper() or None
    method_f   = request.args.get("method")

    items = list(payments_db.values())

    # Apply filters
    if status_f:
        items = [p for p in items if p["status"] == status_f]
    if currency_f:
        items = [p for p in items if p["currency"] == currency_f]
    if method_f:
        items = [p for p in items if p.get("payment_method") == method_f]

    # Sort newest first
    items.sort(key=lambda p: p["created_at"], reverse=True)

    total       = len(items)
    total_pages = max(1, -(-total // per_page))
    start       = (page - 1) * per_page
    page_items  = items[start: start + per_page]

    return ok(
        {"payments": [_serialise(p) for p in page_items]},
        meta={
            "pagination": {
                "page":        page,
                "per_page":    per_page,
                "total":       total,
                "total_pages": total_pages,
                "has_next":    page < total_pages,
                "has_prev":    page > 1,
            },
            "filters_applied": {
                k: v for k, v in {
                    "status":   status_f,
                    "currency": currency_f,
                    "method":   method_f,
                }.items() if v
            },
        },
    )


@v2_bp.route("/payments", methods=["POST"])
@active_version_headers("v2")
def create_payment():
    """
    [V2]  Create a payment.

    Request headers
    ---------------
    Idempotency-Key  (optional)  —  A unique string (8–128 chars).
        If you send the same key twice, the original response is
        returned without creating a duplicate record.

    Request body (v2)
    -----------------
    {
      "amount":         <integer>  — smallest currency unit (required)
      "currency":       <string>   — ISO 4217 code (required)
      "payment_method": <string>   — card|bank_transfer|e_wallet|qr_code
      "description":    <string>   — optional
      "metadata":       <object>   — optional key-value store
    }

    Breaking changes from v1
    ------------------------
    • amount  must be integer  (was float)
    • currency  is required    (was implicit VND)
    ---
    tags:
      - Payments (v2 — current)
    parameters:
      - name: Idempotency-Key
        in: header
        schema:
          type: string
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [amount, currency]
            properties:
              amount:
                type: integer
                example: 15000050
              currency:
                type: string
                example: VND
              payment_method:
                type: string
                example: card
              description:
                type: string
              metadata:
                type: object
    responses:
      201:
        description: Payment created
      200:
        description: Idempotent replay — payment already existed
      422:
        description: Validation error
      409:
        description: Idempotency key collision
    """
    body = request.get_json(silent=True) or {}

    # ── Idempotency check ─────────────────────────────────────────────
    ik = request.headers.get("Idempotency-Key")
    if ik:
        ik_errors = validate_idempotency_key(ik)
        if ik_errors:
            return err("INVALID_IDEMPOTENCY_KEY",
                       "Idempotency-Key header is invalid.",
                       details=ik_errors, http_status=400)

        if ik in idempotency_store:
            existing = payments_db.get(idempotency_store[ik])
            if existing:
                # Return original response — no side-effects
                from flask import make_response, jsonify
                resp = make_response(
                    jsonify({
                        "status": "success",
                        "timestamp": now_iso(),
                        "request_id": request.headers.get("X-Request-ID", "n/a"),
                        "data": _serialise(existing),
                        "idempotent_replay": True,
                    }), 200
                )
                resp.headers["X-Idempotent-Replayed"] = "true"
                resp.headers["X-API-Version"]         = "v2"
                return resp

    # ── Validation ────────────────────────────────────────────────────
    method_val = body.get("payment_method")
    field_errs = collect_errors({
        "amount":         (body.get("amount"),   validate_amount_cents),
        "currency":       (body.get("currency"), validate_currency),
        "payment_method": (method_val,           validate_payment_method,
                           False),   # optional
    })
    if field_errs:
        return validation_error(field_errs)

    # ── Create record ─────────────────────────────────────────────────
    pid = new_id("pay_")
    record = {
        "id":               pid,
        "amount_cents":     body["amount"],
        "currency":         body["currency"].upper(),
        "description":      body.get("description", ""),
        "payment_method":   body.get("payment_method", "card"),
        "status":           "pending",
        "idempotency_key":  ik,
        "metadata":         body.get("metadata") or {},
        "created_at":       now_iso(),
        "updated_at":       now_iso(),
    }
    payments_db[pid] = record
    if ik:
        idempotency_store[ik] = pid

    append_audit("create", "payment", pid, metadata={"version": "v2"})
    return created(_serialise(record))


@v2_bp.route("/payments/<payment_id>", methods=["GET"])
@active_version_headers("v2")
def get_payment(payment_id: str):
    """
    [V2]  Retrieve a single payment by ID.
    ---
    tags:
      - Payments (v2 — current)
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


@v2_bp.route("/payments/<payment_id>", methods=["PATCH"])
@active_version_headers("v2")
def update_payment(payment_id: str):
    """
    [V2]  Update payment status or metadata.

    Status transitions (state machine)
    -----------------------------------
    pending    → processing | cancelled
    processing → completed  | failed
    failed     → pending    (retry)
    completed  → (terminal)
    cancelled  → (terminal)

    Body fields
    -----------
    status    string  — new target status
    metadata  object  — merged into existing metadata
    ---
    tags:
      - Payments (v2 — current)
    parameters:
      - name: payment_id
        in: path
        required: true
        schema:
          type: string
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              status:
                type: string
              metadata:
                type: object
    responses:
      200:
        description: Updated payment
      404:
        description: Not found
      409:
        description: Invalid status transition
    """
    p = payments_db.get(payment_id)
    if not p:
        return not_found("Payment", payment_id)

    body = request.get_json(silent=True) or {}

    # ── Status transition ─────────────────────────────────────────────
    if "status" in body:
        new_status  = body["status"]
        cur_status  = p["status"]
        allowed     = PAYMENT_STATUS_MACHINE.get(cur_status, [])
        if new_status not in allowed:
            return conflict(
                f"Cannot transition from '{cur_status}' to '{new_status}'.",
                details={
                    "current_status":     cur_status,
                    "requested_status":   new_status,
                    "allowed_transitions": allowed,
                    "state_machine": PAYMENT_STATUS_MACHINE,
                },
            )
        p["status"] = new_status
        append_audit("status_change", "payment", payment_id,
                     metadata={"from": cur_status, "to": new_status,
                               "version": "v2"})

    # ── Metadata merge ────────────────────────────────────────────────
    if "metadata" in body and isinstance(body["metadata"], dict):
        p["metadata"] = {**p.get("metadata", {}), **body["metadata"]}

    p["updated_at"] = now_iso()
    return ok(_serialise(p))


@v2_bp.route("/payments/<payment_id>/refund", methods=["POST"])
@active_version_headers("v2")
def refund_payment(payment_id: str):
    """
    [V2]  Initiate a refund for a completed payment.

    Body
    ----
    amount   integer  — partial refund in smallest unit; omit for full refund
    reason   string   — refund reason (optional)
    ---
    tags:
      - Payments (v2 — current)
    parameters:
      - name: payment_id
        in: path
        required: true
        schema:
          type: string
    responses:
      201:
        description: Refund payment record created
      400:
        description: Payment not eligible for refund
      404:
        description: Not found
    """
    p = payments_db.get(payment_id)
    if not p:
        return not_found("Payment", payment_id)

    if p["status"] != "completed":
        return err("NOT_REFUNDABLE",
                   f"Only completed payments can be refunded. "
                   f"Current status: '{p['status']}'.",
                   http_status=400)

    body           = request.get_json(silent=True) or {}
    refund_amount  = body.get("amount", p["amount_cents"])

    if refund_amount > p["amount_cents"]:
        return err("REFUND_EXCEEDS_ORIGINAL",
                   "Refund amount exceeds the original payment amount.",
                   details={"original_cents": p["amount_cents"],
                            "requested_cents": refund_amount},
                   http_status=400)

    rid = new_id("ref_")
    refund = {
        "id":               rid,
        "amount_cents":     refund_amount,
        "currency":         p["currency"],
        "description":      f"Refund for {payment_id}",
        "payment_method":   p.get("payment_method", "card"),
        "status":           "completed",
        "idempotency_key":  None,
        "metadata":         {
            "original_payment_id": payment_id,
            "reason": body.get("reason", ""),
            "type": "refund",
        },
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    payments_db[rid] = refund
    append_audit("refund", "payment", payment_id,
                 metadata={"refund_id": rid, "amount_cents": refund_amount})

    return created({
        "refund":           _serialise(refund),
        "original_payment": _serialise(p),
    })


@v2_bp.route("/payments/summary", methods=["GET"])
@active_version_headers("v2")
def payment_summary():
    """
    [V2]  Aggregated summary of all payments (new in v2).
    ---
    tags:
      - Payments (v2 — current)
    responses:
      200:
        description: Summary statistics
    """
    from collections import defaultdict

    by_status   = defaultdict(int)
    by_currency = defaultdict(int)
    by_method   = defaultdict(int)
    total_cents = 0

    for p in payments_db.values():
        by_status[p["status"]]                 += 1
        by_currency[p["currency"]]             += p["amount_cents"]
        by_method[p.get("payment_method", "?")] += 1
        total_cents += p["amount_cents"]

    return ok({
        "total_payments":  len(payments_db),
        "by_status":       dict(by_status),
        "by_method":       dict(by_method),
        "volume_by_currency": {
            c: {"total_cents": t, "formatted": _fmt_money(t, c)}
            for c, t in by_currency.items()
        },
    })