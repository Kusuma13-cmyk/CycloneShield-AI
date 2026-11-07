"""
CycloneShield AI — Agent 3: Impact Assessment & Early Warning Agent
Evaluates coastal impacts and generates preparedness guidance.
Never issues official government warnings. Never invents population data.
"""
import json
import time
from datetime import datetime, timezone
from typing import Optional

from providers.base import BaseLLMProvider, LLMResponse
from utils.validators import extract_json_from_text, sanitize_location_input, check_prompt_injection
from utils.logging_config import log_agent_event, get_logger

logger = get_logger("ImpactAgent")

AGENT_NAME = "Impact Assessment & Early Warning Agent"

SYSTEM_PROMPT = """You are the Impact Assessment & Early Warning Agent for CycloneShield AI.
You receive cyclone analysis results and produce structured impact assessments and preparedness guidance.

STRICT RULES:
1. Never issue official evacuation orders — only preparedness recommendations.
2. Always include: "IMPORTANT: Contact IMD (1800-180-1717) for official warnings."
3. Risk categories must be justified by the data provided.
4. Do not invent population figures — use provided data or state "data unavailable."
5. Preparedness actions must be practical and evidence-based.
6. Output ONLY valid JSON matching the required schema.
7. Clearly separate what is known (data-based) from what is estimated (model-based).

RISK LEVELS:
- EXTREME: Super Cyclonic Storm making landfall, wind > 200 km/h
- VERY HIGH: Extremely/Very Severe, wind 150–200 km/h
- HIGH: Severe Cyclonic Storm, wind 100–150 km/h
- MODERATE: Cyclonic Storm, wind 63–100 km/h
- LOW: Depression/Deep Depression, wind < 63 km/h
- MINIMAL: No cyclone detected
"""

# Static coastal vulnerability data for reference
COASTAL_DISTRICTS = {
    "Ganjam": {"state": "Odisha", "coast_km": 62, "pop_approx": "1.2M", "vulnerability": "very_high"},
    "Puri": {"state": "Odisha", "coast_km": 148, "pop_approx": "850K", "vulnerability": "very_high"},
    "Jagatsinghpur": {"state": "Odisha", "coast_km": 45, "pop_approx": "450K", "vulnerability": "high"},
    "Kendrapara": {"state": "Odisha", "coast_km": 87, "pop_approx": "480K", "vulnerability": "high"},
    "Bhadrak": {"state": "Odisha", "coast_km": 52, "pop_approx": "350K", "vulnerability": "high"},
    "Balasore": {"state": "Odisha", "coast_km": 90, "pop_approx": "690K", "vulnerability": "high"},
    "Srikakulam": {"state": "Andhra Pradesh", "coast_km": 193, "pop_approx": "1.4M", "vulnerability": "high"},
    "Vizianagaram": {"state": "Andhra Pradesh", "coast_km": 0, "pop_approx": "700K", "vulnerability": "moderate"},
    "Visakhapatnam": {"state": "Andhra Pradesh", "coast_km": 65, "pop_approx": "5.3M", "vulnerability": "very_high"},
    "East Godavari": {"state": "Andhra Pradesh", "coast_km": 120, "pop_approx": "1.8M", "vulnerability": "high"},
}


