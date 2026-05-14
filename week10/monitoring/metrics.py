import time
import logging
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from prometheus_flask_exporter import PrometheusMetrics

logger = logging.getLogger(__name__)

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

rate_limit_hits_total = Counter(
    "rate_limit_hits_total",
    "Total rate limit violations",
    ["endpoint", "ip"],
)

active_requests = Gauge(
    "active_requests",
    "Number of requests currently being processed",
)

auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["status"],  # success | failure
)

circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state: 0=closed, 1=open, 2=half-open",
    ["service"],
)

app_info = Info("app", "Application metadata")


def init_metrics(app):
    metrics = PrometheusMetrics(app, export_defaults=True)

    app_info.info(
        {
            "version": "1.0.0",
            "environment": app.config.get("FLASK_ENV", "production"),
            "service": "flask-production-api",
        }
    )

    circuit_breaker_state.labels(service="external_api").set(0)

    logger.info("Prometheus metrics initialised — scrape at /metrics")
    return metrics


def track_request(method: str, endpoint: str, status: int, duration: float):
    http_requests_total.labels(method=method, endpoint=endpoint, status=str(status)).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def record_rate_limit(endpoint: str, ip: str):
    rate_limit_hits_total.labels(endpoint=endpoint, ip=ip).inc()


def record_auth(success: bool):
    auth_attempts_total.labels(status="success" if success else "failure").inc()
