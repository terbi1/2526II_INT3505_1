"""
core/responses.py
-----------------
Standardised JSON response builders used by every version.
"""

import datetime
from flask import jsonify, request


def _envelope(status: str, data=None, meta: dict = None,
              error: dict = None) -> dict:
    body = {
        "status":    status,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "request_id": request.headers.get("X-Request-ID", "n/a"),
    }
    if data    is not None: body["data"]  = data
    if meta    is not None: body["meta"]  = meta
    if error   is not None: body["error"] = error
    return body


def ok(data, meta: dict = None, http_status: int = 200):
    return jsonify(_envelope("success", data=data, meta=meta)), http_status


def created(data, meta: dict = None):
    return ok(data, meta=meta, http_status=201)


def no_content():
    return "", 204


def err(code: str, message: str, details=None, http_status: int = 400):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return jsonify(_envelope("error", error=error)), http_status


# ── Common shortcuts ──────────────────────────────────────────────────────
def not_found(resource: str, resource_id: str):
    return err("NOT_FOUND",
               f"{resource} '{resource_id}' not found.",
               http_status=404)


def validation_error(fields: list):
    return err("VALIDATION_ERROR",
               "One or more fields failed validation.",
               details={"fields": fields},
               http_status=422)


def conflict(message: str, details=None):
    return err("CONFLICT", message, details=details, http_status=409)