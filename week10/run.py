import os
from app import create_app


def create_application():
    return create_app(os.getenv("FLASK_ENV", "development"))


if __name__ == "__main__":
    app = create_application()
    port = int(os.getenv("PORT", 5000))
    print(f"""
╔══════════════════════════════════════════════════════╗
║      Flask Production API — Session 10               ║
╠══════════════════════════════════════════════════════╣
║  API:      http://localhost:{port}                      ║
║  Health:   http://localhost:{port}/health               ║
║  Status:   http://localhost:{port}/status               ║
║  Metrics:  http://localhost:{port}/metrics  (Prometheus)║
╚══════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))
