"""
CycloneShield AI — Input / Output Validators
Validates weather data, agent outputs and prompt content.
"""
import re
import json
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator
from utils.logging_config import get_logger

logger = get_logger("validators")

# ── Prompt-injection protection ────────────────────────────────────────────────
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"forget\s+(all\s+)?previous",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(a\s+)?(?!weather|cyclone|impact)",
    r"jailbreak",
    r"dan\s+mode",
    r"system\s+prompt",
    r"<\s*script",
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__",
    r"os\.system",
    r"subprocess",
]

_INJECTION_RE = re.compile(
    "|".join(_INJECTION_PATTERNS), re.IGNORECASE
)


def check_prompt_injection(text: str) -> tuple[bool, str]:
    """
    Returns (is_safe, reason).
    is_safe=True means no injection detected.
    """
    if not isinstance(text, str):
        return False, "Input must be a string"
    match = _INJECTION_RE.search(text)
    if match:
        return False, f"Potential prompt injection detected: '{match.group()[:40]}'"
    if len(text) > 10_000:
        return False, "Input exceeds maximum allowed length (10 000 chars)"
    return True, "ok"


# ── Weather data validation ───────────────────────────────────────────────────
WEATHER_RANGES = {
    "pressure_hpa":       (870.0,  1050.0),
    "wind_speed_kmh":     (0.0,    350.0),
    "wind_direction_deg": (0.0,    360.0),
    "humidity_pct":       (0.0,    100.0),
    "rainfall_mm":        (0.0,    500.0),
    "sea_surface_temp_c": (15.0,   35.0),
    "visibility_km":      (0.0,    50.0),
    "wave_height_m":      (0.0,    20.0),
}


def validate_weather_reading(reading: dict) -> tuple[bool, list[str]]:
    """
    Validate a single weather reading dict.
    Returns (is_valid, list_of_issues).
    """
    issues: list[str] = []
    required = ["pressure_hpa", "wind_speed_kmh", "humidity_pct"]
    for field in required:
        if field not in reading or reading[field] is None:
            issues.append(f"Missing required field: {field}")

    for field, (lo, hi) in WEATHER_RANGES.items():
        if field in reading and reading[field] is not None:
            try:
                val = float(reading[field])
                if not (lo <= val <= hi):
                    issues.append(
                        f"{field}={val} out of valid range [{lo}, {hi}]"
                    )
            except (TypeError, ValueError):
                issues.append(f"{field} is not a valid number: {reading[field]}")

    return len(issues) == 0, issues


def validate_agent_json_output(data: Any, required_keys: list[str]) -> tuple[bool, list[str]]:
    """Check that agent output is a dict with all required top-level keys."""
    issues: list[str] = []
    if not isinstance(data, dict):
        return False, ["Agent output is not a JSON object"]
    for key in required_keys:
        if key not in data:
            issues.append(f"Missing required key: '{key}'")
    return len(issues) == 0, issues


def sanitize_location_input(location: str) -> str:
    """Strip potentially dangerous characters from location strings."""
    sanitized = re.sub(r"[^\w\s,.\-()]", "", location)
    return sanitized[:200].strip()


def extract_json_from_text(text: str) -> Optional[dict]:
    """Try to extract a JSON object from an LLM response string."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Try to find JSON block between ```json and ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try to find first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None
