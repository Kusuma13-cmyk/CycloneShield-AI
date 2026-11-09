"""
CycloneShield AI — Dashboard Components
Reusable chart/map/card functions for Streamlit pages.
"""
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import folium
import streamlit as st
from datetime import datetime


# ── Colour palette ─────────────────────────────────────────────────────────────
COLORS = {
    "extreme": "#FF1744",
    "very_high": "#FF6D00",
    "high": "#FFC400",
    "moderate": "#00BFA5",
    "low": "#00B0FF",
    "minimal": "#69F0AE",
    "navy": "#0D1B2A",
    "blue": "#1565C0",
    "card_bg": "#1E2A3A",
    "text": "#E8F4F8",
}

RISK_COLORS = {
    "EXTREME": "#FF1744",
    "VERY HIGH": "#FF6D00",
    "HIGH": "#FFC400",
    "MODERATE": "#00BFA5",
    "LOW": "#00B0FF",
    "MINIMAL": "#69F0AE",
}

ALERT_COLORS = {
    "RED": "#FF1744",
    "ORANGE": "#FF6D00",
    "YELLOW": "#FFC400",
    "GREEN": "#00C853",
}


def metric_card(label: str, value: str, delta: str = "", color: str = "#1565C0", icon: str = "") -> str:
    """Return HTML for a metric card."""
    return f"""
    <div style="background:{color}22;border:1px solid {color}55;border-radius:8px;
                padding:16px;text-align:center;margin:4px;">
        <div style="font-size:1.8em;margin-bottom:4px;">{icon}</div>
        <div style="font-size:0.75em;color:#aab;text-transform:uppercase;
                    letter-spacing:0.08em;margin-bottom:6px;">{label}</div>
        <div style="font-size:1.5em;font-weight:700;color:{color};">{value}</div>
        {f'<div style="font-size:0.8em;color:#9ab;margin-top:4px;">{delta}</div>' if delta else ""}
    </div>
    """


def risk_badge(risk_level: str) -> str:
    """Return an HTML risk badge."""
    color = RISK_COLORS.get(risk_level.upper(), "#607D8B")
    return f"""<span style="background:{color};color:#fff;font-weight:700;
               padding:4px 12px;border-radius:4px;font-size:0.9em;">{risk_level}</span>"""


def alert_banner(alert_level: str, message: str) -> None:
    """Display a colored alert banner."""
    color = ALERT_COLORS.get(alert_level.upper(), "#1565C0")
    st.markdown(f"""
    <div style="background:{color}22;border-left:5px solid {color};padding:14px 18px;
                border-radius:4px;margin:8px 0;">
        <strong style="color:{color};">🚨 {alert_level} ALERT</strong>
        <p style="margin:6px 0 0;color:#dde;">{message}</p>
    </div>
    """, unsafe_allow_html=True)


def build_cyclone_track_map(track_data: list[dict], current_pos: dict = None) -> folium.Map:
    """
    Build a Folium map showing the cyclone track with colour-coded intensity.
    """
    # Centre on Bay of Bengal
    # CartoDB dark_matter requires a paid API key in Folium >= 0.18.
    # OpenStreetMap is free and requires no key.
    fmap = folium.Map(
        location=[15.0, 82.0],
        zoom_start=5,
        tiles="OpenStreetMap",
    )

    if not track_data:
        return fmap

    # Draw track line
    coords = [(float(p["latitude"]), float(p["longitude"])) for p in track_data
              if p.get("latitude") and p.get("longitude")]

    if coords:
        folium.PolyLine(
            coords,
            color="#FF6D00",
            weight=3,
            opacity=0.9,
            tooltip="Cyclone Track",
        ).add_to(fmap)

    # Intensity colour map
    intensity_colors = {
        "Depression": "#AED6F1",
        "Deep Depression": "#85C1E9",
        "Cyclonic Storm": "#F1C40F",
        "Severe Cyclonic Storm": "#E67E22",
        "Very Severe Cyclonic Storm": "#E74C3C",
        "Extremely Severe Cyclonic Storm": "#922B21",
        "Super Cyclonic Storm": "#6C0000",
    }

    for i, point in enumerate(track_data):
        lat = point.get("latitude")
        lon = point.get("longitude")
        if lat is None or lon is None:
            continue
        intensity = point.get("intensity_category", "Unknown")
        color = intensity_colors.get(intensity, "#90A4AE")
        wind = point.get("wind_speed_kmh", "?")
        pressure = point.get("pressure_hpa", "?")
        ts = point.get("timestamp", "")[:10]

        folium.CircleMarker(
            location=[float(lat), float(lon)],
            radius=6 if i < len(track_data) - 1 else 12,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            popup=folium.Popup(
                f"<b>{point.get('storm_name','Storm')}</b><br>"
                f"Time: {ts}<br>"
                f"Intensity: {intensity}<br>"
                f"Wind: {wind} km/h<br>"
                f"Pressure: {pressure} hPa",
                max_width=220,
            ),
            tooltip=f"{intensity} — {ts}",
        ).add_to(fmap)

    # Coastal India markers
    coastal_cities = [
        ("Puri", 19.80, 85.83),
        ("Gopalpur", 19.27, 84.90),
        ("Visakhapatnam", 17.68, 83.22),
        ("Chennai", 13.08, 80.27),
        ("Bhubaneswar", 20.29, 85.82),
        ("Kolkata", 22.57, 88.36),
    ]
    for city, lat, lon in coastal_cities:
        folium.Marker(
            location=[lat, lon],
            tooltip=city,
            icon=folium.Icon(color="blue", icon="home", prefix="fa"),
        ).add_to(fmap)

    return fmap


