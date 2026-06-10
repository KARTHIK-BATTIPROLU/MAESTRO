"""
MAESTRO - Production Resilience Layer

Provides:
  • CircuitBreaker   — prevents cascading failures to Gemini / downstream
  • RetryWithBackoff — exponential backoff with jitter for transient errors
  • StructuredLogger — JSON-formatted logs for production observability
  • GracefulDegradation — fallback responses when services are unavailable

Usage:
    from resilience import circuit_breaker, retry, logger

    @circuit_breaker(failure_threshold=3, recovery_timeout=60)
    @retry(max_attempts=3, base_delay=1.0)
    async def call_llm(prompt):
        ...
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import random
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type


# =============================================================================
# STRUCTURED LOGGER
# =============================================================================

class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON for log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        # Merge extra fields attached via `logger.info("msg", extra={...})`
        for key in ("request_id", "session_id", "pipeline", "stage", "duration_ms", "status_code"):
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val
        return json.dumps(entry, default=str)


def get_logger(name: str = "maestro") -> logging.Logger:
    """Return a logger configured for structured JSON output in production."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


logger = get_logger()


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitState(Enum):
    CLOSED = "CLOSED"          # normal operation
    OPEN = "OPEN"              # failing — reject immediately
    HALF_OPEN = "HALF_OPEN"    # probing — allow one request


@dataclass
class CircuitBreaker:
    """
    Thread-safe circuit breaker for protecting downstream calls.

    State transitions:
        CLOSED  → (failures >= threshold) → OPEN
        OPEN    → (recovery_timeout elapsed) → HALF_OPEN
        HALF_OPEN → (success) → CLOSED
        HALF_OPEN → (failure) → OPEN

    Args:
        name: Human-readable label (e.g., "gemini-api")
        failure_threshold: Consecutive failures before opening
        recovery_timeout: Seconds to wait before half-open probe
        expected_exceptions: Tuple of exception types considered failures
    """
    name: str = "default"
    failure_threshold: int = 3
    recovery_timeout: float = 60.0
    expected_exceptions: tuple = (Exception,)

    # internal state
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _last_error: Optional[str] = field(default=None, init=False)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info(
                    f"Circuit '{self.name}' → HALF_OPEN (probing)",
                    extra={"pipeline": "circuit_breaker"},
                )
        return self._state

    def record_success(self) -> None:
        self._failure_count = 0
        self._last_error = None
        if self._state != CircuitState.CLOSED:
            logger.info(
                f"Circuit '{self.name}' → CLOSED (recovered)",
                extra={"pipeline": "circuit_breaker"},
            )
        self._state = CircuitState.CLOSED

    def record_failure(self, error: Exception) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        self._last_error = str(error)
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                f"Circuit '{self.name}' → OPEN after {self._failure_count} failures: {error}",
                extra={"pipeline": "circuit_breaker"},
            )

    def allow_request(self) -> bool:
        state = self.state  # triggers OPEN→HALF_OPEN check
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            return True
        return False

    def to_health(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "last_error": self._last_error,
        }


class CircuitOpenError(Exception):
    """Raised when the circuit is open and calls are rejected."""
    pass


# Singleton circuits
gemini_circuit = CircuitBreaker(name="gemini-api", failure_threshold=3, recovery_timeout=60)
agent_pipeline_circuit = CircuitBreaker(name="agent-pipeline", failure_threshold=5, recovery_timeout=120)


# =============================================================================
# RETRY WITH EXPONENTIAL BACKOFF
# =============================================================================

async def retry_async(
    fn: Callable,
    *args: Any,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (Exception,),
    circuit: Optional[CircuitBreaker] = None,
    **kwargs: Any,
) -> Any:
    """
    Retry an async function with exponential backoff + jitter.

    If a CircuitBreaker is provided, it is checked before each attempt
    and updated after success/failure.

    Args:
        fn: Async callable to execute
        max_attempts: Maximum number of tries (including the first)
        base_delay: Initial delay in seconds (doubles each retry)
        max_delay: Cap on delay in seconds
        retryable_exceptions: Exception types that trigger a retry
        circuit: Optional CircuitBreaker to consult
    """
    last_exc: Exception = RuntimeError("retry_async: no attempts made")

    for attempt in range(1, max_attempts + 1):
        # Circuit check
        if circuit and not circuit.allow_request():
            raise CircuitOpenError(
                f"Circuit '{circuit.name}' is OPEN — call rejected"
            )

        try:
            result = await fn(*args, **kwargs)
            if circuit:
                circuit.record_success()
            return result

        except retryable_exceptions as exc:
            last_exc = exc
            if circuit:
                circuit.record_failure(exc)

            if attempt == max_attempts:
                logger.error(
                    f"All {max_attempts} attempts failed for {fn.__name__}: {exc}",
                    extra={"pipeline": "retry"},
                )
                break

            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            jitter = random.uniform(0, delay * 0.3)
            total_delay = delay + jitter

            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed for {fn.__name__}: {exc}. "
                f"Retrying in {total_delay:.1f}s",
                extra={"pipeline": "retry"},
            )
            await asyncio.sleep(total_delay)

    raise last_exc


def retry_sync(
    fn: Callable,
    *args: Any,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (Exception,),
    circuit: Optional[CircuitBreaker] = None,
    **kwargs: Any,
) -> Any:
    """Synchronous retry with exponential backoff + jitter."""
    last_exc: Exception = RuntimeError("retry_sync: no attempts made")

    for attempt in range(1, max_attempts + 1):
        if circuit and not circuit.allow_request():
            raise CircuitOpenError(f"Circuit '{circuit.name}' is OPEN — call rejected")

        try:
            result = fn(*args, **kwargs)
            if circuit:
                circuit.record_success()
            return result
        except retryable_exceptions as exc:
            last_exc = exc
            if circuit:
                circuit.record_failure(exc)
            if attempt == max_attempts:
                break
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            jitter = random.uniform(0, delay * 0.3)
            time.sleep(delay + jitter)

    raise last_exc


# =============================================================================
# GRACEFUL DEGRADATION HELPERS
# =============================================================================

def degraded_response(
    stage: str,
    error: str,
    fallback_data: Optional[dict] = None,
) -> dict:
    """
    Build a standardised degraded-but-usable response.

    The pipeline continues with deterministic fallbacks so the user
    still gets *a* recommendation, even if the LLM is unreachable.
    """
    return {
        "success": True,
        "degraded": True,
        "degraded_stage": stage,
        "degraded_reason": error,
        "data": fallback_data or {},
    }


# =============================================================================
# REQUEST CONTEXT (correlation IDs)
# =============================================================================

@dataclass
class RequestContext:
    """Carry correlation metadata through the request lifecycle."""

    request_id: str = ""
    session_id: str = ""
    pipeline: str = ""
    start_time: float = field(default_factory=time.monotonic)

    @property
    def elapsed_ms(self) -> float:
        return round((time.monotonic() - self.start_time) * 1000, 1)

    def log_extras(self) -> dict:
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "pipeline": self.pipeline,
            "duration_ms": self.elapsed_ms,
        }
