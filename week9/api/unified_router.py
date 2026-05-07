"""
api/unified_router.py
---------------------
Strategy 2  (Header versioning)  and  Strategy 3  (Query-param versioning)
are handled here through a single set of URL endpoints that carry NO version
in the path:

    /api/payments                       (no version in URL)

The correct handler is selected by resolve_version() which inspects:

    Accept-Version: v2          ← Strategy 2: HTTP request header
    X-API-Version: v2           ← Strategy 2: alternative header name
    ?version=2                  ← Strategy 3: query parameter
    ?api_version=v2             ← Strategy 3: alternative param name

Priority when both signals are present:  Header > Query param > Default(v2)

This module deliberately imports and re-uses the v1 and v2 business logic
so there is no code duplication.
"""

from flask import Blueprint, request

from api.v1.payments import (
    create_payment as v1_create,
    get_payment    as v1_get,
    list_payments  as v1_list,
)
from api.v2.payments import (
    create_payment  as v2_create,
    get_payment     as v2_get,
    list_payments   as v2_list,
    payment_summary as v2_summary,
    update_payment  as v2_update,
)
from utils import responses as R
from utils.versioning import VERSION_REGISTRY, LATEST_VERSION, resolve_version

unified_bp = Blueprint("unified", __name__, url_prefix="/api")


# ── Version negotiation helper ────────────────────────────────────────────

def _negotiate():
    """
    Returns (version_label, error_response_or_None).
    We call resolve_version with url_version=None so it only looks at
    headers and query params.
    """
    try:
        info = resolve_version(url_version=None)
        return info["label"], info["_resolved_via"], None
    except ValueError as exc:
        return None, None, R.err("UNSUPPORTED_VERSION", str(exc),
                                 http_status=400)


def _stamp_version_headers(response, label: str, source: str):
    """Add version negotiation metadata to any response."""
    from flask import make_response
    if isinstance(response, tuple):
        resp = make_response(response[0], response[1])
    else:
        resp = make_response(response)

    resp.headers["X-API-Version"]              = label
    resp.headers["X-API-Latest-Version"]       = LATEST_VERSION
    resp.headers["X-API-Version-Source"]       = source  # header|query_param|default
    resp.headers["Vary"]                       = "Accept-Version, X-API-Version"

    vinfo = VERSION_REGISTRY.get(label, {})
    if vinfo.get("status") == "deprecated":
        resp.headers["Deprecation"]    = f'date="{vinfo.get("deprecated_on","")}"'
        resp.headers["Sunset"]         = vinfo.get("sunset_date", "")
        resp.headers["Warning"]        = (
            f'299 - "API {label} is deprecated. Migrate to {LATEST_VERSION}."'
        )
        if vinfo.get("migration_guide"):
            resp.headers["Link"] = (
                f'<{vinfo["migration_guide"]}>; rel="deprecation"'
            )
    return resp


# ── Unified endpoints ─────────────────────────────────────────────────────

@unified_bp.route("/payments", methods=["GET"])
def unified_list_payments():
    """
    Versionless  GET /api/payments
    Version resolved via header (Strategy 2) or query param (Strategy 3).

    Strategy 2 — Header:
        curl /api/payments -H "Accept-Version: v1"
        curl /api/payments -H "X-API-Version: v2"

    Strategy 3 — Query param:
        curl /api/payments?version=1
        curl /api/payments?api_version=v2

    If no version signal found → defaults to latest (v2).
    ---
    tags:
      - Payments (unified — strategy 2 & 3)
    parameters:
      - name: Accept-Version
        in: header
        schema: {type: string}
        description: "Strategy 2: version via header"
      - name: X-API-Version
        in: header
        schema: {type: string}
        description: "Strategy 2: alternative header"
      - name: version
        in: query
        schema: {type: string}
        description: "Strategy 3: version via query param"
      - name: api_version
        in: query
        schema: {type: string}
        description: "Strategy 3: alternative query param"
    responses:
      200:
        description: List of payments (format depends on resolved version)
    """
    label, source, error = _negotiate()
    if error:
        return error

    raw = v1_list() if label == "v1" else v2_list()
    return _stamp_version_headers(raw, label, source)


@unified_bp.route("/payments", methods=["POST"])
def unified_create_payment():
    """
    Versionless  POST /api/payments
    Version resolved via header (Strategy 2) or query param (Strategy 3).

    Strategy 2 example:
        curl -X POST /api/payments \\
             -H "Accept-Version: v2" \\
             -d '{"amount":15000050,"currency":"VND"}'

    Strategy 3 example:
        curl -X POST "/api/payments?version=2" \\
             -d '{"amount":15000050,"currency":"VND"}'
    ---
    tags:
      - Payments (unified — strategy 2 & 3)
    responses:
      201:
        description: Payment created
    """
    label, source, error = _negotiate()
    if error:
        return error

    raw = v1_create() if label == "v1" else v2_create()
    return _stamp_version_headers(raw, label, source)


@unified_bp.route("/payments/<payment_id>", methods=["GET"])
def unified_get_payment(payment_id: str):
    """
    Versionless  GET /api/payments/<id>
    ---
    tags:
      - Payments (unified — strategy 2 & 3)
    parameters:
      - name: payment_id
        in: path
        required: true
        schema: {type: string}
    responses:
      200:
        description: Payment detail
      404:
        description: Not found
    """
    label, source, error = _negotiate()
    if error:
        return error

    raw = v1_get(payment_id) if label == "v1" else v2_get(payment_id)
    return _stamp_version_headers(raw, label, source)


@unified_bp.route("/payments/<payment_id>", methods=["PATCH"])
def unified_update_payment(payment_id: str):
    """
    Versionless  PATCH /api/payments/<id>
    Only available in v2; v1 clients receive a 400 with upgrade notice.
    ---
    tags:
      - Payments (unified — strategy 2 & 3)
    parameters:
      - name: payment_id
        in: path
        required: true
        schema: {type: string}
    responses:
      200:
        description: Updated
      400:
        description: Not available in v1
    """
    label, source, error = _negotiate()
    if error:
        return error

    if label == "v1":
        return R.err(
            "NOT_IN_V1",
            "PATCH /api/payments/<id> is not available in v1. "
            "Upgrade to v2 (send Accept-Version: v2) to use status updates.",
            details={"migration_guide":
                     VERSION_REGISTRY["v1"]["migration_guide"]},
            http_status=400,
        )

    raw = v2_update(payment_id)
    return _stamp_version_headers(raw, label, source)


@unified_bp.route("/payments/summary", methods=["GET"])
def unified_summary():
    """
    Versionless  GET /api/payments/summary  (v2 only)
    ---
    tags:
      - Payments (unified — strategy 2 & 3)
    responses:
      200:
        description: Summary statistics
    """
    label, source, error = _negotiate()
    if error:
        return error

    if label == "v1":
        return R.err(
            "NOT_IN_V1",
            "Payment summary is a v2 feature. "
            "Add header 'Accept-Version: v2' or '?version=2' query param.",
            http_status=400,
        )

    raw = v2_summary()
    return _stamp_version_headers(raw, label, source)