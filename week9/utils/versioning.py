
import datetime
import logging
from functools import wraps

from flask import Blueprint, jsonify, make_response, request

logger = logging.getLogger(__name__)

# ── Version registry ──────────────────────────────────────────────────────
#
# Each entry describes one published version.
# Add a new dict here whenever you ship a new version.
#
VERSION_REGISTRY: dict[str, dict] = {
    "v1": {
        "label":          "v1",
        "numeric":        1,
        "status":         "deprecated",          
        "released":       "2023-01-01",
        "deprecated_on":  "2024-06-01",
        "sunset_date":    "2025-12-31",
        "migration_guide":"https://docs.example.com/api/migrate/v1-to-v2",
        "changelog":      "https://docs.example.com/changelog#v1",
    },
    "v2": {
        "label":          "v2",
        "numeric":        2,
        "status":         "active",
        "released":       "2024-01-01",
        "deprecated_on":  None,
        "sunset_date":    None,
        "migration_guide": None,
        "changelog":      "https://docs.example.com/changelog#v2",
    },
}

LATEST_VERSION  = "v2"
MINIMUM_VERSION = "v1"      # oldest still served (sunset ones return 410)
SUPPORTED       = {"v1", "v2"}


# ── Strategy negotiation ───────────────────────────────────────────────────

def resolve_version(url_version: str | None = None) -> dict:
    """
    Negotiate an API version from the three strategies.

    Priority (highest → lowest):
        1. URL path segment  (e.g. /api/v1/...)
        2. Request header    (Accept-Version: v2  OR  X-API-Version: v2)
        3. Query parameter   (?version=2  OR  ?api_version=v2)
        4. Default → LATEST_VERSION

    Returns the version-registry dict for the resolved version.
    Raises ValueError when the client explicitly asks for an unknown version.
    """

    def _normalise(raw: str | None) -> str | None:
        """Accept '1', '2', 'v1', 'v2', 'V2' → 'v1' / 'v2'."""
        if not raw:
            return None
        raw = raw.strip().lower()
        if raw.startswith("v"):
            return raw          # already 'v1'
        if raw.isdigit():
            return f"v{raw}"    # '2' → 'v2'
        return None

    # 1. URL path
    chosen = _normalise(url_version)
    source  = "url_path"

    # 2. Header  (only if URL didn't already tell us)
    if not chosen:
        header_val = (request.headers.get("Accept-Version") or
                      request.headers.get("X-API-Version"))
        chosen = _normalise(header_val)
        source  = "header"

    # 3. Query param
    if not chosen:
        qp = (request.args.get("version") or
              request.args.get("api_version"))
        chosen = _normalise(qp)
        source  = "query_param"

    # 4. Default
    if not chosen:
        chosen = LATEST_VERSION
        source  = "default"

    # Validate
    if chosen not in VERSION_REGISTRY:
        raise ValueError(
            f"Unknown API version '{chosen}'. "
            f"Supported versions: {sorted(SUPPORTED)}"
        )

    info = VERSION_REGISTRY[chosen].copy()
    info["_resolved_via"] = source
    return info


# ── Deprecation decorator ─────────────────────────────────────────────────

def deprecated(version_label: str):
    """
    Class/function decorator that injects RFC 8594 deprecation headers
    into every response produced by the wrapped view.

    Usage:
        @bp.route("/payments")
        @deprecated("v1")
        def list_payments_v1():
            ...
    """
    version = VERSION_REGISTRY.get(version_label, {})
    sunset_str   = version.get("sunset_date")
    guide_url    = version.get("migration_guide", "")
    deprecated_on = version.get("deprecated_on", "")

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # ── Run the original view ──────────────────────────────────
            result = f(*args, **kwargs)

            # Normalise to (response_obj, status_code)
            if isinstance(result, tuple):
                body, status = result[0], result[1]
            else:
                body, status = result, 200

            resp = make_response(body, status)

            # ── RFC 8594 headers ───────────────────────────────────────
            if deprecated_on:
                resp.headers["Deprecation"] = f'date="{deprecated_on}"'
            if sunset_str:
                resp.headers["Sunset"] = sunset_str
                sunset  = datetime.date.fromisoformat(sunset_str)
                today   = datetime.date.today()
                days    = (sunset - today).days
                resp.headers["X-Days-Until-Sunset"] = str(max(0, days))
            if guide_url:
                resp.headers["Link"] = (
                    f'<{guide_url}>; rel="deprecation"; type="text/html"'
                )

            # ── Human-readable warning (RFC 7234 §5.5) ────────────────
            resp.headers["Warning"] = (
                f'299 api.example.com "API {version_label} is deprecated'
                + (f' and will be removed on {sunset_str}' if sunset_str else '')
                + f'. Migrate to {LATEST_VERSION}."'
            )

            # ── Convenience headers ────────────────────────────────────
            resp.headers["X-API-Version"]          = version_label
            resp.headers["X-API-Latest-Version"]   = LATEST_VERSION
            resp.headers["X-Migration-Guide"]      = guide_url or ""

            logger.warning(
                "DEPRECATED %s %s  version=%s  client=%s  "
                "days_until_sunset=%s",
                request.method, request.path,
                version_label, request.remote_addr,
                resp.headers.get("X-Days-Until-Sunset", "n/a"),
            )
            return resp
        return wrapper
    return decorator


