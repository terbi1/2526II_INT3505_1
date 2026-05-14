"""
app.py
------
Main Flask application entry-point.

Blueprints registered
---------------------
  /api/v1/...         Strategy 1 — URL path versioning (v1, deprecated)
  /api/v2/...         Strategy 1 — URL path versioning (v2, current)
  /api/...            Strategy 2 & 3 — header / query-param versioning
  /docs               Swagger UI
  /api/versions       Version manifest
  /api/audit          Audit log (read-only)
  /health             Health check
"""

import logging
import sys

from flask import Flask, jsonify, request

from flasgger import Swagger

from api.v1.payments   import v1_bp
from api.v2.payments   import v2_bp
from api.unified_router import unified_bp
from utils.database     import seed
from utils.versioning   import build_version_manifest, VERSION_REGISTRY
from utils              import responses as R

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


# ── App factory ───────────────────────────────────────────────────────────

def create_app() -> Flask:
    app = Flask(__name__)

    # ── Register blueprints ───────────────────────────────────────────
    app.register_blueprint(v1_bp)
    app.register_blueprint(v2_bp)
    app.register_blueprint(unified_bp)

    # ── Meta endpoints ────────────────────────────────────────────────

    @app.route("/health")
    def health():
        """
        Health check.
        ---
        tags: [Meta]
        responses:
          200:
            description: Server is up
        """
        return jsonify({"status": "ok", "service": "payment-api"})

    @app.route("/api/versions")
    def version_manifest():
        """
        Full version manifest — lists all versions, their status,
        sunset dates, and which versioning strategies are available.
        ---
        tags: [Meta]
        responses:
          200:
            description: Version manifest
        """
        return jsonify(build_version_manifest())

    @app.route("/api/audit")
    def audit():
        """
        Read-only audit log.
        ---
        tags: [Meta]
        responses:
          200:
            description: Audit entries (newest first)
        """
        from utils.database import audit_log
        return jsonify({
            "total":   len(audit_log),
            "entries": list(reversed(audit_log)),
        })

    # ── Global error handlers ─────────────────────────────────────────

    @app.errorhandler(404)
    def handle_404(e):
        return R.err(
            "ROUTE_NOT_FOUND",
            f"The route '{request.path}' does not exist.",
            details={
                "hint": "Check /api/versions for available endpoints.",
                "docs": "/docs/",
            },
            http_status=404,
        )

    @app.errorhandler(405)
    def handle_405(e):
        return R.err("METHOD_NOT_ALLOWED",
                     f"{request.method} is not allowed on {request.path}.",
                     http_status=405)

    @app.errorhandler(500)
    def handle_500(e):
        logger.exception("Unhandled exception")
        return R.err("INTERNAL_ERROR",
                     "An unexpected error occurred.",
                     http_status=500)

    # ── Seed demo data ────────────────────────────────────────────────
    seed()
    logger.info("Demo data seeded — %d payments in db", 5)

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True, port=5000, use_reloader=False)