def pressure_chart(df: pd.DataFrame) -> go.Figure:
    """Pressure trend chart."""
    fig = go.Figure()
    for station in df["station_name"].unique():
        sdf = df[df["station_name"] == station]
        fig.add_trace(go.Scatter(
            x=sdf["timestamp"], y=sdf["pressure_hpa"],
            mode="lines+markers", name=station,
            line=dict(width=2),
        ))
    fig.add_hline(y=990, line_dash="dash", line_color="orange",
                  annotation_text="Depression threshold (990 hPa)")
    fig.add_hline(y=980, line_dash="dash", line_color="red",
                  annotation_text="Severe threshold (980 hPa)")
    fig.update_layout(
        title="Atmospheric Pressure Trend (hPa)",
        plot_bgcolor="#0D1B2A", paper_bgcolor="#0D1B2A",
        font_color="#E8F4F8",
        xaxis_title="Time (UTC)", yaxis_title="Pressure (hPa)",
        legend=dict(bgcolor="#1E2A3A"),
        height=350,
    )
    return fig


def wind_speed_chart(df: pd.DataFrame) -> go.Figure:
    """Wind speed bar chart."""
    latest = df.sort_values("timestamp").groupby("station_name").last().reset_index()
    colors = ["#FF6D00" if w > 100 else "#FFC400" if w > 63 else "#00BFA5"
              for w in latest["wind_speed_kmh"]]
    fig = go.Figure(go.Bar(
        x=latest["station_name"],
        y=latest["wind_speed_kmh"],
        marker_color=colors,
        text=[f"{w:.0f}" for w in latest["wind_speed_kmh"]],
        textposition="outside",
    ))
    fig.add_hline(y=63, line_dash="dash", line_color="yellow",
                  annotation_text="Cyclone threshold (63 km/h)")
    fig.add_hline(y=89, line_dash="dash", line_color="orange",
                  annotation_text="Severe (89 km/h)")
    fig.update_layout(
        title="Wind Speed by Station (km/h)",
        plot_bgcolor="#0D1B2A", paper_bgcolor="#0D1B2A",
        font_color="#E8F4F8",
        xaxis_title="Station", yaxis_title="Wind Speed (km/h)",
        height=350,
    )
    return fig


def cyclone_intensity_chart(track_df: pd.DataFrame) -> go.Figure:
    """Cyclone intensity (wind + pressure) over time."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=track_df["timestamp"],
        y=track_df["wind_speed_kmh"],
        mode="lines+markers",
        name="Wind Speed (km/h)",
        line=dict(color="#FF6D00", width=2),
        yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=track_df["timestamp"],
        y=track_df["pressure_hpa"],
        mode="lines+markers",
        name="Pressure (hPa)",
        line=dict(color="#00B0FF", width=2, dash="dot"),
        yaxis="y2",
    ))
    fig.update_layout(
        title="Cyclone Intensity Over Time",
        plot_bgcolor="#0D1B2A", paper_bgcolor="#0D1B2A",
        font_color="#E8F4F8",
        xaxis_title="Time (UTC)",
        yaxis=dict(title="Wind Speed (km/h)", side="left"),
        yaxis2=dict(title="Pressure (hPa)", side="right", overlaying="y"),
        legend=dict(bgcolor="#1E2A3A"),
        height=380,
    )
    return fig


def agent_timeline_chart(log_entries: list[dict]) -> go.Figure:
    """Gantt-style agent execution timeline."""
    agent_events = [e for e in log_entries if e.get("event") in ("start", "complete", "error")]
    if not agent_events:
        return go.Figure()

    agents_seen = []
    timeline_data = []
    for e in agent_events:
        agent = e.get("agent", "?")
        if agent not in agents_seen:
            agents_seen.append(agent)
        timeline_data.append({
            "Agent": agent,
            "Event": e.get("event"),
            "Duration": e.get("duration_ms", 50),
            "Status": e.get("status", "ok"),
            "Time": e.get("timestamp", ""),
        })

    fig = px.bar(
        timeline_data[-20:],
        x="Duration",
        y="Agent",
        color="Status",
        orientation="h",
        color_discrete_map={"ok": "#00C853", "error": "#FF1744", "skipped": "#607D8B"},
        title="Agent Execution Timeline (ms)",
    )
    fig.update_layout(
        plot_bgcolor="#0D1B2A", paper_bgcolor="#0D1B2A",
        font_color="#E8F4F8", height=300,
    )
    return fig


def render_json_card(title: str, data: dict, expanded: bool = False) -> None:
    """Render a collapsible JSON output card."""
    with st.expander(title, expanded=expanded):
        # Show key fields as readable text first
        st.json(data)
