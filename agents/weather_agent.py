"""
CycloneShield AI — Agent 1: Weather Intelligence Agent
Validates and analyzes meteorological data.
Never invents missing measurements.
"""
import json
import time
from datetime import datetime, timezone
from typing import Any, Optional

from providers.base import BaseLLMProvider, LLMResponse
from utils.validators import validate_weather_reading, extract_json_from_text, check_prompt_injection
from utils.logging_config import log_agent_event, get_logger

logger = get_logger("WeatherAgent")

AGENT_NAME = "Weather Intelligence Agent"

SYSTEM_PROMPT = """You are the Weather Intelligence Agent for CycloneShield AI, an emergency
management system for coastal India. Your role is to analyze meteorological data and identify
conditions that may indicate cyclone development.

STRICT RULES:
1. Only analyze data that is explicitly provided to you.
2. Never invent, estimate, or fabricate sensor readings.
3. If a measurement is missing, flag it as missing — do not guess.
4. Output ONLY valid JSON matching the required schema.
5. All wind speeds in km/h, pressure in hPa, temperature in Celsius.
6. This is a decision-support tool. Never claim your analysis is an official IMD warning.

ANOMALY THRESHOLDS (Bay of Bengal context):
- Pressure < 990 hPa → potential depression/cyclone
- Wind speed > 63 km/h (34 knots) → cyclonic storm threshold
- Humidity > 90% combined with falling pressure → high alert
- Rapid pressure fall (>3 hPa/hour) → significant concern
"""

REQUIRED_OUTPUT_KEYS = [
    "analysis_summary", "pressure_trend", "wind_assessment",
    "humidity_level", "anomalies_detected", "missing_fields",
    "data_quality", "recommendation", "confidence",
    "data_source", "timestamp"
]


