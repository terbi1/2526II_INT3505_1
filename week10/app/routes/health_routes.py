"""
app/routes/health_routes.py - Health checks and observability endpoints
"""
import os
import time
import logging
from flask import Blueprint, jsonify
from monitoring.circuit_breaker import all_statuses

logger = logging.getLogger(__name__)
health_bp = Blueprint("health", __name__)

START_TIME = time.time()


@health_bp.route("/health", methods=["GET"])
def health():
    """
    GET /health
    Liveness probe — used by load balancers, Kubernetes, Docker healthcheck.
    Always returns 200 if the process is alive.
    """
    return jsonify({"status": "healthy", "timestamp": time.time()}), 200


@health_bp.route("/ready", methods=["GET"])
def ready():
    """
    GET /ready
    Readiness probe — returns 200 only when the app is fully ready to serve.
    Extend this to check DB connections, caches, etc.
    """
    checks = {
        "api": True,
        # "database": check_db(),  ← add real checks here
    }
    all_ok = all(checks.values())
    status_code = 200 if all_ok else 503
    return jsonify({"ready": all_ok, "checks": checks}), status_code


@health_bp.route("/status", methods=["GET"])
def status():
    """
    GET /status
    Detailed operational dashboard: uptime, circuit breakers, environment.
    """
    uptime_seconds = time.time() - START_TIME
    return jsonify({
        "status": "operational",
        "uptime_seconds": round(uptime_seconds, 2),
        "uptime_human": _format_uptime(uptime_seconds),
        "environment": os.getenv("FLASK_ENV", "production"),
        "version": "1.0.0",
        "circuit_breakers": all_statuses(),
    }), 200


def _format_uptime(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {secs}s"
