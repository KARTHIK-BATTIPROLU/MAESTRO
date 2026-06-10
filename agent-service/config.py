"""
MAESTRO Agent Service Configuration

Validation:
  - GEMINI_API_KEY (or GOOGLE_API_KEY legacy fallback) required for LLM pipelines
  - PORT must be a valid integer
  - TEMPERATURE is clamped to [0.0, 1.0]
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def _parse_int(value: str, default: int, name: str) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        print(f"WARNING: Invalid {name}='{value}', using default {default}")
        return default


def _parse_float_clamped(value: str, default: float, lo: float, hi: float, name: str) -> float:
    try:
        v = float(value)
        return max(lo, min(hi, v))
    except (ValueError, TypeError):
        return default


class Config:
    # Accept GEMINI_API_KEY (primary, matches render.yaml) or GOOGLE_API_KEY (legacy fallback)
    GOOGLE_API_KEY = (
        os.getenv("GEMINI_API_KEY") or
        os.getenv("GOOGLE_API_KEY")
    )
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = _parse_int(os.getenv("PORT", "8000"), 8000, "PORT")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # Agent configuration
    MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash")
    TEMPERATURE = _parse_float_clamped(
        os.getenv("TEMPERATURE", "0.2"), 0.2, 0.0, 1.0, "TEMPERATURE"
    )
    MAX_TOKENS = _parse_int(os.getenv("MAX_TOKENS", "4096"), 4096, "MAX_TOKENS")

    # Resilience settings
    LLM_TIMEOUT_SECONDS = _parse_int(
        os.getenv("LLM_TIMEOUT_SECONDS", "120"), 120, "LLM_TIMEOUT_SECONDS"
    )
    CIRCUIT_FAILURE_THRESHOLD = _parse_int(
        os.getenv("CIRCUIT_FAILURE_THRESHOLD", "3"), 3, "CIRCUIT_FAILURE_THRESHOLD"
    )
    CIRCUIT_RECOVERY_TIMEOUT = _parse_int(
        os.getenv("CIRCUIT_RECOVERY_TIMEOUT", "60"), 60, "CIRCUIT_RECOVERY_TIMEOUT"
    )

    @classmethod
    def validate(cls):
        """Run startup validation. Call once at boot."""
        issues = []
        if not cls.GOOGLE_API_KEY:
            issues.append(
                "Neither GEMINI_API_KEY nor GOOGLE_API_KEY is set — LLM pipelines will be unavailable"
            )
        if cls.PORT < 1 or cls.PORT > 65535:
            issues.append(f"PORT={cls.PORT} out of range")
        for msg in issues:
            print(f"CONFIG WARNING: {msg}", file=sys.stderr)
        return len(issues) == 0
