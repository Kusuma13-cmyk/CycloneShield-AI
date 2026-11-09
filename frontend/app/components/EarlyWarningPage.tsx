"use client";
import type { AnalysisSession } from "../../lib/api";
import { useState } from "react";

const ALERT_COLORS: Record<string, string> = {
  RED: "#FF1744", ORANGE: "#FF6D00", YELLOW: "#FFC400", GREEN: "#00C853",
};
const EMERGENCY_CONTACTS = [
  { name: "IMD Helpline", number: "1800-180-1717" },
  { name: "NDMA", number: "011-26701700" },
  { name: "NDRF", number: "011-24363260" },
  { name: "Coast Guard", number: "1554" },
  { name: "Emergency", number: "112" },
];

interface Props { session: AnalysisSession | null; }

export default function EarlyWarningPage({ session }: Props) {
  const [checked, setChecked] = useState<Record<string, boolean>>({});

  if (!session) {
    return (
      <div>
        <div className="section-header">🚨 Early Warning</div>
        <div className="info-box">Run the analysis first.</div>
      </div>
    );
  }

  const impact = (session.impact_result?.output ?? {}) as Record<string, unknown>;
  const cyclone = (session.cyclone_result?.output ?? {}) as Record<string, unknown>;

  const alert = (impact.recommended_alert_level as string) ?? "GREEN";
  const risk = (impact.overall_risk_level as string) ?? "MINIMAL";
  const alertColor = ALERT_COLORS[alert] ?? "#00C853";
  const actions = (impact.preparedness_actions as string[]) ?? [];
  const confidence = (impact.confidence as number) ?? 0;

  // recommended_alert_level is an AI assessment label, not an official government warning.
  const alertDisplay = ALERT_COLORS[alert] ? alert : "Unknown";
  const alertColorFinal = ALERT_COLORS[alertDisplay] ?? "#607D8B";

  return (
    <div>
      <div className="section-header">🚨 Early Warning</div>

      {(session.provider_name === "demo" || session.data_mode === "sample") && (
        <div className="demo-banner">
          ⚠️ <strong>DEMO / SAMPLE DATA</strong> — All alert levels and risk assessments below
          are AI-generated estimates based on synthetic test data. They are{" "}
          <strong>not</strong> official IMD warnings or verified observations.
        </div>
      )}

      {/* Big alert display */}
      <div className="alert-banner" style={{
        borderColor: alertColorFinal, background: `${alertColorFinal}18`,
        textAlign: "center", padding: 28, marginBottom: 20,
      }}>
        <div style={{ fontSize: "2.4em", fontWeight: 900, color: alertColorFinal }}>
          {alertDisplay} ALERT
        </div>
        <div style={{ fontSize: "0.88em", color: "#90A4AE", marginTop: 4, fontStyle: "italic" }}>
          AI risk assessment only — not an official IMD warning
        </div>
        <div style={{ fontSize: "1.1em", color: "#dde", marginTop: 8 }}>
          Risk Level: {risk} | {(cyclone.storm_name as string) ?? "Unknown"} — {(cyclone.current_intensity as string) ?? "Unknown"}
        </div>
      </div>

      <div className="grid-2">
        {/* Preparedness checklist */}
        <div>
          <div className="section-header">📋 Preparedness Checklist</div>
          <div className="card">
            {actions.length > 0 ? actions.map((action, i) => (
              <label key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10, cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={checked[action] ?? false}
                  onChange={(e) => setChecked((c) => ({ ...c, [action]: e.target.checked }))}
                  style={{ marginTop: 3, accentColor: alertColorFinal, width: 16, height: 16, flexShrink: 0 }}
                />
                <span style={{ color: checked[action] ? "#69F0AE" : "#B8D4E8", textDecoration: checked[action] ? "line-through" : "none" }}>
                  {action}
                </span>
              </label>
            )) : <p style={{ color: "#90A4AE" }}>No preparedness actions available.</p>}
          </div>
        </div>

        {/* Emergency contacts */}
        <div>
          <div className="section-header">☎️ Emergency Contacts</div>
          <div className="card">
            {EMERGENCY_CONTACTS.map((c) => (
              <div key={c.name} style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, borderBottom: "1px solid #2A4A6A", paddingBottom: 8 }}>
                <strong>{c.name}</strong>
                <code style={{ color: "#64B5F6", fontSize: "1em" }}>{c.number}</code>
              </div>
            ))}
          </div>

          <div className="section-header" style={{ marginTop: 12 }}>🌐 Official Sources</div>
          <div className="card">
            {[
              { name: "IMD India", url: "https://mausam.imd.gov.in" },
              { name: "NDMA India", url: "https://ndma.gov.in" },
              { name: "INCOIS", url: "https://incois.gov.in" },
            ].map((s) => (
              <p key={s.name} style={{ marginBottom: 6 }}>
                — <a href={s.url} target="_blank" rel="noreferrer">{s.name}</a>
              </p>
            ))}
          </div>
        </div>
      </div>

      <div className="disclaimer" style={{ marginTop: 20 }}>
        ⚠️ <strong>IMPORTANT DISCLAIMER:</strong> This AI system provides decision-support only.
        It does NOT issue official government warnings. Always follow official IMD bulletins.
        Contact IMD at <strong>1800-180-1717</strong> for verified cyclone information.
      </div>

      <p style={{ marginTop: 10, fontSize: "0.82em", color: "#7A9BB5" }}>
        Data source: {(impact.data_source as string) ?? "sample"} |
        Confidence: {(confidence * 100).toFixed(0)}%
      </p>
    </div>
  );
}
