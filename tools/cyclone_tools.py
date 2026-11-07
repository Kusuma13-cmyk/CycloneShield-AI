"""
CycloneShield AI — Cyclone Data Tools
Loads cyclone track data from CSV or APIs.
"""
import csv
from pathlib import Path
from utils.logging_config import get_logger, log_agent_event

logger = get_logger("tools.cyclone")

TRACK_CSV = Path(__file__).parent.parent / "data" / "sample_cyclone_track.csv"

# IMD intensity scale for reference
IMD_INTENSITY_ORDER = [
    "Depression",
    "Deep Depression",
    "Cyclonic Storm",
    "Severe Cyclonic Storm",
    "Very Severe Cyclonic Storm",
    "Extremely Severe Cyclonic Storm",
    "Super Cyclonic Storm",
]


def load_sample_track_data() -> list[dict]:
    """Load sample cyclone track data from bundled CSV."""
    track = []
    try:
        with open(TRACK_CSV, "r", newline="", encoding="utf-8") as f:
            lines = [row for row in f if not row.startswith("#") and row.strip()]
            reader = csv.DictReader(lines)
            for row in reader:
                numeric_fields = [
                    "latitude", "longitude", "wind_speed_kmh", "pressure_hpa"
                ]
                for field in numeric_fields:
                    if field in row and row[field]:
                        try:
                            row[field] = float(row[field])
                        except ValueError:
                            row[field] = None
                track.append(row)
        log_agent_event("CycloneTools", "tool_call",
                        input_summary=f"Loaded {len(track)} track points",
                        output_summary="ok", status="ok")
    except FileNotFoundError:
        logger.error("Track CSV not found: %s", TRACK_CSV)
        track = _get_hardcoded_track()
    except Exception as e:
        logger.error("Error reading track CSV: %s", e)
        track = _get_hardcoded_track()
    return track


def cyclone_track_lookup_tool(storm_id: str) -> dict:
    """MCP-compatible cyclone track lookup tool."""
    track = load_sample_track_data()
    filtered = [p for p in track if p.get("storm_id", "") == storm_id]
    if not filtered:
        return {"error": f"No track data found for storm_id: {storm_id}", "data": []}
    return {
        "storm_id": storm_id,
        "storm_name": filtered[0].get("storm_name", "Unknown"),
        "points": len(filtered),
        "data": filtered,
        "data_source": "sample",
        "note": "Sample data — not real-time official track"
    }


def risk_assessment_tool(wind_kmh: float, pressure_hpa: float, distance_km: float) -> dict:
    """
    MCP-compatible risk assessment tool.
    Calculates simple risk score from basic cyclone parameters.
    """
    risk_score = 0.0

    # Wind contribution (0–40 pts)
    if wind_kmh >= 220:
        risk_score += 40
    elif wind_kmh >= 168:
        risk_score += 32
    elif wind_kmh >= 118:
        risk_score += 24
    elif wind_kmh >= 89:
        risk_score += 16
    elif wind_kmh >= 63:
        risk_score += 8

    # Pressure contribution (0–30 pts)
    if pressure_hpa <= 920:
        risk_score += 30
    elif pressure_hpa <= 940:
        risk_score += 24
    elif pressure_hpa <= 960:
        risk_score += 18
    elif pressure_hpa <= 980:
        risk_score += 12
    elif pressure_hpa <= 995:
        risk_score += 6

    # Distance contribution (0–30 pts) — closer = higher risk
    if distance_km <= 100:
        risk_score += 30
    elif distance_km <= 200:
        risk_score += 24
    elif distance_km <= 400:
        risk_score += 15
    elif distance_km <= 600:
        risk_score += 8

    risk_pct = min(risk_score, 100)
    risk_level = (
        "EXTREME" if risk_pct >= 85 else
        "VERY HIGH" if risk_pct >= 70 else
        "HIGH" if risk_pct >= 55 else
        "MODERATE" if risk_pct >= 35 else
        "LOW"
    )
    return {
        "risk_score": round(risk_pct, 1),
        "risk_level": risk_level,
        "inputs": {"wind_kmh": wind_kmh, "pressure_hpa": pressure_hpa, "distance_km": distance_km},
        "note": "Simplified rule-based risk score for decision support only",
    }


def _get_hardcoded_track() -> list[dict]:
    """Minimal hardcoded fallback track."""
    return [
        {"storm_id": "BOB2024_01", "storm_name": "Cyclone AGNI", "timestamp": "2024-10-24T12:00:00Z",
         "latitude": 17.0, "longitude": 80.2, "intensity_category": "Extremely Severe Cyclonic Storm",
         "wind_speed_kmh": 175.0, "pressure_hpa": 942.0, "status": "Active", "source": "Sample"},
        {"storm_id": "BOB2024_01", "storm_name": "Cyclone AGNI", "timestamp": "2024-10-25T09:00:00Z",
         "latitude": 19.8, "longitude": 78.5, "intensity_category": "Super Cyclonic Storm",
         "wind_speed_kmh": 215.0, "pressure_hpa": 920.0, "status": "Landfall-Approaching", "source": "Sample"},
    ]
