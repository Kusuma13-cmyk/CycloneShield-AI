"""
CycloneShield AI — Main Streamlit Application
Agentic AI-based Cyclone Detection & Early Warning System for coastal India

IMPORTANT — correct launch command (must use .venv Python 3.13):
  Windows CMD:        run.bat
  PowerShell:         .\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8503
  Cross-platform:     .venv/bin/python -m streamlit run app.py --server.port 8503

ibm-watsonx-ai requires Python <3.15. If you see the SDK error, you are using the
wrong Python interpreter. Python 3.15 cannot install ibm-watsonx-ai.
"""
import os
import sys
import json
import time
import pandas as pd
import streamlit as st
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# ── Path setup — ensure project root is importable ──────────────────────────
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv()

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="CycloneShield AI",
    page_icon="🌀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Early SDK environment diagnostic ─────────────────────────────────────────
# Run BEFORE any provider import so the user sees the fix immediately.
def _check_sdk_environment() -> dict:
    """
    Check whether ibm-watsonx-ai is importable in this interpreter.
    Returns a dict with keys: sdk_ok, sdk_version, python_version, interpreter_path, fix_cmd.
    """
    py_ver = sys.version.split()[0]
    interp = sys.executable
    try:
        import ibm_watsonx_ai as _ibm
        return {
            "sdk_ok": True,
            "sdk_version": _ibm.__version__,
            "python_version": py_ver,
            "interpreter_path": interp,
            "fix_cmd": None,
        }
    except ImportError:
        # Determine fix command based on Python version
        py_tuple = tuple(int(x) for x in py_ver.split(".")[:2])
        if py_tuple >= (3, 15):
            reason = (
                f"Python {py_ver} detected — ibm-watsonx-ai requires Python <3.15. "
                "You are using the system Python, not the project .venv (Python 3.13)."
            )
            fix = (
                "Use the .venv interpreter:\n"
                "  PowerShell:  .venv\\Scripts\\python.exe -m streamlit run app.py --server.port 8503\n"
                "  CMD:         run.bat\n"
                "  Or activate: .venv\\Scripts\\activate  then  streamlit run app.py --server.port 8503"
            )
        else:
            reason = f"ibm-watsonx-ai not installed in this interpreter ({interp})"
            fix = "pip install ibm-watsonx-ai>=1.9.1"
        return {
            "sdk_ok": False,
            "sdk_version": None,
            "python_version": py_ver,
            "interpreter_path": interp,
            "fix_cmd": fix,
            "reason": reason,
        }

_SDK_ENV = _check_sdk_environment()

# ── Imports after path setup ──────────────────────────────────────────────────
from orchestration.coordinator import (
    run_full_analysis, submit_human_review, AnalysisSession
)
from tools.weather_tools import load_sample_weather_data
from tools.cyclone_tools import load_sample_track_data
from utils.logging_config import get_execution_log
from dashboard.components import (
    metric_card, risk_badge, alert_banner,
    build_cyclone_track_map, pressure_chart, wind_speed_chart,
    cyclone_intensity_chart, agent_timeline_chart, render_json_card,
    RISK_COLORS, ALERT_COLORS,
)

