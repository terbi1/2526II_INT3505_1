import time
import uuid
import logging
import re
from flask import request, g, jsonify

logger = logging.getLogger(__name__)


WAF_PATTERNS = [
    re.compile(
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC)\b)",
        re.IGNORECASE,
    ),
    re.compile(r"<script[\s>]", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"\.\./"),
    re.compile(r"[;&|`$]"),
]

BLOCKED_IPS: set[str] = set() 


def check_waf(value: str) -> bool:
    for pattern in WAF_PATTERNS:
        if pattern.search(value):
            return True
    return False


def register_middleware(app):

    @app.before_request
    def assign_request_id():
        g.request_id = str(uuid.uuid4())
        g.start_time = time.time()

    @app.before_request
    def block_listed_ips():
        if request.remote_addr in BLOCKED_IPS:
            logger.warning(
                "Blocked IP attempted access",
                extra={"ip": request.remote_addr, "path": request.path},
            )
            return jsonify({"error": "Access denied"}), 403

    @app.before_request
    def waf_inspection():
        for key, value in request.args.items():
            if check_waf(value):
                logger.warning(
                    extra={
                        "ip": request.remote_addr,
                        "param": key,
                        "value": value[:80],
                    },
                )
                return jsonify({"error": "Request blocked by WAF"}), 400

        if request.is_json:
            body = request.get_json(silent=True) or {}
            for key, value in body.items():
                if isinstance(value, str) and check_waf(value):
                    logger.warning(
                        "WAF: suspicious JSON field",
                        extra={
                            "ip": request.remote_addr,
                            "field": key,
                            "value": value[:80],
                        },
                    )
                    return jsonify({"error": "Request blocked by WAF"}), 400

    @app.before_request
    def log_incoming_request():
        logger.info(
            "Incoming request",
            extra={
                "request_id": g.get("request_id"),
                "method": request.method,
                "path": request.path,
                "ip": request.remote_addr,
                "user_agent": request.headers.get("User-Agent", "")[:100],
            },
        )

    @app.after_request
    def add_security_headers(response):
        """OWASP-recommended security headers."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Request-ID"] = g.get("request_id", "")
        response.headers.pop("Server", None)  # Hide server info
        return response

    @app.after_request
    def log_response(response):
        duration = time.time() - g.get("start_time", time.time())

        from monitoring.metrics import track_request
        track_request(
            method=request.method,
            endpoint=request.path,
            status=response.status_code,
            duration=duration,
        )

        logger.info(
            "Request completed",
            extra={
                "request_id": g.get("request_id"),
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "ip": request.remote_addr,
            },
        )
        return response