def run_impact_agent(
    cyclone_analysis: dict,
    weather_analysis: dict,
    provider: BaseLLMProvider,
    target_region: str = "Odisha and Andhra Pradesh coast",
) -> dict:
    """
    Execute the Impact Assessment & Early Warning Agent.

    Args:
        cyclone_analysis: Output from Cyclone Detection & Tracking Agent.
        weather_analysis: Output from Weather Intelligence Agent.
        provider: LLM provider instance.
        target_region: Geographic region to assess.

    Returns:
        dict with keys: agent_name, status, output, llm_response_meta, duration_ms
    """
    start_time = time.perf_counter()
    log_agent_event(
        AGENT_NAME, "start",
        input_summary=f"Cyclone: {cyclone_analysis.get('storm_name','?')} | Region: {target_region}"
    )

    result = {
        "agent_name": AGENT_NAME,
        "status": "error",
        "output": {},
        "llm_response_meta": {},
        "duration_ms": 0.0,
    }

    # Sanitize location input
    safe_region = sanitize_location_input(target_region)
    safe, reason = check_prompt_injection(target_region)
    if not safe:
        log_agent_event(AGENT_NAME, "error", status="error", error_msg=f"Injection: {reason}")
        result["output"] = {"error": f"Input rejected: {reason}"}
        result["duration_ms"] = (time.perf_counter() - start_time) * 1000
        return result

    # Determine risk level from cyclone data (rule-based initial estimate)
    wind_speed = cyclone_analysis.get("wind_speed_kmh") or 0
    initial_risk = _estimate_risk_level(wind_speed, cyclone_analysis)

    prompt = f"""Perform an impact assessment for {safe_region}.

CYCLONE DETECTION AGENT OUTPUT:
{json.dumps({k: v for k, v in cyclone_analysis.items() if k not in ['_track_summary', 'timestamp']}, indent=2)}

WEATHER CONDITIONS SUMMARY:
{json.dumps({k: v for k, v in weather_analysis.items() if k not in ['_stats', 'timestamp']}, indent=2)}

COASTAL VULNERABILITY REFERENCE DATA:
{json.dumps({k: v for k, v in list(COASTAL_DISTRICTS.items())[:6]}, indent=2)}

INITIAL RULE-BASED RISK ESTIMATE: {initial_risk}

TASK: Produce a comprehensive impact assessment as a JSON object with exactly these keys:
- analysis_summary: One paragraph overview of expected impact
- overall_risk_level: "EXTREME" | "VERY HIGH" | "HIGH" | "MODERATE" | "LOW" | "MINIMAL"
- risk_justification: Why this risk level was assigned (cite the data)
- affected_districts: Array of objects with: district, state, risk, population_at_risk
- storm_surge_estimate_m: String describing expected storm surge
- rainfall_forecast_mm: String describing expected rainfall
- wind_damage_potential: String describing structural damage potential
- preparedness_actions: Array of 6-8 actionable items (no evacuation orders, preparedness only)
- vulnerable_groups: Array of groups needing special attention
- infrastructure_at_risk: Array of infrastructure types at risk
- recommended_alert_level: "RED" | "ORANGE" | "YELLOW" | "GREEN"
- imd_contact: Always include "Call IMD: 1800-180-1717 | Website: mausam.imd.gov.in"
- official_warning_note: Disclaimer that this is AI assessment, not official warning
- data_source: "live" | "sample" | "demo"
- confidence: float 0.0-1.0

Return ONLY the JSON object."""

    llm_response: LLMResponse = provider.complete(prompt, system_prompt=SYSTEM_PROMPT, max_tokens=2000)

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
        result["output"] = _build_fallback_impact_output(cyclone_analysis, initial_risk)
        result["duration_ms"] = (time.perf_counter() - start_time) * 1000
        return result

    parsed = extract_json_from_text(llm_response.text)
    if not parsed:
        parsed = _build_fallback_impact_output(cyclone_analysis, initial_risk)
        log_agent_event(AGENT_NAME, "error", status="error", error_msg="LLM output not JSON — using fallback")

    if llm_response.is_demo:
        parsed["data_source"] = "sample"

    # Always enforce official warning disclaimer
    parsed["official_warning_note"] = (
        "⚠️ This is an AI-generated decision-support assessment ONLY. "
        "It is NOT an official IMD warning. For official alerts, contact IMD at "
        "1800-180-1717 or visit mausam.imd.gov.in. "
        "Do not take evacuation actions based solely on this AI assessment."
    )
    parsed["imd_contact"] = "Call IMD: 1800-180-1717 | mausam.imd.gov.in | NDMA: 011-26701700"
    parsed["timestamp"] = datetime.now(timezone.utc).isoformat()

    duration_ms = (time.perf_counter() - start_time) * 1000
    log_agent_event(
        AGENT_NAME, "complete",
        output_summary=f"Risk: {parsed.get('overall_risk_level')} | Alert: {parsed.get('recommended_alert_level')}",
        status="ok", duration_ms=duration_ms
    )

    result["status"] = "ok"
    result["output"] = parsed
    result["duration_ms"] = duration_ms
    return result


def _estimate_risk_level(wind_kmh: float, cyclone_data: dict) -> str:
    """Rule-based initial risk estimate from wind speed."""
    if not cyclone_data.get("cyclone_detected", False):
        return "MINIMAL"
    if wind_kmh >= 200:
        return "EXTREME"
    if wind_kmh >= 168:
        return "VERY HIGH"
    if wind_kmh >= 118:
        return "HIGH"
    if wind_kmh >= 89:
        return "MODERATE"
    if wind_kmh >= 63:
        return "LOW"
    return "MINIMAL"


def _build_fallback_impact_output(cyclone_data: dict, risk_level: str) -> dict:
    """Rule-based fallback impact assessment."""
    wind = cyclone_data.get("wind_speed_kmh") or 0
    storm_surge = "1–2 m" if wind < 120 else ("2–4 m" if wind < 180 else "4–6+ m")
    rainfall = "50–100 mm/day" if wind < 120 else ("100–250 mm/day" if wind < 180 else "200–400 mm/day")

    return {
        "analysis_summary": f"Rule-based assessment: {risk_level} risk. Cyclone with {wind} km/h winds approaching coast.",
        "overall_risk_level": risk_level,
        "risk_justification": f"Wind speed {wind} km/h places this in {risk_level} category per IMD scale.",
        "affected_districts": [
            {"district": "Ganjam", "state": "Odisha", "risk": risk_level, "population_at_risk": "~1.2M"},
            {"district": "Puri", "state": "Odisha", "risk": risk_level, "population_at_risk": "~850K"},
        ],
        "storm_surge_estimate_m": storm_surge,
        "rainfall_forecast_mm": rainfall,
        "wind_damage_potential": f"Significant structural damage expected at {wind} km/h",
        "preparedness_actions": [
            "Ensure emergency supply kits are ready (water, food, first aid)",
            "Identify nearest cyclone shelter",
            "Charge all communication devices",
            "Secure loose outdoor objects",
            "Keep important documents in waterproof bag",
            "Follow official IMD and NDMA advisories",
        ],
        "vulnerable_groups": ["Elderly", "Children", "Coastal fishing communities", "Differently-abled"],
        "infrastructure_at_risk": ["Coastal roads", "Power lines", "Fishing boats", "Agricultural crops"],
        "recommended_alert_level": "RED" if risk_level in ["EXTREME", "VERY HIGH"] else "ORANGE",
        "imd_contact": "Call IMD: 1800-180-1717 | mausam.imd.gov.in | NDMA: 011-26701700",
        "official_warning_note": (
            "⚠️ AI-generated assessment only. Not an official IMD warning. "
            "Contact IMD at 1800-180-1717 for official bulletins."
        ),
        "data_source": "sample",
        "confidence": 0.7,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