def run_weather_agent(
    weather_data: list[dict],
    provider: BaseLLMProvider,
    location_context: str = "Bay of Bengal coastal India",
) -> dict:
    """
    Execute the Weather Intelligence Agent.

    Args:
        weather_data: List of weather reading dicts (from CSV or API).
        provider: LLM provider instance.
        location_context: Geographic context string.

    Returns:
        dict with keys: agent_name, status, output, llm_response_meta, validation_issues, duration_ms
    """
    start_time = time.perf_counter()
    log_agent_event(AGENT_NAME, "start", input_summary=f"{len(weather_data)} weather readings, location: {location_context}")

    result = {
        "agent_name": AGENT_NAME,
        "status": "error",
        "output": {},
        "llm_response_meta": {},
        "validation_issues": [],
        "duration_ms": 0.0,
    }

    # Step 0: Check for prompt injection FIRST
    safe, reason = check_prompt_injection(location_context)
    if not safe:
        log_agent_event(AGENT_NAME, "error", status="error", error_msg=f"Injection blocked: {reason}")
        result["output"] = {"error": f"Input rejected: {reason}", "data_source": "blocked"}
        result["duration_ms"] = (time.perf_counter() - start_time) * 1000
        return result

    # Step 1: Validate all input readings
    all_issues = []
    valid_readings = []
    for i, reading in enumerate(weather_data):
        valid, issues = validate_weather_reading(reading)
        if issues:
            all_issues.extend([f"Reading {i+1}: {iss}" for iss in issues])
        if valid or len(issues) < 3:  # keep partially valid readings
            valid_readings.append(reading)

    if not valid_readings:
        msg = "No valid weather readings to analyze"
        log_agent_event(AGENT_NAME, "error", status="error", error_msg=msg)
        result["validation_issues"] = all_issues
        result["output"] = {"error": msg, "data_source": "none"}
        result["duration_ms"] = (time.perf_counter() - start_time) * 1000
        return result

    result["validation_issues"] = all_issues

    # Step 2: Build summary statistics for prompt
    pressures = [r["pressure_hpa"] for r in valid_readings if r.get("pressure_hpa") is not None]
    winds = [r["wind_speed_kmh"] for r in valid_readings if r.get("wind_speed_kmh") is not None]
    humidity = [r["humidity_pct"] for r in valid_readings if r.get("humidity_pct") is not None]
    rainfall = [r.get("rainfall_mm", 0) for r in valid_readings if r.get("rainfall_mm") is not None]
    sst = [r.get("sea_surface_temp_c") for r in valid_readings if r.get("sea_surface_temp_c") is not None]

    stats_summary = {
        "station_count": len(valid_readings),
        "pressure_min_hpa": min(pressures) if pressures else None,
        "pressure_max_hpa": max(pressures) if pressures else None,
        "pressure_avg_hpa": round(sum(pressures) / len(pressures), 1) if pressures else None,
        "wind_max_kmh": max(winds) if winds else None,
        "wind_avg_kmh": round(sum(winds) / len(winds), 1) if winds else None,
        "humidity_avg_pct": round(sum(humidity) / len(humidity), 1) if humidity else None,
        "rainfall_total_mm": round(sum(rainfall), 1) if rainfall else None,
        "sst_avg_c": round(sum(sst) / len(sst), 1) if sst else None,
        "stations": [r.get("station_name", r.get("station_id", "unknown")) for r in valid_readings[:6]],
    }

    # Step 3: Build prompt
    prompt = f"""Analyze the following weather station data for {location_context}.

WEATHER STATISTICS SUMMARY:
{json.dumps(stats_summary, indent=2)}

RAW STATION READINGS (latest {min(6, len(valid_readings))} stations):
{json.dumps(valid_readings[:6], indent=2, default=str)}

TASK: Analyze this data and return a JSON object with exactly these keys:
- analysis_summary: One paragraph describing overall weather conditions
- pressure_trend: Assessment of pressure levels and trend (rising/falling/stable)
- wind_assessment: Assessment of wind speed and direction patterns
- humidity_level: Assessment of humidity observations
- anomalies_detected: Array of strings describing any unusual observations
- missing_fields: Array of field names that have missing data
- data_quality: "good" | "partial" | "poor"
- recommendation: "Escalate to Cyclone Detection Agent" | "Monitor" | "Normal operations"
- confidence: float 0.0–1.0 representing analysis confidence
- data_source: "live" | "sample" | "demo"
- timestamp: ISO8601 timestamp of this analysis

Return ONLY the JSON object. No explanation text outside the JSON."""

    # Step 4: Call LLM
    llm_response: LLMResponse = provider.complete(prompt, system_prompt=SYSTEM_PROMPT, max_tokens=1500)

    result["llm_response_meta"] = {
        "provider": llm_response.provider,
        "model": llm_response.model,
        "latency_ms": llm_response.latency_ms,
        "tokens": llm_response.total_tokens,
        "cost_usd": llm_response.estimated_cost_usd,
        "is_demo": llm_response.is_demo,
        "error": llm_response.error,
    }

    if not llm_response.success:
        log_agent_event(AGENT_NAME, "error", status="error", error_msg=llm_response.error)
        result["output"] = {"error": llm_response.error, "data_source": "api_error"}
        result["duration_ms"] = (time.perf_counter() - start_time) * 1000
        return result

    # Step 6: Parse and validate output
    parsed = extract_json_from_text(llm_response.text)
    if not parsed:
        # Fallback: build output from stats
        parsed = _build_fallback_output(stats_summary, valid_readings)
        log_agent_event(AGENT_NAME, "error", status="error", error_msg="LLM output not JSON — using fallback")

    # Ensure data_source is marked correctly
    if llm_response.is_demo:
        parsed["data_source"] = "sample"
    parsed["timestamp"] = datetime.now(timezone.utc).isoformat()
    parsed["_stats"] = stats_summary

    duration_ms = (time.perf_counter() - start_time) * 1000
    log_agent_event(
        AGENT_NAME, "complete",
        output_summary=f"Quality: {parsed.get('data_quality')} | Rec: {parsed.get('recommendation')}",
        status="ok", duration_ms=duration_ms
    )

    result["status"] = "ok"
    result["output"] = parsed
    result["duration_ms"] = duration_ms
    return result


def _build_fallback_output(stats: dict, readings: list[dict]) -> dict:
    """Build a rule-based output when LLM parsing fails."""
    pressure_min = stats.get("pressure_min_hpa") or 1013
    wind_max = stats.get("wind_max_kmh") or 0
    anomalies = []

    if pressure_min < 980:
        anomalies.append(f"Critical low pressure: {pressure_min} hPa")
    elif pressure_min < 990:
        anomalies.append(f"Low pressure detected: {pressure_min} hPa")
    if wind_max > 100:
        anomalies.append(f"Dangerous wind speed: {wind_max} km/h")
    elif wind_max > 63:
        anomalies.append(f"Cyclonic wind speed: {wind_max} km/h")

    recommendation = "Normal operations"
    if pressure_min < 985 or wind_max > 100:
        recommendation = "Escalate to Cyclone Detection Agent"
    elif pressure_min < 995 or wind_max > 63:
        recommendation = "Escalate to Cyclone Detection Agent"

    return {
        "analysis_summary": f"Rule-based analysis: Min pressure {pressure_min} hPa, Max wind {wind_max} km/h across {stats.get('station_count', 0)} stations.",
        "pressure_trend": f"Min: {pressure_min} hPa, Avg: {stats.get('pressure_avg_hpa')} hPa",
        "wind_assessment": f"Max: {wind_max} km/h, Avg: {stats.get('wind_avg_kmh')} km/h",
        "humidity_level": f"Average: {stats.get('humidity_avg_pct')}%",
        "anomalies_detected": anomalies,
        "missing_fields": [],
        "data_quality": "good" if not anomalies else "partial",
        "recommendation": recommendation,
        "confidence": 0.7,
        "data_source": "sample",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
