import logging
import os
import sys
from datetime import datetime, timezone
from pythonjsonlogger import jsonlogger


class AuditLogger:

    def __init__(self):
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        os.makedirs("logs", exist_ok=True)
        handler = logging.FileHandler("logs/audit.log")
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log(self, event: str, user: str = "anonymous", ip: str = None, **kwargs):
        self.logger.info(
            event,
            extra={
                "event_type": event,
                "user": user,
                "ip": ip,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **kwargs,
            },
        )

    def login_success(self, user: str, ip: str):
        self.log("AUTH_LOGIN_SUCCESS", user=user, ip=ip, severity="INFO")

    def login_failure(self, user: str, ip: str):
        self.log("AUTH_LOGIN_FAILURE", user=user, ip=ip, severity="WARNING")

    def rate_limit_exceeded(self, user: str, ip: str, endpoint: str):
        self.log(
            "RATE_LIMIT_EXCEEDED",
            user=user,
            ip=ip,
            endpoint=endpoint,
            severity="WARNING",
        )

    def unauthorized_access(self, ip: str, endpoint: str):
        self.log(
            "UNAUTHORIZED_ACCESS",
            ip=ip,
            endpoint=endpoint,
            severity="WARNING",
        )


def setup_logging(app):
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper())
    log_file = app.config.get("LOG_FILE", "logs/app.log")

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    json_formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(module)s %(funcName)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(json_formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if app.config.get("DEBUG"):
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
    else:
        console_handler.setFormatter(json_formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    app.logger.setLevel(log_level)

    app.logger.info(
        "Logging initialised",
        extra={"log_level": app.config.get("LOG_LEVEL"), "log_file": log_file},
    )

    return logging.getLogger(__name__)
