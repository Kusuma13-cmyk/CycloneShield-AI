"""
CycloneShield AI — Weather Data Tools
Loads weather data from CSV files or live APIs.
"""
import csv
import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from utils.logging_config import get_logger, log_agent_event

logger = get_logger("tools.weather")

SAMPLE_CSV = Path(__file__).parent.parent / "data" / "sample_weather.csv"


def load_sample_weather_data() -> list[dict]:
    """Load sample weather data from the bundled CSV file."""
    readings = []
    try:
        with open(SAMPLE_CSV, "r", newline="", encoding="utf-8") as f:
            lines = [row for row in f if not row.startswith("#") and row.strip()]
            reader = csv.DictReader(lines)
            for row in reader:
                # Convert numeric fields
                numeric_fields = [
                    "latitude", "longitude", "pressure_hpa", "wind_speed_kmh",
                    "wind_direction_deg", "humidity_pct", "rainfall_mm",
                    "sea_surface_temp_c", "visibility_km", "wave_height_m"
                ]
                for field in numeric_fields:
                    if field in row and row[field]:
                        try:
                            row[field] = float(row[field])
                        except ValueError:
                            row[field] = None
                readings.append(row)
        log_agent_event("WeatherTools", "tool_call",
                        input_summary=f"Loaded {len(readings)} sample readings from CSV",
                        output_summary="ok", status="ok")
    except FileNotFoundError:
        logger.error("Sample weather CSV not found: %s", SAMPLE_CSV)
        readings = _get_hardcoded_fallback()
    except Exception as e:
        logger.error("Error reading weather CSV: %s", e)
        readings = _get_hardcoded_fallback()
    return readings


def load_live_weather_data(location: str = "Chennai") -> list[dict]:
    """
    Attempt to load live weather data from OpenWeatherMap API.
    Returns empty list if API key not configured or request fails.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY", "")
    if not api_key:
        logger.info("OPENWEATHER_API_KEY not set — live weather unavailable")
        return []

    # Bay of Bengal coastal cities to query
    cities = [
        ("Chennai", 13.08, 80.27),
        ("Visakhapatnam", 17.68, 83.22),
        ("Bhubaneswar", 20.29, 85.82),
        ("Kolkata", 22.57, 88.36),
        ("Puri", 19.80, 85.83),
    ]

    readings = []
    for city, lat, lon in cities:
        try:
            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?lat={lat}&lon={lon}&appid={api_key}&units=metric"
            )
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                reading = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "station_id": f"OWM_{city[:3].upper()}",
                    "station_name": city,
                    "latitude": lat,
                    "longitude": lon,
                    "pressure_hpa": data.get("main", {}).get("pressure"),
                    "wind_speed_kmh": round((data.get("wind", {}).get("speed", 0) or 0) * 3.6, 1),
                    "wind_direction_deg": data.get("wind", {}).get("deg"),
                    "humidity_pct": data.get("main", {}).get("humidity"),
                    "rainfall_mm": data.get("rain", {}).get("1h", 0),
                    "sea_surface_temp_c": None,  # Not in basic API
                    "visibility_km": round((data.get("visibility", 10000) or 10000) / 1000, 1),
                    "wave_height_m": None,
                    "data_source": "live_openweathermap",
                }
                readings.append(reading)
        except Exception as e:
            logger.warning("OWM request failed for %s: %s", city, e)

    log_agent_event("WeatherTools", "tool_call",
                    input_summary=f"Live weather loaded for {len(readings)} cities",
                    output_summary="ok" if readings else "empty", status="ok")
    return readings


def validate_weather_tool(readings: list[dict]) -> dict:
    """MCP-compatible weather validation tool."""
    from utils.validators import validate_weather_reading
    results = []
    for r in readings:
        valid, issues = validate_weather_reading(r)
        results.append({
            "station": r.get("station_name", "?"),
            "valid": valid,
            "issues": issues,
        })
    return {
        "total": len(readings),
        "valid": sum(1 for r in results if r["valid"]),
        "results": results,
    }


def _get_hardcoded_fallback() -> list[dict]:
    """Minimal hardcoded fallback if CSV fails to load."""
    return [
        {
            "timestamp": "2024-10-25T12:00:00Z",
            "station_id": "GON001", "station_name": "Gopalpur",
            "latitude": 19.27, "longitude": 84.90,
            "pressure_hpa": 984.1, "wind_speed_kmh": 118.0,
            "wind_direction_deg": 210.0, "humidity_pct": 98.0,
            "rainfall_mm": 98.4, "sea_surface_temp_c": 30.7,
            "visibility_km": 1.6, "wave_height_m": 6.4,
            "data_source": "sample"
        },
        {
            "timestamp": "2024-10-25T12:00:00Z",
            "station_id": "PRI001", "station_name": "Puri",
            "latitude": 19.80, "longitude": 85.83,
            "pressure_hpa": 986.2, "wind_speed_kmh": 108.0,
            "wind_direction_deg": 205.0, "humidity_pct": 96.0,
            "rainfall_mm": 85.2, "sea_surface_temp_c": 30.4,
            "visibility_km": 2.1, "wave_height_m": 5.8,
            "data_source": "sample"
        },
    ]
