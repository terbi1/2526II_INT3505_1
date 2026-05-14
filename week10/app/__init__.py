import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS

from config.settings import config
from monitoring.logger import setup_logging
from monitoring.metrics import init_metrics
from app.rate_limiter import init_limiter
from app.middleware import register_middleware

logger = logging.getLogger(__name__)


def create_app(env: str = None) -> Flask:
    env = env or os.getenv("FLASK_ENV", "production")
    cfg = config.get(env, config["default"])

    app = Flask(__name__)
    app.config.from_object(cfg)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    setup_logging(app)

    init_metrics(app)

    init_limiter(app)

    register_middleware(app)

    from app.routes.auth_routes import auth_bp
    from app.routes.product_routes import products_bp
    from app.routes.health_routes import health_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(health_bp)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        logger.exception("Unhandled server error")
        return jsonify({"error": "Internal server error"}), 500

    logger.info(f"Flask app created — environment: {env}")
    return app
