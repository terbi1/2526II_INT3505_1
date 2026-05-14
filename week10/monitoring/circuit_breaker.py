import time
import logging
from enum import Enum
from functools import wraps
from threading import Lock

logger = logging.getLogger(__name__)


class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = State.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        self._lock = Lock()

    @property
    def state(self) -> State:
        with self._lock:
            if self._state == State.OPEN:
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    logger.warning(
                        f"[CircuitBreaker:{self.name}] Transitioning OPEN → HALF_OPEN"
                    )
                    self._state = State.HALF_OPEN
                    self._half_open_calls = 0
            return self._state

    @property
    def is_open(self) -> bool:
        return self.state == State.OPEN

    def _on_success(self):
        with self._lock:
            if self._state == State.HALF_OPEN:
                logger.info(
                    f"[CircuitBreaker:{self.name}] Recovery confirmed — HALF_OPEN → CLOSED"
                )
            self._state = State.CLOSED
            self._failure_count = 0
            self._last_failure_time = None

    def _on_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self.failure_threshold:
                if self._state != State.OPEN:
                    logger.error(
                        f"[CircuitBreaker:{self.name}] Threshold reached "
                        f"({self._failure_count}/{self.failure_threshold}) — OPEN"
                    )
                self._state = State.OPEN

    def call(self, func, *args, **kwargs):
        """Execute func through the circuit breaker."""
        current_state = self.state

        if current_state == State.OPEN:
            raise CircuitOpenError(
                f"Circuit '{self.name}' is OPEN — request blocked (fail fast)"
            )

        if current_state == State.HALF_OPEN:
            with self._lock:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitOpenError(
                        f"Circuit '{self.name}' is HALF_OPEN — probe limit reached"
                    )
                self._half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }


class CircuitOpenError(Exception):
    """Raised when a call is blocked by an open circuit breaker."""

def with_circuit_breaker(breaker: CircuitBreaker):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


_registry: dict[str, CircuitBreaker] = {}


def get_or_create(name: str, **kwargs) -> CircuitBreaker:
    if name not in _registry:
        _registry[name] = CircuitBreaker(name, **kwargs)
    return _registry[name]


def all_statuses() -> list[dict]:
    return [cb.status() for cb in _registry.values()]
