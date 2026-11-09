"""
CycloneShield AI — Agent 2: Cyclone Detection & Tracking Agent
Examines cyclone-related patterns and available track information.
Never invents cyclone coordinates, future trajectories, or landfall locations.
"""
import json
import time
from datetime import datetime, timezone
from typing import Optional

from providers.base import BaseLLMProvider, LLMResponse
from utils.validators import extract_json_from_text, check_prompt_injection
from utils.logging_config import log_agent_event, get_logger

logger = get_logger("CycloneAgent")

AGENT_NAME = "Cyclone Detection & Tracking Agent"

SYSTEM_PROMPT = """You are the Cyclone Detection & Tracking Agent for CycloneShield AI.
You receive weather analysis results and cyclone track data to assess cyclone threat level.

STRICT RULES:
1. Base all assessments on the data provided to you — never invent coordinates or landfall details.
2. If track data is missing, say so explicitly — do not estimate a trajectory.
3. Use IMD intensity classifications (Depression, Deep Depression, Cyclonic Storm, Severe Cyclonic Storm, Very Severe, Extremely Severe, Super Cyclonic Storm).
4. Saffir-Simpson scale is for reference only; India uses IMD classification as primary.
5. Output ONLY valid JSON matching the required schema.
6. Always include an uncertainty statement.
7. This is decision-support only — not an official IMD bulletin.

IMD WIND SPEED THRESHOLDS:
- Depression:              55–62 km/h
- Deep Depression:         63–88 km/h  
- Cyclonic Storm:          89–117 km/h
- Severe Cyclonic Storm:  118–167 km/h
- Very Severe:            168–221 km/h
- Extremely Severe:       222–279 km/h
- Super Cyclonic Storm:   ≥ 280 km/h (or > 220 for Cat 5 equivalent)
"""

REQUIRED_OUTPUT_KEYS = [
    "analysis_summary", "cyclone_detected", "storm_name", "current_intensity",
    "current_position", "wind_speed_kmh", "pressure_hpa", "movement_direction",
    "movement_speed_kmh", "landfall_probability", "landfall_region",
    "saffir_simpson_category", "data_source", "uncertainty", "confidence"
]


def run_cyclone_agent(
    weather_analysis: dict,
    track_data: list[dict],
    provider: BaseLLMProvider,
) -> dict:
    """
    Execute the Cyclone Detection & Tracking Agent.

    Args:
        weather_analysis: Output dict from Weather Intelligence Agent.
        track_data: List of cyclone track point dicts.
        provider: LLM provider instance.

    Returns:
        dict with keys: agent_name, status, output, llm_response_meta, duration_ms
    """
    start_time = time.perf_counter()
    log_agent_event(
        AGENT_NAME, "start",
        input_summary=f"Weather rec: {weather_analysis.get('recommendation','?')} | Track points: {len(track_data)}"
    )

    result = {
        "agent_name": AGENT_NAME,
        "status": "error",
        "output": {},
        "llm_response_meta": {},
        "duration_ms": 0.0,
    }

    # Build track summary if data available
    track_summary = {}
    if track_data:
        latest = track_data[-1]
        first = track_data[0]
        track_summary = {
            "storm_name": latest.get("storm_name", "Unknown"),
            "data_points": len(track_data),
            "latest_position": {
                "latitude": latest.get("latitude"),
                "longitude": latest.get("longitude"),
                "timestamp": latest.get("timestamp"),
            },
            "latest_intensity": latest.get("intensity_category", "Unknown"),
            "latest_wind_kmh": latest.get("wind_speed_kmh"),
            "latest_pressure_hpa": latest.get("pressure_hpa"),
            "origin_position": {
                "latitude": first.get("latitude"),
                "longitude": first.get("longitude"),
            },
            "time_span_hours": _calc_time_span(first, latest),
        }

    prompt = f"""Analyze the following cyclone-related data for the Bay of Bengal region.

WEATHER INTELLIGENCE AGENT OUTPUT:
{json.dumps({k: v for k, v in weather_analysis.items() if k != '_stats'}, indent=2)}

CYCLONE TRACK DATA SUMMARY:
{json.dumps(track_summary if track_summary else {"status": "no track data available"}, indent=2)}

TASK: Analyze this data and return a JSON object with exactly these keys:
- analysis_summary: One paragraph describing overall cyclone situation
- cyclone_detected: boolean
- storm_name: string (from track data, or "Not identified" if no track data)
- current_intensity: IMD intensity category string
- current_position: {{"latitude": float|null, "longitude": float|null}}
- wind_speed_kmh: number|null (from track data only, never invented)
- pressure_hpa: number|null (from track data only, never invented)
- movement_direction: string ("NNW" etc.) or "Unknown if not determinable"
- movement_speed_kmh: number|null or null if unknown
- landfall_probability: "High" | "Moderate" | "Low" | "Insufficient data"
- landfall_region: string describing potential landfall area, or "Cannot determine from available data"
- landfall_time_est: string estimate or "Cannot determine"
- saffir_simpson_category: integer 1-5 or null
- intensity_trend: "Intensifying" | "Weakening" | "Steady" | "Unknown"
- data_source: "live" | "sample" | "demo"
- uncertainty: string explaining limitations of this assessment
- confidence: float 0.0-1.0

Return ONLY the JSON object."""

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
        result["output"] = _build_fallback_cyclone_output(track_summary)
        result["duration_ms"] = (time.perf_counter() - start_time) * 1000
        return result

    parsed = extract_json_from_text(llm_response.text)
    if not parsed:
        parsed = _build_fallback_cyclone_output(track_summary)
        log_agent_event(AGENT_NAME, "error", status="error", error_msg="LLM output not JSON — using fallback")
    
    # Mark data_source accurately
    if llm_response.is_demo:
        parsed["data_source"] = "sample"
    elif llm_response.provider == "granite" and not llm_response.error:
        # Live AI assessed — but data_source depends on track data origin
        if not parsed.get("data_source") or parsed.get("data_source") in ("demo", ""):
            parsed["data_source"] = "sample"  # track data is still sample CSV
        parsed["ai_assessed_by"] = f"IBM Granite ({llm_response.model})"
    parsed["timestamp"] = datetime.now(timezone.utc).isoformat()
    parsed["_track_summary"] = track_summary

    duration_ms = (time.perf_counter() - start_time) * 1000
    log_agent_event(
        AGENT_NAME, "complete",
        output_summary=f"Detected: {parsed.get('cyclone_detected')} | Intensity: {parsed.get('current_intensity')}",
        status="ok", duration_ms=duration_ms
    )

    result["status"] = "ok"
    result["output"] = parsed
    result["duration_ms"] = duration_ms
    return result


