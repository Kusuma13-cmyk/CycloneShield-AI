"use client";
import type { AnalysisSession } from "../../lib/api";

const RISK_COLORS: Record<string, string> = {
  EXTREME: "#FF1744", "VERY HIGH": "#FF6D00", HIGH: "#FFC400",
  MODERATE: "#00BFA5", LOW: "#00B0FF", MINIMAL: "#69F0AE",
};
const ALERT_COLORS: Record<string, string> = {
  RED: "#FF1744", ORANGE: "#FF6D00", YELLOW: "#FFC400", GREEN: "#00C853",
};

interface Props { session: AnalysisSession | null; }

export default function ImpactPage({ session }: Props) {
  if (!session) {
    return (
      <div>
        <div className="section-header">⚠️ Impact Assessment</div>
        <div className="info-box">Run the analysis first.</div>
      </div>
    );
  }

  const out = (session.impact_result?.output ?? {}) as Record<string, unknown>;
  if (!out || Object.keys(out).length === 0) {
    return (
      <div>
        <div className="section-header">⚠️ Impact Assessment</div>
        <div className="error-box">Impact agent produced no output.</div>
      </div>
    );
  }

  const risk = (out.overall_risk_level as string) || "Unknown";
  const rawAlert = out.recommended_alert_level as string | undefined;
  const alert = rawAlert && ALERT_COLORS[rawAlert] ? rawAlert : null;
  const alertDisplay = alert ?? (rawAlert || "Unknown");
  const riskColor = RISK_COLORS[risk] ?? "#607D8B";
  const alertColor = alert ? (ALERT_COLORS[alert] ?? "#607D8B") : "#607D8B";
  const districts = (out.affected_districts as Array<Record<string, string>>) ?? [];
  const actions = (out.preparedness_actions as string[]) ?? [];
  const groups = (out.vulnerable_groups as string[]) ?? [];
  const infrastructure = (out.infrastructure_at_risk as string[]) ?? [];

  return (
    <div>
      <div className="section-header">⚠️ Impact Assessment</div>
      {(session.provider_name === "demo" || session.data_mode === "sample") && (
        <div className="demo-banner">
          ⚠️ <strong>DEMO / SAMPLE DATA</strong> — This impact assessment is based on synthetic
          test data. It is <strong>not</strong> a real assessment or official IMD advisory.
        </div>
      )}

      <div className="grid-2" style={{ alignItems: "start" }}>
        {/* Risk badge */}
        <div className="card" style={{
          borderColor: riskColor, background: `${riskColor}11`,
          textAlign: "center", padding: 24,
        }}>
          <p style={{ fontSize: "0.8em", color: "#aaa", marginBottom: 6 }}>OVERALL RISK</p>
          <p style={{ fontSize: "3em", fontWeight: 900, color: riskColor }}>{risk}</p>
          <div style={{
            background: alertColor, color: "#fff", borderRadius: 6,
            padding: "4px 16px", marginTop: 12, fontWeight: 700, display: "inline-block",
            fontSize: "0.85em",
          }}>
            {alertDisplay} ALERT (AI assessment)
          </div>
        </div>

        <div className="card">
          <p style={{ fontWeight: 700, marginBottom: 6 }}>Risk Justification</p>
          <p style={{ color: "#90A4AE", marginBottom: 12 }}>{out.risk_justification as string}</p>
          <p style={{ fontWeight: 700, marginBottom: 6 }}>Summary</p>
          <p style={{ color: "#90A4AE" }}>{out.analysis_summary as string}</p>
        </div>
      </div>

      <div className="grid-2" style={{ marginTop: 16 }}>
        {/* Districts */}
        <div>
          <div className="section-header">Affected Districts</div>
          {districts.length > 0 ? (
            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              <table>
                <thead>
                  <tr><th>District</th><th>State</th><th>Risk</th><th>Population at Risk</th></tr>
                </thead>
                <tbody>
                  {districts.map((d, i) => (
                    <tr key={i}>
                      <td>{d.district}</td><td>{d.state}</td>
                      <td>
                        <span style={{
                          background: `${RISK_COLORS[d.risk] ?? "#607D8B"}33`,
                          color: RISK_COLORS[d.risk] ?? "#E8F4F8",
                          padding: "2px 8px", borderRadius: 4, fontSize: "0.82em",
                        }}>
                          {d.risk}
                        </span>
                      </td>
                      <td>{d.population_at_risk}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p className="card" style={{ color: "#90A4AE" }}>No district data available.</p>}

          <div className="section-header" style={{ marginTop: 16 }}>Hazard Estimates</div>
          <div className="card">
            <p>🌊 <strong>Storm Surge:</strong> {out.storm_surge_estimate_m as string}</p>
            <p style={{ marginTop: 6 }}>🌧️ <strong>Rainfall:</strong> {out.rainfall_forecast_mm as string}</p>
            <p style={{ marginTop: 6 }}>💨 <strong>Wind Damage:</strong> {out.wind_damage_potential as string}</p>
          </div>
        </div>

        {/* Actions */}
        <div>
          <div className="section-header">Preparedness Actions</div>
          <div className="card">
            <ol style={{ paddingLeft: 18 }}>
              {actions.map((a, i) => <li key={i} style={{ marginBottom: 6, color: "#B8D4E8" }}>{a}</li>)}
            </ol>
          </div>

          {groups.length > 0 && (
            <>
              <div className="section-header" style={{ marginTop: 12 }}>Vulnerable Groups</div>
              <div className="card" style={{ color: "#90A4AE" }}>{groups.join(", ")}</div>
            </>
          )}

          {infrastructure.length > 0 && (
            <>
              <div className="section-header" style={{ marginTop: 12 }}>Infrastructure at Risk</div>
              <div className="card" style={{ color: "#90A4AE" }}>{infrastructure.join(", ")}</div>
            </>
          )}
        </div>
      </div>

      {/* Disclaimer — always prominent */}
      <div className="disclaimer" style={{ marginTop: 16 }}>
        {out.official_warning_note as string}
      </div>
      <p style={{ color: "#64B5F6", marginTop: 8 }}>📞 {out.imd_contact as string}</p>

      <details style={{ marginTop: 16 }}>
        <summary style={{ cursor: "pointer", color: "#64B5F6", fontWeight: 600 }}>Raw Impact Agent JSON</summary>
        <pre style={{ marginTop: 8 }}>{JSON.stringify(out, null, 2)}</pre>
      </details>
    </div>
  );
}
