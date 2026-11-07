"""
CycloneShield AI — Main Streamlit Application
Agentic AI-based Cyclone Detection & Early Warning System for coastal India

Run with: python -m streamlit run app.py
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
        )

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
        app_mode = os.getenv("APP_MODE", "demo")
        st.markdown(f"**Mode:** {'🔵 Demo' if app_mode == 'demo' else '🟢 Live'}")
        st.caption("CycloneShield AI v1.0 | Hackathon Edition")


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
            data_mode="sample",
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
    
    # Demo banner
    if session.provider_name == "demo":
        st.markdown(
            '<div class="demo-banner">⚠️ <strong>DEMO MODE</strong> — '
            'All results are based on sample data. Not real weather observations. '
            'Configure an API key in .env to enable live AI analysis.</div>',
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
        st.markdown(f"**Provider:** {session.provider_name} ({session.llm_eval.get('models_used', ['?'])[0] if session.llm_eval else '?'})")
        st.markdown(f"**Total Time:** {session.total_duration_ms:.0f} ms")
        st.markdown(f"**Data Mode:** {session.data_mode}")
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

    # Demo warning
    if session.provider_name == "demo":
        st.markdown('<div class="demo-banner">⚠️ SAMPLE DATA — Not real observations</div>', unsafe_allow_html=True)

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

    # Charts
    try:
        weather_data = load_sample_weather_data()
        df = pd.DataFrame(weather_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df = df.dropna(subset=["pressure_hpa", "wind_speed_kmh"])
        if not df.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(pressure_chart(df), use_container_width=True)
            with col2:
                st.plotly_chart(wind_speed_chart(df), use_container_width=True)
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

    if session.provider_name == "demo":
        st.markdown('<div class="demo-banner">⚠️ SAMPLE DATA — Not real cyclone data</div>', unsafe_allow_html=True)

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

    if session and session.provider_name == "demo":
        st.markdown('<div class="demo-banner">⚠️ SAMPLE TRACK DATA — Not a real cyclone track</div>', unsafe_allow_html=True)

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
        # Fallback: Plotly scatter map
        track_df = pd.DataFrame(track_data)
        track_df = track_df.dropna(subset=["latitude", "longitude"])
        fig = __import__("plotly.express", fromlist=["scatter_mapbox"]).scatter_mapbox(
            track_df, lat="latitude", lon="longitude",
            color="intensity_category",
            hover_name="storm_name",
            hover_data=["wind_speed_kmh", "pressure_hpa", "timestamp"],
            mapbox_style="carto-darkmatter",
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

    st.caption(f"⚠️ Data source: {latest.get('source', 'Sample')} — Not a real-time official cyclone track")


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

    if session.provider_name == "demo":
        st.markdown('<div class="demo-banner">⚠️ SAMPLE DATA — Not a real impact assessment</div>', unsafe_allow_html=True)

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

    # Big alert display
    color = ALERT_COLORS.get(alert, "#69F0AE")
    st.markdown(
        f'<div style="background:{color}22;border:3px solid {color};border-radius:12px;'
        f'padding:24px;text-align:center;margin:16px 0;">'
        f'<div style="font-size:3em;font-weight:900;color:{color};">{alert} ALERT</div>'
        f'<div style="font-size:1.2em;color:#dde;margin-top:8px;">'
        f'Risk Level: {risk} | {cyclone_out.get("storm_name", "?")} — '
        f'{cyclone_out.get("current_intensity", "?")}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

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
        "⚠️ **IMPORTANT DISCLAIMER**: This AI system provides decision-support only. "
        "It does NOT issue official government warnings. Always follow official IMD bulletins. "
        "Contact IMD at **1800-180-1717** for verified cyclone information."
    )
    st.caption(f"Data source: {impact_out.get('data_source', 'sample')} | "
               f"Confidence: {impact_out.get('confidence', 0):.0%} | "
               f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")


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
    st.markdown('<div class="section-header">⚙️ Settings & API Configuration</div>', unsafe_allow_html=True)

    st.markdown("### API Key Status")
    st.markdown("""
    API keys are read from a `.env` file in the project root.
    **Never enter API keys directly in this form** — use the `.env` file.
    """)

    # Show configured status (never show actual keys)
    providers_status = {
        "IBM watsonx.ai (Granite)": bool(os.getenv("IBM_GRANITE_API_KEY") and os.getenv("IBM_GRANITE_PROJECT_ID")),
        "OpenWeatherMap": bool(os.getenv("OPENWEATHER_API_KEY")),
    }

    for provider, configured in providers_status.items():
        icon = "🟢" if configured else "⚪"
        st.markdown(f"{icon} **{provider}**: {'Configured' if configured else 'Not configured'}")

    st.markdown("---")
    st.markdown("### .env Setup Instructions")
    st.code("""
# 1. Copy the example file:
#    cp .env.example .env

# 2. Edit .env and add your IBM watsonx.ai credentials:
IBM_GRANITE_API_KEY=your_ibm_api_key
IBM_GRANITE_PROJECT_ID=your_project_id
IBM_GRANITE_URL=https://us-south.ml.cloud.ibm.com

# 3. Set primary provider (IBM watsonx.ai only):
PRIMARY_LLM_PROVIDER=granite

# 4. For demo mode (no real API):
APP_MODE=demo
    """, language="bash")

    st.markdown("---")
    st.markdown("### Current Configuration")
    st.markdown(f"**APP_MODE:** `{os.getenv('APP_MODE', 'not set (defaults to auto-detect)')}`")
    st.markdown(f"**PRIMARY_LLM_PROVIDER:** `{os.getenv('PRIMARY_LLM_PROVIDER', 'not set (auto-detect)')}`")
    st.markdown(f"**IBM_GRANITE_URL:** `{os.getenv('IBM_GRANITE_URL', 'not set')}`")

    st.markdown("---")
    st.markdown("### Guardrails & Security")
    st.markdown("""
    - ✅ API keys stored in `.env` (never in code or frontend)
    - ✅ Prompt injection detection (regex pattern matching)
    - ✅ Input length limits (max 10,000 characters)
    - ✅ Output JSON schema validation
    - ✅ Human-in-the-loop approval before alert verification
    - ✅ Demo mode clearly labelled — never disguised as real data
    - ✅ AI never issues official government warnings
    - ✅ All outputs include uncertainty and source information
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