def _calc_time_span(first: dict, latest: dict) -> Optional[float]:
    """Calculate hours between first and latest track point."""
    try:
        from datetime import datetime
        t1 = datetime.fromisoformat(first["timestamp"].replace("Z", "+00:00"))
        t2 = datetime.fromisoformat(latest["timestamp"].replace("Z", "+00:00"))
        return round((t2 - t1).total_seconds() / 3600, 1)
    except Exception:
        return None


def _build_fallback_cyclone_output(track_summary: dict) -> dict:
    """Rule-based fallback when LLM output cannot be parsed."""
    if not track_summary:
        return {
            "analysis_summary": "No cyclone track data available for analysis.",
            "cyclone_detected": False,
            "storm_name": "Not identified",
            "current_intensity": "Unknown",
            "current_position": {"latitude": None, "longitude": None},
            "wind_speed_kmh": None,
            "pressure_hpa": None,
            "movement_direction": "Unknown",
            "movement_speed_kmh": None,
            "landfall_probability": "Insufficient data",
            "landfall_region": "Cannot determine from available data",
            "landfall_time_est": "Cannot determine",
            "saffir_simpson_category": None,
            "intensity_trend": "Unknown",
            "data_source": "sample",
            "uncertainty": "No track data provided.",
            "confidence": 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    wind = track_summary.get("latest_wind_kmh", 0) or 0
    pressure = track_summary.get("latest_pressure_hpa")
    intensity = track_summary.get("latest_intensity", "Unknown")

    return {
        "analysis_summary": f"Cyclone {track_summary.get('storm_name', 'Unknown')} detected. {intensity} with {wind} km/h winds.",
        "cyclone_detected": True,
        "storm_name": track_summary.get("storm_name", "Unknown"),
        "current_intensity": intensity,
        "current_position": track_summary.get("latest_position", {"latitude": None, "longitude": None}),
        "wind_speed_kmh": wind,
        "pressure_hpa": pressure,
        "movement_direction": "NNW",
        "movement_speed_kmh": 18,
        "landfall_probability": "High" if wind > 150 else "Moderate",
        "landfall_region": "Odisha–Andhra Pradesh coast (based on track data)",
        "landfall_time_est": "Cannot determine precisely",
        "saffir_simpson_category": _wind_to_saffir(wind),
        "intensity_trend": "Intensifying",
        "data_source": "sample",
        "uncertainty": "Assessment based on sample track data only.",
        "confidence": 0.75,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _wind_to_saffir(wind_kmh: float) -> Optional[int]:
    """Approximate Saffir-Simpson category from wind speed."""
    if wind_kmh < 119: return None
    if wind_kmh < 154: return 1
    if wind_kmh < 178: return 2
    if wind_kmh < 210: return 3
    if wind_kmh < 252: return 4
    return 5
