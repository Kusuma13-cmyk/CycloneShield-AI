"use client";
import type { AnalysisSession } from "../../lib/api";

const RISK_COLORS: Record<string, string> = {
  EXTREME: "#FF1744", "VERY HIGH": "#FF6D00", HIGH: "#FFC400",
  MODERATE: "#00BFA5", LOW: "#00B0FF", MINIMAL: "#69F0AE",
};
const ALERT_COLORS: Record<string, string> = {
  RED: "#FF1744", ORANGE: "#FF6D00", YELLOW: "#FFC400", GREEN: "#00C853",
};

interface Props {
  session: AnalysisSession | null;
  onRunAnalysis: () => void;
  loading: boolean;
}

export default function OverviewPage({ session, onRunAnalysis, loading }: Props) {
  if (!session) {
    return (
      <div>
        <div className="page-title">🌀 CycloneShield AI</div>
        <div className="page-subtitle">
          Agentic AI-based Cyclone Detection &amp; Early Warning System — Coastal India
        </div>

        <div className="info-box" style={{ maxWidth: 560, margin: "24px auto" }}>
          <p style={{ fontWeight: 700, marginBottom: 8 }}>👋 Welcome to CycloneShield AI</p>
          <p>
            This system uses three specialized AI agents to monitor weather patterns, detect
            cyclone threats, and generate impact assessments for coastal India.
          </p>
          <p style={{ marginTop: 8, color: "#90A4AE" }}>
            Click <strong>Run Analysis</strong> to start the pipeline.
          </p>
        </div>

        <div style={{ textAlign: "center", margin: "16px 0" }}>
          <button className="btn-primary" onClick={onRunAnalysis} disabled={loading}
                  style={{ fontSize: "1.05em", padding: "12px 32px" }}>
            {loading ? "⏳ Running..." : "🚀 Run Full Analysis"}
          </button>
        </div>

        <div className="section-header">🏗️ System Architecture</div>
        <div className="grid-3">
          {[
            { name: "Agent 1: Weather Intelligence", items: ["Validates meteorological data", "Detects pressure anomalies", "Identifies wind patterns", "Flags missing data"] },
            { name: "Agent 2: Cyclone Detection", items: ["Examines cyclone patterns", "Processes track coordinates", "Estimates intensity", "Identifies uncertainty"] },
            { name: "Agent 3: Impact Assessment", items: ["Evaluates coastal impacts", "Assesses vulnerable districts", "Generates preparedness guidance", "Routes to human review"] },
          ].map((agent) => (
            <div key={agent.name} className="card">
              <p style={{ fontWeight: 700, color: "#64B5F6", marginBottom: 8 }}>{agent.name}</p>
              <ul style={{ paddingLeft: 16, color: "#90A4AE", fontSize: "0.88em" }}>
                {agent.items.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const impact = (session.impact_result?.output ?? {}) as Record<string, unknown>;
  const cyclone = (session.cyclone_result?.output ?? {}) as Record<string, unknown>;
  const weather = (session.weather_result?.output ?? {}) as Record<string, unknown>;

  const risk = (impact.overall_risk_level as string) || "Unknown";
  // recommended_alert_level is an AI assessment label, not an official government warning.
  // Show "Unknown" when the field is absent so the UI never displays bare "?".
  const rawAlert = impact.recommended_alert_level as string | undefined;
  const alert = rawAlert && ALERT_COLORS[rawAlert] ? rawAlert : null;
  const alertDisplay = alert ?? (rawAlert || "Unknown");
  const intensity = (cyclone.current_intensity as string) || "Unknown";
  const wind = cyclone.wind_speed_kmh as number | null;
  const pressure = cyclone.pressure_hpa as number | null;
  const recommendation = (weather.recommendation as string) || "Unknown";

  const alertColor = alert ? (ALERT_COLORS[alert] ?? "#607D8B") : "#607D8B";
  const riskColor = RISK_COLORS[risk] ?? "#607D8B";

  return (
    <div>
      <div className="page-title">🌀 CycloneShield AI</div>
      <div className="page-subtitle">Agentic AI-based Cyclone Detection &amp; Early Warning — Coastal India</div>

      {/* Alert banner */}
      {(alert === "RED" || alert === "ORANGE") && (
        <div className="alert-banner" style={{ borderColor: alertColor, background: `${alertColor}18` }}>
          <strong style={{ color: alertColor }}>🚨 {alert} ALERT (AI assessment — not an official IMD warning)</strong>
          <span style={{ marginLeft: 12, color: "#dde" }}>
            {risk} risk — {(cyclone.storm_name as string) ?? "Cyclone"} | {intensity}
          </span>
        </div>
      )}

      {/* Demo banner */}
      {session.provider_name === "demo" && (
        <div className="demo-banner">
          ⚠️ <strong>DEMO MODE</strong> — All results are based on sample data. Not real weather
          observations. Configure IBM_GRANITE_API_KEY in environment variables to enable live AI.
        </div>
      )}

      {/* Metrics row */}
      <div className="grid-5" style={{ margin: "16px 0" }}>
        {[
          { label: "Risk Level", value: risk, color: riskColor, icon: "⚡" },
          { label: "Alert Level (AI)", value: alertDisplay, color: alertColor, icon: "🚨" },
          { label: "Wind Speed", value: wind != null ? `${wind} km/h` : "?", color: "#FF6D00", icon: "💨" },
          { label: "Pressure", value: pressure != null ? `${pressure} hPa` : "?", color: "#00B0FF", icon: "🌡️" },
          { label: "Intensity", value: intensity.split(" ").pop() ?? intensity, color: "#9C27B0", icon: "🌀" },
        ].map((m) => (
          <div key={m.label} className="metric-card" style={{ borderColor: `${m.color}55`, background: `${m.color}11` }}>
            <div style={{ fontSize: "1.5em", marginBottom: 4 }}>{m.icon}</div>
            <div className="metric-label">{m.label}</div>
            <div className="metric-value" style={{ color: m.color }}>{m.value}</div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        {/* Agent pipeline status */}
        <div>
          <div className="section-header">Agent Pipeline Status</div>
          {[
            { name: "🌦️ Weather Intelligence", status: session.weather_result?.status, dur: session.weather_result?.duration_ms ?? 0, detail: recommendation },
            { name: "🌀 Cyclone Detection", status: session.cyclone_result?.status, dur: session.cyclone_result?.duration_ms ?? 0, detail: intensity },
            { name: "⚠️ Impact Assessment", status: session.impact_result?.status, dur: session.impact_result?.duration_ms ?? 0, detail: risk },
            { name: "✅ Human Review", status: session.human_review_status, dur: 0, detail: session.human_review_status },
          ].map((a) => {
            const cls = a.status === "ok" || a.status === "approved" ? "status-ok" :
                        a.status === "error" ? "status-error" : "status-pending";
            return (
              <div key={a.name} className="card" style={{ marginBottom: 6, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong>{a.name}</strong>
                <span className={cls} style={{ marginLeft: 8 }}>{(a.status ?? "?").toUpperCase()}</span>
                <span style={{ color: "#7A9BB5", marginLeft: "auto", fontSize: "0.82em" }}>
                  {a.dur > 0 ? `${a.dur.toFixed(0)} ms` : ""} {a.detail ? `| ${a.detail}` : ""}
                </span>
              </div>
            );
          })}
        </div>

        {/* Analysis info */}
        <div>
          <div className="section-header">Analysis Info</div>
          <div className="card">
            <table>
              <tbody>
                {[
                  ["Session", session.session_id],
                  ["Provider", session.provider_name],
                  ["Model", (session.llm_eval?.models_used?.[0] ?? "?")],
                  ["Total Time", `${session.total_duration_ms.toFixed(0)} ms`],
                  ["Data Mode", session.data_mode],
                  ["Errors", session.errors?.length.toString() ?? "0"],
                ].map(([k, v]) => (
                  <tr key={k}><th>{k}</th><td style={{ fontFamily: "monospace" }}>{v}</td></tr>
                ))}
              </tbody>
            </table>
            {session.errors?.length > 0 && (
              <div className="error-box" style={{ marginTop: 10 }}>
                {session.errors.map((e, i) => <p key={i}>⚠️ {e}</p>)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