try:
    from streamlit_folium import folium_static
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Dark navy theme */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0D1B2A 0%, #112240 100%);
    color: #E8F4F8;
}
[data-testid="stSidebar"] {
    background: #0A1628 !important;
    border-right: 1px solid #1E3A5F;
}
[data-testid="stSidebar"] * { color: #B8D4E8 !important; }
.stButton > button {
    background: #1565C0;
    color: white;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    padding: 8px 20px;
}
.stButton > button:hover { background: #1976D2; }
div[data-testid="metric-container"] {
    background: #1E2A3A;
    border: 1px solid #2A4A6A;
    border-radius: 8px;
    padding: 12px;
}
.main-title {
    font-size: 2.2em;
    font-weight: 800;
    color: #64B5F6;
    margin: 0;
}
.subtitle { color: #90A4AE; font-size: 1em; margin-top: 4px; }
.section-header {
    font-size: 1.3em;
    font-weight: 700;
    color: #64B5F6;
    border-bottom: 2px solid #1565C0;
    padding-bottom: 6px;
    margin: 20px 0 12px;
}
.agent-card {
    background: #1E2A3A;
    border: 1px solid #2A4A6A;
    border-radius: 8px;
    padding: 14px;
    margin: 8px 0;
}
.demo-banner {
    background: #1A237E22;
    border: 1px solid #3F51B5;
    border-radius: 6px;
    padding: 10px 16px;
    font-size: 0.85em;
    color: #9FA8DA;
    margin: 8px 0;
}
.status-ok { color: #00C853; font-weight: 700; }
.status-error { color: #FF5252; font-weight: 700; }
.status-pending { color: #FFC400; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ── Session state initialization ──────────────────────────────────────────────
def init_session():
    defaults = {
        "analysis_session": None,
        "running": False,
        "nav_page": "Overview",
        "provider_override": "",
        "use_live_weather": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ── Sidebar Navigation ────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🌀 CycloneShield AI")
        st.markdown("*Agentic Early Warning System*")
        st.divider()

        pages = [
            ("📊", "Overview"),
            ("🌦️", "Weather Intelligence"),
            ("🌀", "Cyclone Detection"),
            ("🗺️", "Cyclone Tracking"),
            ("⚠️", "Impact Assessment"),
            ("🚨", "Early Warning"),
            ("🤖", "Multi-Agent Activity"),
            ("✅", "Human Verification"),
            ("📈", "Model Evaluation"),
            ("⚙️", "Settings"),
        ]

        for icon, name in pages:
            active = st.session_state.nav_page == name
            if st.button(
                f"{icon} {name}",
                key=f"nav_{name}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state.nav_page = name

        st.divider()

        # Quick run button in sidebar
        st.markdown("### Quick Run")
        provider = st.selectbox(
            "LLM Provider",
            ["auto", "demo", "granite"],
            key="sidebar_provider",
            help=(
                "auto = use IBM Granite if credentials configured, else demo\n"
                "demo = pre-written demo responses (no IBM API calls)\n"
                "granite = force IBM Granite (ibm/granite-4-h-small); shows error if no credentials"
            ),
        )
        live_wx = st.toggle(
            "Use live weather (Open-Meteo)",
            value=st.session_state.get("use_live_weather", True),
            key="sidebar_live_weather",
            help="On = fetch real current weather from Open-Meteo (free API, no key needed). Off = use sample CSV.",
        )
        st.session_state.use_live_weather = live_wx

        if st.button("🚀 Run Analysis", use_container_width=True, type="primary"):
            st.session_state.provider_override = "" if provider == "auto" else provider
            st.session_state.running = True
            st.rerun()

        # Status indicator
        st.divider()
        session: AnalysisSession = st.session_state.analysis_session
        if session:
            status_color = {
                "complete": "🟢", "awaiting_review": "🟡",
                "error": "🔴", "running": "🔵", "idle": "⚪",
            }.get(session.status, "⚪")
            st.markdown(f"**Status:** {status_color} {session.status.replace('_', ' ').title()}")
            st.markdown(f"**Provider:** {session.provider_name}")
            st.markdown(f"**Session:** `{session.session_id}`")
        else:
            st.markdown("**Status:** ⚪ Not started")

        st.divider()
        # Show ACTUAL operating mode — read from active session, not just env var
        from providers.factory import get_provider_mode
        mode_info = get_provider_mode()
        if session and session.ai_mode == "live":
            st.markdown("**AI Mode:** 🟢 **LIVE** (IBM Granite)")
            st.markdown(f"**Model:** `{session.model_name}`")
        elif session and session.ai_mode == "demo":
            st.markdown("**AI Mode:** 🔵 **DEMO** (sample data)")
        elif mode_info["mode"] == "live":
            st.markdown("**AI Mode:** 🟢 **LIVE** (IBM Granite)")
            st.markdown(f"**Model:** `{mode_info['model_name']}`")
        elif mode_info["mode"] == "misconfigured":
            st.markdown("**AI Mode:** 🔴 **CONFIG ERROR**")
            st.caption(mode_info.get("reason", ""))
        else:
            st.markdown("**AI Mode:** 🔵 **DEMO** (no credentials)")
            st.caption(mode_info.get("reason", ""))
        if session:
            st.markdown(f"**Data:** {session.data_source_label}")

        # SDK / interpreter health indicator
        if not _SDK_ENV["sdk_ok"]:
            st.divider()
            st.error(
                f"⚠️ **SDK Missing**\n\n"
                f"Python {_SDK_ENV['python_version']} — "
                f"ibm-watsonx-ai not available.\n\n"
                f"**Fix:** Use `.venv` interpreter.\n"
                f"See Settings → SDK Diagnostic."
            )
        st.caption("CycloneShield AI v1.0")


# ── Run analysis trigger ──────────────────────────────────────────────────────
def maybe_run_analysis():
    if not st.session_state.running:
        return

    st.session_state.running = False
    progress_bar = st.progress(0, text="Initializing CycloneShield AI pipeline...")
    status_area = st.empty()

    def update_progress(msg: str, pct: float):
        pct_int = max(0, min(100, int(pct * 100)))
        progress_bar.progress(pct_int, text=msg)
        status_area.info(msg)

    try:
        session = run_full_analysis(
            location="Odisha and Andhra Pradesh coast, Bay of Bengal",
            provider_override=st.session_state.provider_override,
            data_mode="auto",
            use_live_weather=st.session_state.use_live_weather,
            progress_callback=update_progress,
        )
        st.session_state.analysis_session = session
        progress_bar.progress(100, text="Analysis complete!")
        time.sleep(0.5)
        status_area.success(
            f"✅ Analysis complete in {session.total_duration_ms:.0f} ms | "
            f"Provider: {session.provider_name}"
        )
    except Exception as e:
        status_area.error(f"Pipeline error: {e}")
        progress_bar.empty()


# ── Page renderers ─────────────────────────────────────────────────────────────

def page_overview():
    st.markdown('<div class="main-title">🌀 CycloneShield AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Agentic AI-based Cyclone Detection & Early Warning System — Coastal India</div>', unsafe_allow_html=True)
    st.markdown("")

    session: AnalysisSession = st.session_state.analysis_session

    if not session:
        # Welcome state
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info(
                "👋 **Welcome to CycloneShield AI**\n\n"
                "This system uses three specialized AI agents to monitor weather patterns, "
                "detect cyclone threats, and generate impact assessments for coastal India.\n\n"
                "**Click '🚀 Run Analysis' in the sidebar to start.**"
            )
            st.markdown("")
            if st.button("🚀 Run Full Analysis Now", type="primary", use_container_width=True):
                st.session_state.running = True
                st.rerun()
        _render_system_overview()
        return

    # Session is available
    impact_out = session.impact_result.get("output", {})
    cyclone_out = session.cyclone_result.get("output", {})
    weather_out = session.weather_result.get("output", {})

    risk = impact_out.get("overall_risk_level", "?")
    alert = impact_out.get("recommended_alert_level", "?")
    intensity = cyclone_out.get("current_intensity", "?")
    wind = cyclone_out.get("wind_speed_kmh", "?")
    pressure_val = cyclone_out.get("pressure_hpa", "?")
    recommendation = weather_out.get("recommendation", "?")

    # Alert banner
    if alert in ("RED", "ORANGE"):
        alert_banner(alert, f"{risk} risk — {cyclone_out.get('storm_name', 'Cyclone')} | {intensity}")
    
    # Mode banner — always show clearly
    if session.ai_mode == "live":
        st.markdown(
            f'<div style="background:#00332211;border:1px solid #00C853;border-radius:6px;'
            f'padding:10px 16px;font-size:0.85em;color:#A5D6A7;margin:8px 0;">'
            f'🟢 <strong>LIVE AI MODE</strong> — IBM Granite ({session.model_name}) | '
            f'Weather: {session.data_source_label}</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="demo-banner">🔵 <strong>DEMO MODE</strong> — '
            'All results are based on sample/pre-written data. Not real AI responses. '
            'Configure IBM credentials in .env to enable Live AI (ibm/granite-4-h-small).</div>',
            unsafe_allow_html=True
        )

    # Metric row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(metric_card("Risk Level", risk, color=RISK_COLORS.get(risk, "#607D8B"), icon="⚡"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Alert Level", alert, color=ALERT_COLORS.get(alert, "#607D8B"), icon="🚨"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card("Wind Speed", f"{wind} km/h" if wind != "?" else "?", color="#FF6D00", icon="💨"), unsafe_allow_html=True)
    with col4:
        st.markdown(metric_card("Pressure", f"{pressure_val} hPa" if pressure_val != "?" else "?", color="#00B0FF", icon="🌡️"), unsafe_allow_html=True)
    with col5:
        st.markdown(metric_card("Intensity", intensity.split()[-1] if intensity != "?" else "?", color="#9C27B0", icon="🌀"), unsafe_allow_html=True)

    st.markdown("")

    # Pipeline status
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown('<div class="section-header">Agent Pipeline Status</div>', unsafe_allow_html=True)
        agents_info = [
            ("🌦️ Weather Intelligence", session.weather_result.get("status", "?"),
             session.weather_result.get("duration_ms", 0), recommendation),
            ("🌀 Cyclone Detection", session.cyclone_result.get("status", "?"),
             session.cyclone_result.get("duration_ms", 0), intensity),
            ("⚠️ Impact Assessment", session.impact_result.get("status", "?"),
             session.impact_result.get("duration_ms", 0), risk),
            ("✅ Human Review", session.human_review_status, 0, session.human_reviewer or "Pending"),
        ]
        for name, status, dur, detail in agents_info:
            status_class = "status-ok" if status in ("ok", "approved") else \
                           "status-error" if status == "error" else "status-pending"
            st.markdown(
                f'<div class="agent-card">'
                f'<strong>{name}</strong> &nbsp; '
                f'<span class="{status_class}">{status.upper()}</span>'
                f'<span style="color:#7A9BB5;float:right;">{dur:.0f} ms | {detail}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    with col2:
        st.markdown('<div class="section-header">Analysis Info</div>', unsafe_allow_html=True)
        st.markdown(f"**Session:** `{session.session_id}`")
        ai_badge = "🟢 LIVE" if session.ai_mode == "live" else "🔵 DEMO"
        st.markdown(f"**AI Mode:** {ai_badge}")
        st.markdown(f"**Model:** `{session.model_name}`")
        st.markdown(f"**Data Source:** {session.data_source_label}")
        st.markdown(f"**Total Time:** {session.total_duration_ms:.0f} ms")
        st.markdown(f"**Errors:** {len(session.errors)}")
        if session.errors:
            for err in session.errors:
                st.warning(err)


def page_weather_intelligence():
    st.markdown('<div class="section-header">🌦️ Weather Intelligence</div>', unsafe_allow_html=True)

    session: AnalysisSession = st.session_state.analysis_session
    if not session:
        st.info("Run the analysis first (click '🚀 Run Analysis' in the sidebar).")
        return

    weather_out = session.weather_result.get("output", {})
    if not weather_out:
        st.warning("Weather agent produced no output.")
        return

    # Mode/data source banner
    if session.ai_mode == "demo":
        st.markdown('<div class="demo-banner">🔵 DEMO MODE — Pre-written responses, not real AI or real weather data</div>', unsafe_allow_html=True)
    else:
        src = session.data_source_label
        st.markdown(
            f'<div style="background:#00332211;border:1px solid #00C853;border-radius:6px;'
            f'padding:8px 14px;font-size:0.85em;color:#A5D6A7;margin:6px 0;">'
            f'🟢 LIVE AI — IBM Granite ({session.model_name}) | Weather data: {src}</div>',
            unsafe_allow_html=True
        )

    col1, col2, col3 = st.columns(3)
    stats = weather_out.get("_stats", {})
    with col1:
        st.metric("Min Pressure", f"{stats.get('pressure_min_hpa', '?')} hPa")
        st.metric("Max Wind", f"{stats.get('wind_max_kmh', '?')} km/h")
    with col2:
        st.metric("Avg Humidity", f"{stats.get('humidity_avg_pct', '?')}%")
        st.metric("Total Rainfall", f"{stats.get('rainfall_total_mm', '?')} mm")
    with col3:
        st.metric("Stations", stats.get("station_count", "?"))
        quality = weather_out.get("data_quality", "?")
        st.metric("Data Quality", quality.upper())

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Analysis Summary**")
        st.write(weather_out.get("analysis_summary", "No summary available."))
        st.markdown("**Pressure Trend**")
        st.write(weather_out.get("pressure_trend", "?"))
        st.markdown("**Wind Assessment**")
        st.write(weather_out.get("wind_assessment", "?"))

    with col2:
        st.markdown("**Anomalies Detected**")
        anomalies = weather_out.get("anomalies_detected", [])
        if anomalies:
            for a in anomalies:
                st.warning(f"⚠️ {a}")
        else:
            st.success("No anomalies detected")

        st.markdown("**Recommendation**")
        rec = weather_out.get("recommendation", "?")
        if "Escalate" in rec:
            st.error(f"🔴 {rec}")
        elif rec == "Monitor":
            st.warning(f"🟡 {rec}")
        else:
            st.success(f"🟢 {rec}")

        conf = weather_out.get("confidence", 0)
        st.markdown(f"**Confidence:** {conf:.0%}")

    # Charts — use live data from session if available, otherwise sample
    try:
        _weather_cache = weather_out.get("_raw_readings") or []
        if _weather_cache:
            weather_data_for_chart = _weather_cache
            chart_src = session.data_source_label
        else:
            weather_data_for_chart = load_sample_weather_data()
            chart_src = "sample CSV"
        df = pd.DataFrame(weather_data_for_chart)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        # Coerce numeric fields
        for col_name in ["pressure_hpa", "wind_speed_kmh", "humidity_pct"]:
            if col_name in df.columns:
                df[col_name] = pd.to_numeric(df[col_name], errors="coerce")
        df = df.dropna(subset=["pressure_hpa", "wind_speed_kmh"])
        if not df.empty:
            st.caption(f"Chart data source: {chart_src} | {len(df)} readings")
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(pressure_chart(df), use_container_width=True)
            with col2:
                st.plotly_chart(wind_speed_chart(df), use_container_width=True)
        else:
            st.info("No numeric weather data available for charting.")
    except Exception as e:
        st.info(f"Chart error: {e}")

    render_json_card("Raw Weather Agent JSON Output", weather_out)


def page_cyclone_detection():
    st.markdown('<div class="section-header">🌀 Cyclone Detection</div>', unsafe_allow_html=True)

    session: AnalysisSession = st.session_state.analysis_session
    if not session:
        st.info("Run the analysis first.")
        return

    cyclone_out = session.cyclone_result.get("output", {})
    if not cyclone_out:
        st.warning("Cyclone agent produced no output.")
        return

    if session.ai_mode == "demo":
        st.markdown('<div class="demo-banner">🔵 DEMO MODE — Pre-written cyclone analysis, not real detection</div>', unsafe_allow_html=True)
    else:
        ai_by = cyclone_out.get("ai_assessed_by", f"IBM Granite ({session.model_name})")
        st.markdown(
            f'<div style="background:#00332211;border:1px solid #00C853;border-radius:6px;'
            f'padding:8px 14px;font-size:0.85em;color:#A5D6A7;margin:6px 0;">'
            f'🟢 LIVE AI — AI assessed by {ai_by} | Track data: sample CSV (no live cyclone API)</div>',
            unsafe_allow_html=True
        )

    detected = cyclone_out.get("cyclone_detected", False)

    if detected:
        st.error(f"🚨 **CYCLONE DETECTED: {cyclone_out.get('storm_name', 'Unknown')}**")
    else:
        st.success("✅ No active cyclone detected in available data.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Intensity", cyclone_out.get("current_intensity", "?"))
    with col2:
        st.metric("Wind Speed", f"{cyclone_out.get('wind_speed_kmh', '?')} km/h")
    with col3:
        st.metric("Pressure", f"{cyclone_out.get('pressure_hpa', '?')} hPa")
    with col4:
        cat = cyclone_out.get("saffir_simpson_category")
        st.metric("Saffir-Simpson", f"Category {cat}" if cat else "Below Cat 1")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Detection Summary**")
        st.write(cyclone_out.get("analysis_summary", "?"))
        pos = cyclone_out.get("current_position", {})
        if pos.get("latitude"):
            st.markdown(f"**Position:** {pos.get('latitude')}°N, {pos.get('longitude')}°E")
        st.markdown(f"**Movement:** {cyclone_out.get('movement_direction', '?')} at {cyclone_out.get('movement_speed_kmh', '?')} km/h")
        st.markdown(f"**Intensity Trend:** {cyclone_out.get('intensity_trend', '?')}")

    with col2:
        st.markdown("**Landfall Assessment**")
        lp = cyclone_out.get("landfall_probability", "?")
        lr = cyclone_out.get("landfall_region", "?")
        lt = cyclone_out.get("landfall_time_est", "?")
        lp_color = {"High": "error", "Moderate": "warning", "Low": "success"}.get(lp, "info")
        getattr(st, lp_color)(f"Probability: **{lp}**")
        st.markdown(f"**Region:** {lr}")
        st.markdown(f"**Est. Time:** {lt}")
        st.markdown(f"**Confidence:** {cyclone_out.get('confidence', 0):.0%}")
        st.caption(f"⚠️ Uncertainty: {cyclone_out.get('uncertainty', 'Not specified')}")

    render_json_card("Raw Cyclone Agent JSON Output", cyclone_out)


def page_cyclone_tracking():
    st.markdown('<div class="section-header">🗺️ Cyclone Track Map</div>', unsafe_allow_html=True)

    session: AnalysisSession = st.session_state.analysis_session

    if session and session.ai_mode == "demo":
        st.markdown('<div class="demo-banner">🔵 DEMO MODE — Sample cyclone track, not real-time data</div>', unsafe_allow_html=True)
    elif session:
        st.info("ℹ️ Track data: sample CSV (Cyclone AGNI illustrative). No live cyclone track API is integrated. AI analysis is real (IBM Granite).")

    track_data = load_sample_track_data()

    if not track_data:
        st.warning("No track data available.")
        return

    # Track info
    latest = track_data[-1]
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Storm", latest.get("storm_name", "?"))
    with col2:
        st.metric("Latest Intensity", latest.get("intensity_category", "?").split()[-1])
    with col3:
        st.metric("Wind", f"{latest.get('wind_speed_kmh', '?')} km/h")
    with col4:
        st.metric("Track Points", len(track_data))

    st.markdown("---")

    # Map
    fmap = build_cyclone_track_map(track_data)
    if FOLIUM_AVAILABLE:
        folium_static(fmap, width=1100, height=500)
    else:
        st.info("Map display requires streamlit-folium. Install with: pip install streamlit-folium")
        # Fallback: Plotly scatter map (Plotly 6+ uses scatter_map with map_style)
        track_df = pd.DataFrame(track_data)
        track_df = track_df.dropna(subset=["latitude", "longitude"])
        import plotly.express as _px
        fig = _px.scatter_map(
            track_df, lat="latitude", lon="longitude",
            color="intensity_category",
            hover_name="storm_name",
            hover_data=["wind_speed_kmh", "pressure_hpa", "timestamp"],
            map_style="carto-darkmatter",
            zoom=4, height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Intensity chart
    track_df = pd.DataFrame(track_data)
    track_df = track_df.dropna(subset=["wind_speed_kmh", "pressure_hpa"])
    if not track_df.empty:
        st.plotly_chart(cyclone_intensity_chart(track_df), use_container_width=True)

    # Track table
    with st.expander("📋 Track Data Table", expanded=False):
        display_cols = ["timestamp", "latitude", "longitude",
                        "intensity_category", "wind_speed_kmh", "pressure_hpa", "status"]
        display_df = track_df[[c for c in display_cols if c in track_df.columns]]
        st.dataframe(display_df, use_container_width=True)

    st.error(
        "⚠️ **SAMPLE DATA** — 'Cyclone AGNI' is a fictional illustrative cyclone "
        "based on historical Bay of Bengal patterns. It is NOT a real current cyclone. "
        "For official real-time cyclone information: "
        "[IMD](https://mausam.imd.gov.in) · "
        "[INCOIS](https://incois.gov.in) · "
        "Call IMD: **1800-180-1717**"
    )
    st.caption(f"Source: {latest.get('source', 'IMD-Sample')} | Track timestamps are historical, not current | No live cyclone track API integrated")


def page_impact_assessment():
    st.markdown('<div class="section-header">⚠️ Impact Assessment</div>', unsafe_allow_html=True)

    session: AnalysisSession = st.session_state.analysis_session
    if not session:
        st.info("Run the analysis first.")
        return

    impact_out = session.impact_result.get("output", {})
    if not impact_out:
        st.warning("Impact agent produced no output.")
        return

    if session.ai_mode == "demo":
        st.markdown('<div class="demo-banner">🔵 DEMO MODE — Pre-written impact assessment, not real AI analysis</div>', unsafe_allow_html=True)
    else:
        ai_by = impact_out.get("ai_assessed_by", f"IBM Granite ({session.model_name})")
        st.markdown(
            f'<div style="background:#00332211;border:1px solid #00C853;border-radius:6px;'
            f'padding:8px 14px;font-size:0.85em;color:#A5D6A7;margin:6px 0;">'
            f'🟢 LIVE AI — Impact assessed by {ai_by}</div>',
            unsafe_allow_html=True
        )

    risk = impact_out.get("overall_risk_level", "?")
    alert = impact_out.get("recommended_alert_level", "?")
    risk_color = RISK_COLORS.get(risk, "#607D8B")
    alert_color = ALERT_COLORS.get(alert, "#607D8B")

    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(
            f'<div style="background:{risk_color}33;border:3px solid {risk_color};'
            f'border-radius:12px;padding:20px;text-align:center;">'
            f'<div style="font-size:0.9em;color:#aaa;">OVERALL RISK</div>'
            f'<div style="font-size:2.5em;font-weight:900;color:{risk_color};">{risk}</div>'
            f'<div style="background:{alert_color};color:#fff;border-radius:6px;'
            f'padding:4px 12px;margin-top:10px;font-weight:700;">{alert} ALERT</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    with col2:
        st.markdown("**Risk Justification**")
        st.write(impact_out.get("risk_justification", "?"))
        st.markdown("**Summary**")
        st.write(impact_out.get("analysis_summary", "?"))

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Affected Districts**")
        districts = impact_out.get("affected_districts", [])
        if districts:
            df_dist = pd.DataFrame(districts)
            st.dataframe(df_dist, use_container_width=True, hide_index=True)

        st.markdown("**Hazard Estimates**")
        st.info(f"🌊 Storm Surge: {impact_out.get('storm_surge_estimate_m', '?')}")
        st.info(f"🌧️ Rainfall: {impact_out.get('rainfall_forecast_mm', '?')}")
        st.info(f"💨 Wind Damage: {impact_out.get('wind_damage_potential', '?')}")

    with col2:
        st.markdown("**Preparedness Actions**")
        actions = impact_out.get("preparedness_actions", [])
        for i, action in enumerate(actions, 1):
            st.markdown(f"{i}. {action}")

        st.markdown("**Vulnerable Groups**")
        groups = impact_out.get("vulnerable_groups", [])
        if groups:
            st.markdown(", ".join(groups))

    st.markdown("---")

    # Official warning note — always displayed prominently
    st.error(impact_out.get("official_warning_note", ""))
    st.info(f"📞 {impact_out.get('imd_contact', 'Call IMD: 1800-180-1717')}")

    render_json_card("Raw Impact Agent JSON Output", impact_out)


def page_early_warning():
    st.markdown('<div class="section-header">🚨 Early Warning</div>', unsafe_allow_html=True)

    session: AnalysisSession = st.session_state.analysis_session
    if not session:
        st.info("Run the analysis first.")
        return

    impact_out = session.impact_result.get("output", {})
    cyclone_out = session.cyclone_result.get("output", {})

    alert = impact_out.get("recommended_alert_level", "GREEN")
    risk = impact_out.get("overall_risk_level", "MINIMAL")
    review_status = session.human_review_status

    # Review gate — prominent banner
    if review_status == "pending":
        st.warning(
            "⏳ **Awaiting Human Review** — This warning has NOT been verified by a human operator. "
            "Go to **Human Verification** page to review and approve/reject before acting on this alert."
        )
    elif review_status == "approved":
        st.success(
            f"✅ **Reviewed and Approved** by {session.human_reviewer} at "
            f"{session.review_timestamp[:19] if session.review_timestamp else '?'} UTC"
        )
    elif review_status == "rejected":
        st.error(
            f"❌ **Rejected** by {session.human_reviewer} — "
            f"Notes: {session.human_notes or 'No notes'}"
        )

    # Mode banner
    if session.ai_mode == "demo":
        st.markdown('<div class="demo-banner">🔵 DEMO MODE — These alerts are based on SAMPLE data. Not real AI. Not a real warning.</div>', unsafe_allow_html=True)
    elif session.data_mode == "sample":
        st.markdown(
            '<div style="background:#1A237E22;border:1px solid #3F51B5;border-radius:6px;'
            'padding:10px 16px;font-size:0.85em;color:#9FA8DA;margin:8px 0;">'
            '🟢 LIVE AI (IBM Granite) | ⚠️ SAMPLE cyclone track (no real-time cyclone API) | '
            'Open-Meteo weather data</div>',
            unsafe_allow_html=True
        )

    # Big alert display
    color = ALERT_COLORS.get(alert, "#69F0AE")
    st.markdown(
        f'<div style="background:{color}22;border:3px solid {color};border-radius:12px;'
        f'padding:24px;text-align:center;margin:16px 0;">'
        f'<div style="font-size:3em;font-weight:900;color:{color};">{alert} ALERT</div>'
        f'<div style="font-size:1.2em;color:#dde;margin-top:8px;">'
        f'Risk Level: {risk} | {cyclone_out.get("storm_name", "?")} — '
        f'{cyclone_out.get("current_intensity", "?")}</div>'
        f'<div style="font-size:0.85em;color:#aaa;margin-top:6px;">'
        f'AI Mode: {session.ai_mode.upper()} | Data: {session.data_source_label} | '
        f'Review: {review_status.upper()}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Evidence section — required for any human review
    with st.expander("📋 Evidence & Source Information (required for human review)", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Analysis Evidence**")
            st.markdown(f"- AI Provider: `{session.provider_name}` (`{session.model_name}`)")
            st.markdown(f"- AI Mode: `{session.ai_mode}` (live = real IBM Granite response)")
            st.markdown(f"- Weather Data: `{session.data_source_label}`")
            st.markdown(f"- Cyclone Track: `SAMPLE — Cyclone AGNI is illustrative only`")
            st.markdown(f"- Session ID: `{session.session_id}`")
            st.markdown(f"- Analysis time: `{session.end_time[:19] if session.end_time else '?'} UTC`")
        with col2:
            st.markdown("**Risk Justification**")
            st.write(impact_out.get("risk_justification", "No justification provided."))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📋 Preparedness Checklist")
        actions = impact_out.get("preparedness_actions", [])
        for action in actions:
            st.checkbox(action, key=f"check_{action[:20]}")

    with col2:
        st.markdown("### ☎️ Emergency Contacts")
        contacts = {
            "IMD Helpline": "1800-180-1717",
            "NDMA": "011-26701700",
            "NDRF": "011-24363260",
            "Coast Guard": "1554",
            "Emergency": "112",
        }
        for name, number in contacts.items():
            st.markdown(f"**{name}:** `{number}`")

        st.markdown("### 🌐 Official Sources")
        st.markdown("- [IMD India](https://mausam.imd.gov.in)")
        st.markdown("- [NDMA India](https://ndma.gov.in)")
        st.markdown("- [INCOIS](https://incois.gov.in)")

    st.markdown("---")
    st.error(
        "⚠️ **EDUCATIONAL PROTOTYPE ONLY** — This AI system provides decision-support only. "
        "It does NOT issue official government warnings. "
        "CycloneShield AI has NOT verified any real cyclone. "
        "The 'Cyclone AGNI' track is a fictional sample — not a real active system. "
        "Always consult official IMD bulletins. Call IMD: **1800-180-1717**"
    )
    conf_val = impact_out.get("confidence", 0)
    if isinstance(conf_val, (int, float)):
        conf_str = f"{conf_val:.0%}"
    else:
        conf_str = str(conf_val)
    st.caption(
        f"Data source: {impact_out.get('data_source', 'sample')} | "
        f"AI confidence: {conf_str} | "
        f"Review: {review_status} | "
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )


def page_multi_agent():
    st.markdown('<div class="section-header">🤖 Multi-Agent Activity Monitor</div>', unsafe_allow_html=True)

    session: AnalysisSession = st.session_state.analysis_session
    if not session:
        st.info("Run the analysis first to see agent activity.")
        return

    log = session.execution_log or get_execution_log()

    # Agent summary cards
    agents = ["Weather Intelligence Agent", "Cyclone Detection & Tracking Agent",
              "Impact Assessment & Early Warning Agent", "CycloneShield Coordinator"]

    cols = st.columns(len(agents))
    for i, agent in enumerate(agents):
        agent_events = [e for e in log if e.get("agent") == agent]
        status_events = [e for e in agent_events if e.get("event") in ("complete", "error")]
        status = "ok"
        if status_events:
            status = status_events[-1].get("status", "ok")
        duration = sum(e.get("duration_ms", 0) for e in agent_events if e.get("event") == "complete")
        short_name = agent.split()[0]
        with cols[i]:
            color = "#00C853" if status == "ok" else "#FF5252"
            st.markdown(
                f'<div style="background:#1E2A3A;border:2px solid {color};border-radius:8px;'
                f'padding:12px;text-align:center;">'
                f'<div style="font-size:0.75em;color:#aab;">{short_name}</div>'
                f'<div style="font-size:1.1em;font-weight:700;color:{color};">'
                f'{"✓ OK" if status == "ok" else "✗ ERROR"}</div>'
                f'<div style="font-size:0.85em;color:#7AB;">{duration:.0f} ms</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    # Timeline chart
    if log:
        st.plotly_chart(agent_timeline_chart(log), use_container_width=True)

    # Detailed execution log
    st.markdown("### 📜 Execution Log")
    col1, col2 = st.columns([3, 1])
    with col2:
        filter_agent = st.selectbox("Filter by Agent", ["All"] + list({e.get("agent", "?") for e in log}))

    filtered_log = log if filter_agent == "All" else [e for e in log if e.get("agent") == filter_agent]

    for entry in reversed(filtered_log[-50:]):
        status = entry.get("status", "ok")
        color = "#00C853" if status == "ok" else "#FF5252" if status == "error" else "#FFC400"
        ts = entry.get("timestamp", "")[:19]
        agent = entry.get("agent", "?")[:30]
        event = entry.get("event", "?")
        summary = entry.get("output_summary") or entry.get("input_summary", "")
        dur = entry.get("duration_ms", 0)
        err = entry.get("error", "")

        with st.container():
            st.markdown(
                f'<div style="background:#1a2535;border-left:3px solid {color};'
                f'padding:8px 12px;margin:3px 0;border-radius:0 4px 4px 0;font-size:0.85em;">'
                f'<span style="color:#7AB;">[{ts}]</span> '
                f'<strong style="color:{color};">{agent}</strong> — {event}'
                f'{f" | {summary[:100]}" if summary else ""}'
                f'{f" | ⏱ {dur:.0f}ms" if dur else ""}'
                f'{f" | ❌ {err[:60]}" if err else ""}'
                f'</div>',
                unsafe_allow_html=True
            )

    # Agent communication diagram
    with st.expander("🔗 Agent Communication Flow", expanded=False):
        st.markdown("""
        ```
        ┌─────────────────────────────────────────────────────────────────┐
        │                   CycloneShield AI Pipeline                     │
        └─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Coordinator      │  Loads data, selects provider
                    │  (Orchestrator)   │  manages session memory
                    └─────────┬─────────┘
                              │ weather_data[]
                    ┌─────────▼─────────┐
                    │  Weather Agent    │  LLM: analyzes meteorological data
                    │                   │  Output: weather_analysis JSON
                    └─────────┬─────────┘
                              │ weather_analysis + track_data[]
                    ┌─────────▼─────────┐
                    │  Cyclone Agent    │  LLM: detects cyclone patterns
                    │                   │  Output: cyclone_analysis JSON
                    └─────────┬─────────┘
                              │ cyclone_analysis + weather_analysis
                    ┌─────────▼─────────┐
                    │  Impact Agent     │  LLM: assesses coastal impacts
                    │                   │  Output: impact_assessment JSON
                    └─────────┬─────────┘
                              │ All outputs
                    ┌─────────▼─────────┐
                    │  Human Review     │  Operator approves/rejects
                    │  (Gate)           │  before final alert
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Dashboard        │  Displays all results
                    └───────────────────┘
        ```
        """)


def page_human_verification():
    st.markdown('<div class="section-header">✅ Human Verification</div>', unsafe_allow_html=True)

    session: AnalysisSession = st.session_state.analysis_session
    if not session:
        st.info("Run the analysis first to enable human review.")
        return

    st.markdown("""
    ### Why Human Verification?
    AI agents provide decision support only. Before any alert is marked *verified*,
    a human operator must review the AI outputs and approve or reject them.
    This prevents automated false alarms and ensures accountability.
    """)

    # Current review status
    review_status = session.human_review_status
    color = {"approved": "#00C853", "rejected": "#FF5252", "pending": "#FFC400"}.get(review_status, "#607D8B")
    st.markdown(
        f'<div style="background:{color}22;border:2px solid {color};border-radius:8px;'
        f'padding:16px;margin:12px 0;">'
        f'<strong>Review Status:</strong> <span style="color:{color};font-weight:700;">'
        f'{review_status.upper()}</span>'
        f'{f" | Reviewer: {session.human_reviewer}" if session.human_reviewer else ""}'
        f'{f" | Notes: {session.human_notes}" if session.human_notes else ""}'
        f'</div>',
        unsafe_allow_html=True
    )

    if review_status == "pending":
        # Show summary for review
        impact_out = session.impact_result.get("output", {})
        cyclone_out = session.cyclone_result.get("output", {})

        st.markdown("### Analysis Summary for Review")
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Storm:** {cyclone_out.get('storm_name', '?')}")
            st.info(f"**Intensity:** {cyclone_out.get('current_intensity', '?')}")
            st.info(f"**Wind Speed:** {cyclone_out.get('wind_speed_kmh', '?')} km/h")
        with col2:
            st.info(f"**Risk Level:** {impact_out.get('overall_risk_level', '?')}")
            st.info(f"**Alert Level:** {impact_out.get('recommended_alert_level', '?')}")
            st.info(f"**Provider:** {session.provider_name} (demo={session.provider_name == 'demo'})")

        st.warning(
            "⚠️ Remember: This is AI-generated analysis based on "
            f"{'SAMPLE' if session.data_mode == 'sample' else 'LIVE'} data. "
            "Verify against official IMD sources before taking any action."
        )

        st.markdown("### Submit Review Decision")
        with st.form("review_form"):
            reviewer = st.text_input("Your Name / Role", placeholder="e.g., Duty Officer, SDMA")
            decision = st.radio("Decision", ["approve", "reject"])
            notes = st.text_area("Notes / Observations", placeholder="Add any notes about this analysis...")
            submitted = st.form_submit_button("Submit Review", type="primary")

        if submitted:
            if not reviewer.strip():
                st.error("Please enter your name/role before submitting.")
            else:
                updated = submit_human_review(
                    session,
                    decision=decision + "d",  # "approved" / "rejected"
                    reviewer=reviewer,
                    notes=notes,
                )
                st.session_state.analysis_session = updated
                st.success(f"Review submitted: {decision.upper()} by {reviewer}")
                st.rerun()
    else:
        st.success(
            f"Review completed: **{review_status.upper()}** by {session.human_reviewer} "
            f"at {session.review_timestamp[:19] if session.review_timestamp else '?'} UTC"
        )
        if session.human_notes:
            st.info(f"Notes: {session.human_notes}")

        if st.button("Reset Review (Re-analyze)"):
            session.human_review_status = "pending"
            session.human_reviewer = ""
            session.human_notes = ""
            st.rerun()


def page_model_evaluation():
    st.markdown('<div class="section-header">📈 Model Evaluation</div>', unsafe_allow_html=True)

    session: AnalysisSession = st.session_state.analysis_session
    if not session or not session.llm_eval:
        st.info("Run the analysis first to see evaluation metrics.")
        return

    eval_data = session.llm_eval

    st.markdown("""
    Evaluation measures **structure accuracy** (did the LLM return valid JSON?),
    **output completeness** (required fields present?), **speed** (end-to-end latency),
    and **estimated cost** (token pricing where available).

    > No fabricated accuracy metrics. These are objective, measurable properties.
    """)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Latency", f"{eval_data.get('total_latency_ms', 0):.0f} ms")
    with col2:
        st.metric("Total Tokens", eval_data.get("total_tokens", 0))
    with col3:
        st.metric("Est. Cost", f"${eval_data.get('total_cost_usd', 0):.6f}")
    with col4:
        st.metric("JSON Validity", f"{eval_data.get('json_validity_score', 0):.0%}")

    st.metric("Output Completeness", f"{eval_data.get('output_completeness_score', 0):.0%}")
    st.markdown(f"**Provider(s):** {', '.join(eval_data.get('providers_used', ['?']))}")
    st.markdown(f"**Model(s):** {', '.join(eval_data.get('models_used', ['?']))}")

    st.markdown("---")

    # Per-agent breakdown
    st.markdown("### Per-Agent Breakdown")
    per_agent = eval_data.get("per_agent", {})
    if per_agent:
        df_eval = pd.DataFrame([
            {
                "Agent": name.replace("_", " ").title(),
                "Latency (ms)": round(data.get("latency_ms", 0), 1),
                "Tokens": data.get("tokens", 0),
                "Provider": data.get("provider", "?"),
            }
            for name, data in per_agent.items()
        ])
        st.dataframe(df_eval, use_container_width=True, hide_index=True)

    # Multi-provider comparison (if demo mode, show all demo)
    st.markdown("---")
    st.markdown("### Multi-Provider Comparison")
    if session.provider_name == "demo":
        st.info("Demo mode active. Configure multiple API keys in .env to enable provider comparison.")
    else:
        st.info("Live provider active. Configure additional API keys to enable head-to-head comparison.")

    st.caption(eval_data.get("note", ""))


def page_settings():
    st.markdown('<div class="section-header">⚙️ Settings & Configuration Diagnostics</div>', unsafe_allow_html=True)

    from providers.factory import get_provider_mode
    mode_info = get_provider_mode()

    # ── SDK / Interpreter Diagnostic ─────────────────────────────────────────
    st.markdown("### 🐍 SDK & Python Environment")
    if _SDK_ENV["sdk_ok"]:
        st.success(
            f"✅ **ibm-watsonx-ai {_SDK_ENV['sdk_version']}** installed\n\n"
            f"Python {_SDK_ENV['python_version']} | Interpreter: `{_SDK_ENV['interpreter_path']}`"
        )
    else:
        st.error(
            f"❌ **ibm-watsonx-ai NOT available in this interpreter**\n\n"
            f"Reason: {_SDK_ENV.get('reason', 'import failed')}\n\n"
            f"Python: {_SDK_ENV['python_version']} | Interpreter: `{_SDK_ENV['interpreter_path']}`"
        )
        st.warning(
            "**Fix required:**\n\n"
            + _SDK_ENV.get("fix_cmd", "Install ibm-watsonx-ai>=1.9.1 in this interpreter.")
        )
        st.info(
            "**Why this happens:** The system `streamlit` command uses Python 3.15 which "
            "does NOT support `ibm-watsonx-ai` (all versions require Python <3.15). "
            "You must use the `.venv` interpreter (Python 3.13) which has the SDK installed.\n\n"
            "**Correct launch commands:**\n"
            "```\n"
            "# PowerShell:\n"
            ".venv\\Scripts\\python.exe -m streamlit run app.py --server.port 8503\n\n"
            "# Or use the launcher:\n"
            "run.bat   (Windows CMD)\n"
            ".\\run.ps1  (PowerShell)\n"
            "```"
        )

    st.markdown("---")

    # ── Current Operating Mode ────────────────────────────────────────────────
    st.markdown("### 🤖 AI Provider Status")
    if mode_info["mode"] == "live":
        st.success(
            f"🟢 **LIVE AI MODE** — IBM Granite (`{mode_info['model_name']}`) is active.\n\n"
            f"Real IBM watsonx.ai responses will be used for all three agents."
        )
    elif mode_info["mode"] == "misconfigured":
        st.error(
            f"🔴 **CONFIGURATION ERROR** — APP_MODE=live is set but credentials are missing.\n\n"
            f"Reason: {mode_info.get('reason', 'credentials not configured')}\n\n"
            f"Set IBM_GRANITE_API_KEY and IBM_GRANITE_PROJECT_ID in .env to fix this."
        )
    else:
        st.info(
            f"🔵 **DEMO MODE** — No real AI responses.\n\n"
            f"Reason: {mode_info.get('reason', 'credentials not configured')}\n\n"
            f"Configure IBM watsonx.ai credentials below to enable Live AI."
        )

    # ── Connectivity Test (safe — only when explicitly clicked) ──────────────
    if _SDK_ENV["sdk_ok"]:
        ibm_key = os.getenv("IBM_GRANITE_API_KEY", "")
        ibm_pid = os.getenv("IBM_GRANITE_PROJECT_ID", "")
        placeholders_ibm = {"", "your_ibm_api_key_here", "your_ibm_project_id_here"}
        ibm_creds_ok = (
            bool(ibm_key) and ibm_key not in placeholders_ibm
            and bool(ibm_pid) and ibm_pid not in placeholders_ibm
        )

        if ibm_creds_ok:
            if st.button(
                "🔍 Test IBM Granite Connectivity (sends one real API request)",
                type="secondary",
                help="Sends a minimal test prompt to ibm/granite-4-h-small. Requires valid credentials. Does NOT display your API key.",
            ):
                with st.spinner("Testing IBM Granite (ibm/granite-4-h-small) via chat API…"):
                    try:
                        from providers.granite import GraniteProvider
                        _test_p = GraniteProvider()
                        _test_resp = _test_p.complete(
                            prompt="Reply with: {\"ping\":\"pong\"}",
                            system_prompt="You are a test system. Reply only with valid JSON.",
                            max_tokens=20,
                        )
                        if _test_resp.success:
                            st.success(
                                f"✅ **IBM Granite ibm/granite-4-h-small responded successfully**\n\n"
                                f"Tokens: {_test_resp.total_tokens} | Latency: {_test_resp.latency_ms:.0f} ms\n\n"
                                f"Response preview: `{_test_resp.text[:80]}`"
                            )
                        else:
                            st.error(f"❌ Granite returned an error: {_test_resp.error}")
                    except Exception as _e:
                        st.error(f"❌ Connectivity test failed: {_e}")
        else:
            st.caption("Configure IBM credentials in .env to enable the connectivity test.")

    st.markdown("---")
    st.markdown("### 🔑 API Key Status")
    st.markdown("""
    API keys are read from a `.env` file in the project root.
    **Never enter API keys directly in this UI** — use the `.env` file only.
    Credentials are never displayed, logged, or committed to git.
    """)

    ibm_key = os.getenv("IBM_GRANITE_API_KEY", "")
    ibm_pid = os.getenv("IBM_GRANITE_PROJECT_ID", "")
    owm_key = os.getenv("OPENWEATHER_API_KEY", "")
    placeholders = {"", "your_ibm_api_key_here", "your_ibm_project_id_here"}
    ibm_ok = bool(ibm_key) and ibm_key not in placeholders and bool(ibm_pid) and ibm_pid not in placeholders

    providers_status = {
        f"IBM watsonx.ai Granite (`{mode_info['model_name']}`)": ibm_ok,
        "OpenWeatherMap (optional — additional live weather)": bool(owm_key and owm_key not in {"", "your_openweather_api_key_here"}),
        "Open-Meteo (free — no key required)": True,
    }
    for provider_name_disp, configured in providers_status.items():
        icon = "🟢" if configured else "⚪"
        st.markdown(f"{icon} **{provider_name_disp}**: {'Configured ✓' if configured else 'Not configured'}")

    st.markdown("---")
    st.markdown("### ⚙️ Current Configuration")
    st.markdown(f"**APP_MODE:** `{os.getenv('APP_MODE', 'not set — auto-detecting from credentials')}`")
    st.markdown(f"**IBM_GRANITE_URL:** `{os.getenv('IBM_GRANITE_URL', 'https://us-south.ml.cloud.ibm.com (default)')}`")
    st.markdown(f"**IBM_GRANITE_API_KEY:** `{'[SET — not displayed]' if ibm_key and ibm_key not in placeholders else '[NOT SET]'}`")
    st.markdown(f"**IBM_GRANITE_PROJECT_ID:** `{'[SET — not displayed]' if ibm_pid and ibm_pid not in {'', 'your_ibm_project_id_here'} else '[NOT SET]'}`")
    st.markdown(f"**Open-Meteo (live weather):** `always available — no key required`")
    st.markdown(f"**SDK available in this interpreter:** `{'YES — ibm-watsonx-ai ' + _SDK_ENV['sdk_version'] if _SDK_ENV['sdk_ok'] else 'NO — use .venv (Python 3.13)'}`")
    st.markdown(f"**Python interpreter:** `{sys.executable}`")

    st.markdown("---")
    st.markdown("### 📋 .env Setup Instructions")
    st.code("""# 1. Copy the example file:
Copy-Item .env.example .env   (PowerShell)
cp .env.example .env          (Linux/Mac)

# 2. Edit .env — add your IBM watsonx.ai credentials:
IBM_GRANITE_API_KEY=your_actual_ibm_api_key
IBM_GRANITE_PROJECT_ID=your_actual_project_id
IBM_GRANITE_URL=https://us-south.ml.cloud.ibm.com

# 3. To enable live AI, remove or comment APP_MODE=demo:
# APP_MODE=live    # (or just remove the APP_MODE line entirely)

# 4. Launch using the .venv interpreter (Python 3.13):
.venv\\Scripts\\python.exe -m streamlit run app.py --server.port 8503
# or simply:
run.bat           (Windows CMD)
.\\run.ps1        (PowerShell)
""", language="bash")

    st.markdown("---")
    st.markdown("### 🛡️ Security & Guardrails")
    st.markdown("""
    - ✅ API keys stored in `.env` only — never in code, frontend, or logs
    - ✅ `.env` excluded from git via `.gitignore`
    - ✅ Prompt injection detection (regex pattern matching on all LLM inputs)
    - ✅ Input length limit: 10,000 characters
    - ✅ Output JSON schema validation on all agent responses
    - ✅ Human-in-the-loop approval required before any alert is marked verified
    - ✅ Demo mode clearly labelled — never disguised as live AI
    - ✅ AI never issues official government warnings
    - ✅ Live AI mode confirmed only after a genuine Granite response received
    - ✅ Sample/synthetic data never presented as real observations
    - ✅ Cyclone AGNI labeled as SAMPLE everywhere — not a real current cyclone
    """)


def _render_system_overview():
    """Render the system architecture overview for first-time users."""
    st.markdown("---")
    st.markdown("### 🏗️ System Architecture")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        **Agent 1: Weather Intelligence**
        - Validates meteorological data
        - Detects pressure anomalies
        - Identifies wind patterns
        - Flags missing data
        """)
    with col2:
        st.markdown("""
        **Agent 2: Cyclone Detection**
        - Examines cyclone patterns
        - Processes track coordinates
        - Estimates intensity
        - Identifies uncertainty
        """)
    with col3:
        st.markdown("""
        **Agent 3: Impact Assessment**
        - Evaluates coastal impacts
        - Assesses vulnerable districts
        - Generates preparedness guidance
        - Routes to human review
        """)


# ── Main app ──────────────────────────────────────────────────────────────────
def main():
    render_sidebar()
    maybe_run_analysis()

    page = st.session_state.nav_page
    page_map = {
        "Overview": page_overview,
        "Weather Intelligence": page_weather_intelligence,
        "Cyclone Detection": page_cyclone_detection,
        "Cyclone Tracking": page_cyclone_tracking,
        "Impact Assessment": page_impact_assessment,
        "Early Warning": page_early_warning,
        "Multi-Agent Activity": page_multi_agent,
        "Human Verification": page_human_verification,
        "Model Evaluation": page_model_evaluation,
        "Settings": page_settings,
    }
    page_fn = page_map.get(page, page_overview)
    page_fn()


if __name__ == "__main__":
    main()
