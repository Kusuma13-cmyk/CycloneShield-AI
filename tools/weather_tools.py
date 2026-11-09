"""
CycloneShield AI — Weather Data Tools
Loads weather data from CSV files or live APIs.

Live weather sources (in priority order):
1. Open-Meteo API (free, no API key, real meteorological data)
2. OpenWeatherMap API (requires OPENWEATHER_API_KEY)
3. Sample CSV (bundled data — clearly labelled as sample)

Data source labels:
  "live_open_meteo"      — real-time from Open-Meteo (free)
  "live_openweathermap"  — real-time from OpenWeatherMap (requires key)
  "sample"               — bundled CSV, illustrative only
  "hardcoded_fallback"   — last-resort minimal data
"""
import csv
import os
import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from utils.logging_config import get_logger, log_agent_event

logger = get_logger("tools.weather")

SAMPLE_CSV = Path(__file__).parent.parent / "data" / "sample_weather.csv"

# Bay of Bengal coastal monitoring stations (lat, lon)
BOB_STATIONS = [
    ("Chennai",        13.08, 80.27),
    ("Visakhapatnam",  17.68, 83.22),
    ("Bhubaneswar",    20.29, 85.82),
    ("Puri",           19.80, 85.83),
    ("Gopalpur",       19.27, 84.90),
    ("Kolkata",        22.57, 88.36),
    ("Port Blair",     11.67, 92.73),
    ("Paradip",        20.32, 86.61),
]

# Open-Meteo API — free, no auth, real WMO weather data
OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_PARAMS = (
    "temperature_2m,surface_pressure,wind_speed_10m,wind_direction_10m,"
    "relative_humidity_2m,precipitation,visibility"
)


def load_sample_weather_data() -> list[dict]:
    """Load sample weather data from the bundled CSV file.

    Returns data labelled data_source='sample' — not live observations.
    """
    readings = []
    try:
        with open(SAMPLE_CSV, "r", newline="", encoding="utf-8") as f:
            lines = [row for row in f if not row.startswith("#") and row.strip()]
            reader = csv.DictReader(lines)
            for row in reader:
                _coerce_numeric(row)
                if "data_source" not in row or not row["data_source"]:
                    row["data_source"] = "sample"
                readings.append(row)
        log_agent_event(
            "WeatherTools", "tool_call",
            input_summary=f"Loaded {len(readings)} sample readings from CSV",
            output_summary="ok", status="ok",
        )
    except FileNotFoundError:
        logger.error("Sample weather CSV not found: %s", SAMPLE_CSV)
        readings = _get_hardcoded_fallback()
    except Exception as e:
        logger.error("Error reading weather CSV: %s", e)
        readings = _get_hardcoded_fallback()
    return readings


def load_live_weather_data(location: str = "Bay of Bengal") -> list[dict]:
    """
    Attempt to load LIVE weather data from real meteorological APIs.

    Tries Open-Meteo first (free, no key required), then OpenWeatherMap
    (if OPENWEATHER_API_KEY is configured).

    Returns a list of standardised reading dicts, or [] on total failure.
    Readings include 'data_source', 'fetch_timestamp', and 'data_freshness_note'.
    """
    readings = []

    # --- Attempt 1: Open-Meteo (free, no API key) ---
    open_meteo_readings = _load_open_meteo()
    if open_meteo_readings:
        readings.extend(open_meteo_readings)
        log_agent_event(
            "WeatherTools", "tool_call",
            input_summary=f"Open-Meteo: loaded {len(open_meteo_readings)} real station readings",
            output_summary="live", status="ok",
        )
        return readings

    # --- Attempt 2: OpenWeatherMap (requires API key) ---
    owm_readings = _load_openweathermap()
    if owm_readings:
        readings.extend(owm_readings)
        log_agent_event(
            "WeatherTools", "tool_call",
            input_summary=f"OpenWeatherMap: loaded {len(owm_readings)} readings",
            output_summary="live", status="ok",
        )
        return readings

    # Both live sources failed
    logger.warning("All live weather sources failed — caller should fall back to sample")
    log_agent_event(
        "WeatherTools", "tool_call",
        input_summary="Live weather: all sources failed",
        output_summary="empty", status="error",
    )
    return []


