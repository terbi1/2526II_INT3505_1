import logging
from flask import request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)


def _get_key():
    user = getattr(g, "current_user", None)
    return user if user else get_remote_address()


limiter = Limiter(
    key_func=_get_key,
    default_limits=["200 per day", "50 per hour"],
    headers_enabled=True,          
    storage_uri="memory://",    
)


def init_limiter(app):
    limiter.init_app(app)

    @app.errorhandler(429)
    def ratelimit_handler(e):
        from monitoring.logger import AuditLogger
        from monitoring.metrics import record_rate_limit

        audit = AuditLogger()
        ip = request.remote_addr
        endpoint = request.path
        user = getattr(g, "current_user", "anonymous")

        audit.rate_limit_exceeded(user=user, ip=ip, endpoint=endpoint)
        record_rate_limit(endpoint=endpoint, ip=ip)

        logger.warning(
            "Rate limit exceeded",
            extra={"ip": ip, "endpoint": endpoint, "user": user},
        )
        return (
            jsonify(
                {
                    "error": "Rate limit exceeded",
                    "message": str(e.description),
                    "retry_after": e.response.headers.get("Retry-After"),
                }
            ),
            429,
        )

    return limiter
