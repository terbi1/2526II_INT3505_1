"""
app/auth.py - JWT-based authentication helpers
"""
import logging
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, current_app, g

logger = logging.getLogger(__name__)


def generate_token(user_id: str, role: str = "user") -> str:
    """Create a signed JWT access token."""
    secret = current_app.config["JWT_SECRET_KEY"]
    expires = current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    payload = {
        "sub": user_id,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expires),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt exceptions on failure."""
    secret = current_app.config["JWT_SECRET_KEY"]
    return jwt.decode(token, secret, algorithms=["HS256"])


def jwt_required(f):
    """Decorator: require a valid Bearer JWT to access the endpoint."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from monitoring.metrics import record_auth
        from monitoring.logger import AuditLogger

        audit = AuditLogger()
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            audit.unauthorized_access(
                ip=request.remote_addr,
                endpoint=request.path,
            )
            record_auth(success=False)
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token)
            g.current_user = payload["sub"]
            g.current_role = payload.get("role", "user")
            record_auth(success=True)
        except jwt.ExpiredSignatureError:
            record_auth(success=False)
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            record_auth(success=False)
            logger.warning(f"Invalid token from {request.remote_addr}: {e}")
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated


def role_required(required_role: str):
    """Decorator: require a specific role (stacks on top of jwt_required)."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            role = getattr(g, "current_role", None)
            if role != required_role:
                return jsonify({"error": f"Role '{required_role}' required"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
