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

def _negotiate():
    
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

@unified_bp.route("/payments", methods=["GET"])
def unified_list_payments():
    
    label, source, error = _negotiate()
    if error:
        return error

    raw = v1_list() if label == "v1" else v2_list()
    return _stamp_version_headers(raw, label, source)


@unified_bp.route("/payments", methods=["POST"])
def unified_create_payment():
    
    label, source, error = _negotiate()
    if error:
        return error

    raw = v1_create() if label == "v1" else v2_create()
    return _stamp_version_headers(raw, label, source)


@unified_bp.route("/payments/<payment_id>", methods=["GET"])
def unified_get_payment(payment_id: str):
    
    label, source, error = _negotiate()
    if error:
        return error

    raw = v1_get(payment_id) if label == "v1" else v2_get(payment_id)
    return _stamp_version_headers(raw, label, source)


@unified_bp.route("/payments/<payment_id>", methods=["PATCH"])
def unified_update_payment(payment_id: str):
    
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