def _load_open_meteo() -> list[dict]:
    """
    Fetch current weather from Open-Meteo API for Bay of Bengal stations.
    Free API, no authentication required.
    Returns standardised reading list, or [] on failure.
    """
    readings = []
    fetch_ts = datetime.now(timezone.utc).isoformat()

    for city, lat, lon in BOB_STATIONS:
        try:
            url = OPEN_METEO_BASE
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": OPEN_METEO_PARAMS,
                "wind_speed_unit": "kmh",
                "timeformat": "unixtime",
            }
            resp = requests.get(url, params=params, timeout=12)
            if resp.status_code != 200:
                logger.warning("Open-Meteo HTTP %d for %s", resp.status_code, city)
                continue

            data = resp.json()
            current = data.get("current", {})

            # Pressure: Open-Meteo reports surface pressure in hPa
            pressure = current.get("surface_pressure")
            wind_spd = current.get("wind_speed_10m")
            wind_dir = current.get("wind_direction_10m")
            humidity = current.get("relative_humidity_2m")
            rainfall = current.get("precipitation", 0) or 0
            visibility_m = current.get("visibility")  # metres
            visibility_km = round(visibility_m / 1000, 1) if visibility_m else None
            # temperature_2m is included in OPEN_METEO_PARAMS
            temperature = current.get("temperature_2m")

            # Timestamp from API (unix) or fetch time
            obs_unix = current.get("time")
            obs_ts = (
                datetime.fromtimestamp(obs_unix, tz=timezone.utc).isoformat()
                if obs_unix else fetch_ts
            )

            reading = {
                "timestamp": obs_ts,
                "fetch_timestamp": fetch_ts,
                "station_id": f"OM_{city[:4].upper()}",
                "station_name": city,
                "latitude": lat,
                "longitude": lon,
                "pressure_hpa": float(pressure) if pressure is not None else None,
                "wind_speed_kmh": float(wind_spd) if wind_spd is not None else None,
                "wind_direction_deg": float(wind_dir) if wind_dir is not None else None,
                "humidity_pct": float(humidity) if humidity is not None else None,
                "rainfall_mm": float(rainfall),
                "temperature_c": float(temperature) if temperature is not None else None,
                "sea_surface_temp_c": None,  # not available from this Open-Meteo endpoint
                "visibility_km": visibility_km,
                "wave_height_m": None,
                "data_source": "live_open_meteo",
                "data_freshness_note": f"Real-time observation from Open-Meteo API at {fetch_ts[:16]} UTC",
                "attribution": "Weather data by Open-Meteo.com (CC BY 4.0)",
            }
            readings.append(reading)

        except requests.exceptions.Timeout:
            logger.warning("Open-Meteo timeout for %s", city)
        except requests.exceptions.ConnectionError:
            logger.warning("Open-Meteo connection error for %s", city)
        except Exception as e:
            logger.warning("Open-Meteo error for %s: %s", city, e)

    return readings


def _load_openweathermap() -> list[dict]:
    """
    Fetch weather from OpenWeatherMap if OPENWEATHER_API_KEY is configured.
    Returns standardised reading list or [].
    """
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not api_key or api_key in ("", "your_openweather_api_key_here"):
        logger.info("OPENWEATHER_API_KEY not configured — skipping OWM")
        return []

    readings = []
    fetch_ts = datetime.now(timezone.utc).isoformat()

    for city, lat, lon in BOB_STATIONS:
        try:
            url = (
                f"https://api.openweathermap.org/data/2.5/weather"
                f"?lat={lat}&lon={lon}&appid={api_key}&units=metric"
            )
            resp = requests.get(url, timeout=10)
            if resp.status_code == 401:
                logger.error("OpenWeatherMap: invalid API key")
                return []
            if resp.status_code != 200:
                logger.warning("OWM HTTP %d for %s", resp.status_code, city)
                continue

            data = resp.json()
            reading = {
                "timestamp": fetch_ts,
                "fetch_timestamp": fetch_ts,
                "station_id": f"OWM_{city[:3].upper()}",
                "station_name": city,
                "latitude": lat,
                "longitude": lon,
                "pressure_hpa": data.get("main", {}).get("pressure"),
                "wind_speed_kmh": round((data.get("wind", {}).get("speed", 0) or 0) * 3.6, 1),
                "wind_direction_deg": data.get("wind", {}).get("deg"),
                "humidity_pct": data.get("main", {}).get("humidity"),
                "rainfall_mm": data.get("rain", {}).get("1h", 0) or 0,
                "sea_surface_temp_c": None,
                "visibility_km": round((data.get("visibility", 10000) or 10000) / 1000, 1),
                "wave_height_m": None,
                "data_source": "live_openweathermap",
                "data_freshness_note": f"Real observation from OpenWeatherMap at {fetch_ts[:16]} UTC",
            }
            readings.append(reading)
        except Exception as e:
            logger.warning("OWM request failed for %s: %s", city, e)

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
            "data_source": r.get("data_source", "unknown"),
        })
    return {
        "total": len(readings),
        "valid": sum(1 for r in results if r["valid"]),
        "results": results,
    }


def get_data_source_label(readings: list[dict]) -> str:
    """
    Return a human-readable label describing the data source.
    Used for display in the dashboard.
    """
    if not readings:
        return "no data"
    sources = {r.get("data_source", "unknown") for r in readings}
    if "live_open_meteo" in sources:
        return "live (Open-Meteo)"
    if "live_openweathermap" in sources:
        return "live (OpenWeatherMap)"
    if "sample" in sources:
        return "sample (CSV — not live observations)"
    if "hardcoded_fallback" in sources:
        return "hardcoded fallback (very limited data)"
    return "unknown"


def _coerce_numeric(row: dict) -> None:
    """Convert string CSV fields to float in-place."""
    numeric_fields = [
        "latitude", "longitude", "pressure_hpa", "wind_speed_kmh",
        "wind_direction_deg", "humidity_pct", "rainfall_mm",
        "sea_surface_temp_c", "visibility_km", "wave_height_m",
    ]
    for field in numeric_fields:
        if field in row and row[field]:
            try:
                row[field] = float(row[field])
            except (ValueError, TypeError):
                row[field] = None


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
            "data_source": "hardcoded_fallback",
            "data_freshness_note": "Static fallback data — not a real observation",
        },
        {
            "timestamp": "2024-10-25T12:00:00Z",
            "station_id": "PRI001", "station_name": "Puri",
            "latitude": 19.80, "longitude": 85.83,
            "pressure_hpa": 986.2, "wind_speed_kmh": 108.0,
            "wind_direction_deg": 205.0, "humidity_pct": 96.0,
            "rainfall_mm": 85.2, "sea_surface_temp_c": 30.4,
            "visibility_km": 2.1, "wave_height_m": 5.8,
            "data_source": "hardcoded_fallback",
            "data_freshness_note": "Static fallback data — not a real observation",
        },
    ]