def active_version_headers(version_label: str):
    """
    Decorator that stamps every active-version response with
    informational headers (no deprecation warnings).
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            if isinstance(result, tuple):
                body, status = result[0], result[1]
            else:
                body, status = result, 200
            resp = make_response(body, status)
            resp.headers["X-API-Version"]        = version_label
            resp.headers["X-API-Latest-Version"] = LATEST_VERSION
            return resp
        return wrapper
    return decorator


# ── Strategy-2 & 3 router blueprint ───────────────────────────────────────
#
# Mounts at /api/payments (no version in URL).
# Dispatches to the correct handler based on header / query-param.
#
from utils import responses as R          # noqa: E402  (avoid circular at top)

strategy_bp = Blueprint("strategy_versioning", __name__)


def _dispatch(v1_fn, v2_fn):
    """
    Resolve version from header / query-param and call the right handler.
    Used by the strategy-2/3 unified endpoints below.
    """
    try:
        vinfo = resolve_version(url_version=None)   # skip URL strategy here
    except ValueError as exc:
        return R.err("UNSUPPORTED_VERSION", str(exc), http_status=400)

    label = vinfo["label"]

    if label == "v1":
        resp_data = v1_fn()
        # If it's already a Flask response tuple, unwrap to add headers
        if isinstance(resp_data, tuple):
            body_resp, status = resp_data
        else:
            body_resp, status = resp_data, 200

        resp = make_response(body_resp, status)
        # Stamp deprecation headers
        _stamp_deprecation(resp, "v1")
        return resp

    elif label == "v2":
        resp_data = v2_fn()
        if isinstance(resp_data, tuple):
            body_resp, status = resp_data
        else:
            body_resp, status = resp_data, 200
        resp = make_response(body_resp, status)
        resp.headers["X-API-Version"]        = "v2"
        resp.headers["X-API-Latest-Version"] = LATEST_VERSION
        return resp

    return R.err("UNSUPPORTED_VERSION",
                 f"Version '{label}' is not handled by this router.",
                 http_status=400)


def _stamp_deprecation(resp, version_label: str):
    version = VERSION_REGISTRY.get(version_label, {})
    sunset_str    = version.get("sunset_date")
    guide_url     = version.get("migration_guide", "")
    deprecated_on = version.get("deprecated_on", "")
    if deprecated_on:
        resp.headers["Deprecation"] = f'date="{deprecated_on}"'
    if sunset_str:
        resp.headers["Sunset"] = sunset_str
        days = (datetime.date.fromisoformat(sunset_str) -
                datetime.date.today()).days
        resp.headers["X-Days-Until-Sunset"] = str(max(0, days))
    if guide_url:
        resp.headers["Link"] = (
            f'<{guide_url}>; rel="deprecation"; type="text/html"'
        )
    resp.headers["Warning"] = (
        f'299 api.example.com "API {version_label} is deprecated. '
        f'Migrate to {LATEST_VERSION}."'
    )
    resp.headers["X-API-Version"]        = version_label
    resp.headers["X-API-Latest-Version"] = LATEST_VERSION
    resp.headers["X-Migration-Guide"]    = guide_url


# ── Version info endpoint ─────────────────────────────────────────────────

def build_version_manifest() -> dict:
    versions = []
    for label, info in VERSION_REGISTRY.items():
        entry = {k: v for k, v in info.items() if not k.startswith("_")}
        if info["status"] == "deprecated" and info["sunset_date"]:
            sunset = datetime.date.fromisoformat(info["sunset_date"])
            entry["days_until_sunset"] = max(0, (sunset - datetime.date.today()).days)
        versions.append(entry)
    return {
        "versions":         versions,
        "latest":           LATEST_VERSION,
        "minimum":          MINIMUM_VERSION,
        "versioning_strategies": {
            "url_path": {
                "description": "Embed version in URL path segment",
                "example":     "/api/v2/payments",
                "priority":    1,
            },
            "header": {
                "description": "Send Accept-Version or X-API-Version header",
                "example":     "Accept-Version: v2",
                "priority":    2,
            },
            "query_param": {
                "description": "Append ?version= or ?api_version= query parameter",
                "example":     "/api/payments?version=2",
                "priority":    3,
            },
        },
    }