from flask import Flask, jsonify
from v1.payments import v1_bp
from v2.payments import v2_bp
import logging

# ---- Cấu hình logging ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = Flask(__name__)


# ---- Đăng ký Blueprints ----
app.register_blueprint(v1_bp)
app.register_blueprint(v2_bp)


# ---- Health check endpoint ----
@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "api_versions": {
            "v1": {
                "status": "deprecated",
                "sunset_date": "2025-12-31",
                "migration_guide": "https://docs.example.com/api/migration/v1-to-v2"
            },
            "v2": {
                "status": "active",
                "current": True
            }
        }
    })


# ---- API Version Discovery ----
@app.route("/api")
def api_root():
    """Endpoint liệt kê tất cả API versions."""
    return jsonify({
        "versions": [
            {
                "version": "v1",
                "status": "deprecated",
                "base_url": "/api/v1",
                "sunset_date": "2025-12-31",
                "docs": "/api/v1/docs"
            },
            {
                "version": "v2",
                "status": "current",
                "base_url": "/api/v2",
                "docs": "/api/v2/docs"
            }
        ],
        "recommended": "v2"
    })


# ---- Error handlers ----
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "status": "error",
        "error": {
            "code": "ENDPOINT_NOT_FOUND",
            "message": str(e),
            "hint": "Check /api for available versions"
        }
    }), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({
        "status": "error",
        "error": {
            "code": "METHOD_NOT_ALLOWED",
            "message": str(e)
        }
    }), 405


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Payment API Server")
    print("="*60)
    print("  Endpoints:")
    print("    Health:   GET  /health")
    print("    API Info: GET  /api")
    print()
    print("  V1 (DEPRECATED - Sunset: 2025-12-31):")
    print("    GET  /api/v1/payments")
    print("    POST /api/v1/payments")
    print("    GET  /api/v1/payments/<id>")
    print()
    print("  V2 (CURRENT):")
    print("    GET   /api/v2/payments")
    print("    POST  /api/v2/payments")
    print("    GET   /api/v2/payments/<id>")
    print("    PATCH /api/v2/payments/<id>")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)