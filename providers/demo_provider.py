"""
CycloneShield AI — Demo LLM Provider
Returns realistic structured responses without calling any real API.
Used when no API keys are configured, or APP_MODE=demo.
"""
import json
import time
import random
from providers.base import BaseLLMProvider, LLMResponse

# Pre-written demo responses keyed by context keywords
_DEMO_RESPONSES = {
    "weather": {
        "analysis_summary": "⚠️ DEMO MODE — Weather analysis based on sample data",
        "pressure_trend": "Falling — pressure dropped from 998 hPa to 984 hPa over 6 hours",
        "wind_assessment": "Strong winds detected at Gopalpur (118 km/h) and Puri (108 km/h)",
        "humidity_level": "Very high (94–98%) at coastal stations — indicative of intense moisture",
        "anomalies_detected": [
            "Pressure below 990 hPa at multiple stations",
            "Wind speeds exceeding 100 km/h at Gopalpur",
            "Rainfall >80 mm/6h at Gopalpur and Puri"
        ],
        "missing_fields": [],
        "data_quality": "good",
        "recommendation": "Escalate to Cyclone Detection Agent",
        "confidence": 0.88,
        "data_source": "sample",
        "timestamp": "2024-10-25T12:00:00Z"
    },
    "cyclone": {
        "analysis_summary": "⚠️ DEMO MODE — Cyclone analysis based on sample track data",
        "cyclone_detected": True,
        "storm_name": "Cyclone AGNI (Sample)",
        "current_intensity": "Super Cyclonic Storm",
        "current_position": {"latitude": 19.8, "longitude": 78.5},
        "wind_speed_kmh": 215,
        "pressure_hpa": 920,
        "movement_direction": "NNW",
        "movement_speed_kmh": 18,
        "landfall_probability": "High",
        "landfall_region": "Odisha–Andhra Pradesh coast (sample estimate)",
        "landfall_time_est": "Within 12–18 hours of last observation",
        "saffir_simpson_category": 4,
        "data_source": "sample",
        "uncertainty": "Forecast based on sample data — not a real official forecast",
        "confidence": 0.82
    },
    "impact": {
        "analysis_summary": "⚠️ DEMO MODE — Impact assessment based on sample data. Not a real observation.",
        "overall_risk_level": "VERY HIGH",
        "risk_justification": "Super Cyclonic Storm with 215 km/h winds approaching densely populated Odisha coast",
        "affected_districts": [
            {"district": "Ganjam", "state": "Odisha", "risk": "EXTREME", "population_at_risk": "~1.2 million"},
            {"district": "Puri", "state": "Odisha", "risk": "VERY HIGH", "population_at_risk": "~850,000"},
            {"district": "Khordha", "state": "Odisha", "risk": "HIGH", "population_at_risk": "~2.1 million"},
            {"district": "Srikakulam", "state": "Andhra Pradesh", "risk": "HIGH", "population_at_risk": "~1.4 million"}
        ],
        "storm_surge_estimate_m": "3–5 metres above normal tide",
        "rainfall_forecast_mm": "200–400 mm in 24 hours",
        "wind_damage_potential": "Severe structural damage expected — DEMO sample estimate only",
        "preparedness_actions": [
            "Ensure emergency supply kits are ready (water, food, first aid)",
            "Identify and note nearest cyclone shelter location",
            "Charge all communication devices",
            "Secure loose outdoor objects and signboards",
            "Keep important documents in a waterproof bag",
            "Follow official IMD and NDMA advisories",
            "Alert fishermen — no sea entry until all-clear",
            "Pre-position NDRF teams at vulnerable points"
        ],
        "vulnerable_groups": ["Elderly", "Children", "Coastal fishing communities", "Differently-abled"],
        "infrastructure_at_risk": ["Coastal roads", "Power lines", "Fishing boats", "Agricultural crops"],
        "recommended_alert_level": "ORANGE",
        "imd_contact": "Call IMD: 1800-180-1717 | mausam.imd.gov.in | NDMA: 011-26701700",
        "official_warning_note": "⚠️ DEMO/SAMPLE DATA — This is an AI-generated decision-support assessment ONLY. It is NOT an official IMD warning. For official alerts, contact IMD at 1800-180-1717 or visit mausam.imd.gov.in.",
        "data_source": "sample",
        "confidence": 0.79
    }
}


class DemoProvider(BaseLLMProvider):
    """
    Demo LLM provider — returns realistic pre-written responses.
    Clearly labels all output as demo / sample data.
    """
    provider_name = "demo"
    model_name = "cycloneshield-demo-v1"

    def complete(self, prompt: str, system_prompt: str = "", max_tokens: int = 1024) -> LLMResponse:
        time.sleep(random.uniform(0.3, 0.8))  # simulate API latency

        prompt_lower = prompt.lower()
        # Check most-specific patterns first to avoid false positives
        if "impact" in prompt_lower or "preparedness" in prompt_lower or "evacuate" in prompt_lower or "affected_districts" in prompt_lower or "overall_risk_level" in prompt_lower:
            data = _DEMO_RESPONSES["impact"]
        elif "cyclone_detected" in prompt_lower or "track" in prompt_lower or "storm" in prompt_lower or "landfall" in prompt_lower or "intensity" in prompt_lower:
            data = _DEMO_RESPONSES["cyclone"]
        elif "weather" in prompt_lower or "meteorolog" in prompt_lower or "pressure" in prompt_lower or "humidity" in prompt_lower or "station" in prompt_lower:
            data = _DEMO_RESPONSES["weather"]
        else:
            data = {
                "summary": "⚠️ DEMO MODE — CycloneShield AI is running in demo mode.",
                "note": "Configure a real API key in .env to enable live AI analysis.",
                "data_source": "demo"
            }

        text = json.dumps(data, indent=2)
        tokens = len(prompt.split()) + len(text.split())
        return LLMResponse(
            text=text,
            model=self.model_name,
            provider=self.provider_name,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(text.split()),
            total_tokens=tokens,
            latency_ms=random.uniform(300, 800),
            estimated_cost_usd=0.0,
            is_demo=True,
        )
