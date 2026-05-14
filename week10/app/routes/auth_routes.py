"""
app/routes/auth_routes.py - Authentication endpoints
"""
import logging
from flask import Blueprint, request, jsonify, current_app
from app.auth import generate_token
from app.rate_limiter import limiter
from monitoring.logger import AuditLogger
from monitoring.metrics import record_auth

logger = logging.getLogger(__name__)
audit = AuditLogger()

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# In production, use a real database. This is a demo store.
DEMO_USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "alice": {"password": "alice123", "role": "user"},
    "bob": {"password": "bob123", "role": "user"},
}


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")        # Strict: protect against brute force
def login():
    """
    POST /api/auth/login
    Body: { "username": "alice", "password": "alice123" }
    Returns: { "token": "<jwt>", "role": "user" }
    """
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    ip = request.remote_addr

    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    user = DEMO_USERS.get(username)
    if not user or user["password"] != password:
        audit.login_failure(user=username, ip=ip)
        record_auth(success=False)
        logger.warning(f"Failed login attempt for user '{username}' from {ip}")
        return jsonify({"error": "Invalid credentials"}), 401

    token = generate_token(user_id=username, role=user["role"])
    audit.login_success(user=username, ip=ip)
    record_auth(success=True)

    logger.info(f"User '{username}' authenticated from {ip}")
    return jsonify({"token": token, "role": user["role"], "user": username}), 200


@auth_bp.route("/verify", methods=["GET"])
@limiter.limit("30 per minute")
def verify():
    """Quick token health check — returns the decoded claims."""
    from app.auth import decode_token
    import jwt

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "No token provided"}), 400

    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        return jsonify({"valid": True, "user": payload["sub"], "role": payload.get("role")}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"valid": False, "error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"valid": False, "error": "Invalid token"}), 401
