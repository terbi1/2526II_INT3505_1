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

    # ── Swagger / OpenAPI config ──────────────────────────────────────
    app.config["SWAGGER"] = {
        "title":   "Payment API — Versioning Demo",
        "version": "2.0",
        "uiversion": 3,
        "openapi": "3.0.3",
    }

    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route":    "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui":      True,
        "specs_route":     "/docs/",
    }

    swagger_template = {
        "info": {
            "title":       "Payment API — Versioning & Lifecycle Demo",
            "description": (
                "## API Versioning Strategies\n\n"
                "This API demonstrates **all three** versioning strategies:\n\n"
                "### Strategy 1 — URL Path  *(highest priority)*\n"
                "Embed the version directly in the URL path:\n"
                "```\n"
                "GET /api/v1/payments   # deprecated\n"
                "GET /api/v2/payments   # current\n"
                "```\n\n"
                "### Strategy 2 — Request Header\n"
                "Send `Accept-Version` or `X-API-Version` header:\n"
                "```\n"
                "GET /api/payments\n"
                "Accept-Version: v2\n"
                "```\n\n"
                "### Strategy 3 — Query Parameter\n"
                "Append `?version=` or `?api_version=` to the URL:\n"
                "```\n"
                "GET /api/payments?version=2\n"
                "GET /api/payments?api_version=v1\n"
                "```\n\n"
                "### Priority order when multiple signals present\n"
                "`URL path > Header > Query param > Default (v2)`\n\n"
                "---\n\n"
                "## Deprecation\n"
                "v1 is **deprecated** (sunset: 2025-12-31).  "
                "All v1 responses carry:\n"
                "- `Deprecation` header (RFC 8594)\n"
                "- `Sunset` header\n"
                "- `Warning` header (RFC 7234)\n"
                "- `Link` header pointing to migration guide\n"
            ),
            "version": "2.0.0",
            "contact": {"email": "platform@example.com"},
        },
        "tags": [
            {"name": "Payments (v1 — deprecated)",
             "description": "URL path versioning: /api/v1/payments"},
            {"name": "Payments (v2 — current)",
             "description": "URL path versioning: /api/v2/payments"},
            {"name": "Payments (unified — strategy 2 & 3)",
             "description": "Header / query-param versioning: /api/payments"},
            {"name": "Meta",
             "description": "Version manifest, health, audit"},
        ],
        "servers": [{"url": "http://localhost:5000"}],
    }

    Swagger(app, config=swagger_config, template=swagger_template)

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


# ── Banner ────────────────────────────────────────────────────────────────

# def _print_banner(app: Flask):
#     try:
#         from colorama import Fore, Style, init
#         init(autoreset=True)
#         G = Fore.GREEN; Y = Fore.YELLOW; C = Fore.CYAN
#         R_ = Fore.RED;  W = Fore.WHITE;  B = Style.BRIGHT
#         RS = Style.RESET_ALL
#     except ImportError:
#         G = Y = C = R_ = W = B = RS = ""

#     lines = [
#         "",
#         f"{B}{C}╔══════════════════════════════════════════════════════╗{RS}",
#         f"{B}{C}║        Payment API — Versioning & Lifecycle          ║{RS}",
#         f"{B}{C}╚══════════════════════════════════════════════════════╝{RS}",
#         "",
#         f"{B}{W}  Swagger UI:{RS}  {G}http://localhost:5000/docs/{RS}",
#         f"{B}{W}  Version manifest:{RS}  {G}http://localhost:5000/api/versions{RS}",
#         "",
#         f"{B}{Y}  ── Strategy 1: URL Path ─────────────────────────────{RS}",
#         f"{R_}  [DEPRECATED] GET/POST  /api/v1/payments{RS}",
#         f"{R_}  [DEPRECATED] GET       /api/v1/payments/<id>{RS}",
#         f"{G}  [CURRENT]    GET/POST  /api/v2/payments{RS}",
#         f"{G}  [CURRENT]    GET/PATCH /api/v2/payments/<id>{RS}",
#         f"{G}  [CURRENT]    POST      /api/v2/payments/<id>/refund{RS}",
#         f"{G}  [CURRENT]    GET       /api/v2/payments/summary{RS}",
#         "",
#         f"{B}{Y}  ── Strategy 2: Header ───────────────────────────────{RS}",
#         f"{C}  GET /api/payments          + header 'Accept-Version: v2'{RS}",
#         f"{C}  GET /api/payments          + header 'X-API-Version: v1'{RS}",
#         "",
#         f"{B}{Y}  ── Strategy 3: Query Param ──────────────────────────{RS}",
#         f"{C}  GET /api/payments?version=2{RS}",
#         f"{C}  GET /api/payments?api_version=v1{RS}",
#         "",
#         f"{B}{W}  Priority: URL path > Header > Query param > Default(v2){RS}",
#         "",
#     ]
#     print("\n".join(lines))


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    application = create_app()
    # _print_banner(application)
    application.run(debug=True, port=5000, use_reloader=False)