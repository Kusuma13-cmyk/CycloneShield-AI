"use client";
import type { AnalysisSession } from "../../lib/api";

interface Props { session: AnalysisSession | null; }

export default function CycloneDetectionPage({ session }: Props) {
  if (!session) {
    return (
      <div>
        <div className="section-header">🌀 Cyclone Detection</div>
        <div className="info-box">Run the analysis first.</div>
      </div>
    );
  }

  const out = (session.cyclone_result?.output ?? {}) as Record<string, unknown>;
  if (!out || Object.keys(out).length === 0) {
    return (
      <div>
        <div className="section-header">🌀 Cyclone Detection</div>
        <div className="error-box">Cyclone agent produced no output.</div>
      </div>
    );
  }

  const detected = out.cyclone_detected as boolean;
  const pos = (out.current_position as { latitude: number | null; longitude: number | null }) ?? {};
  const lp = out.landfall_probability as string;
  const lpColor: Record<string, string> = { High: "#FF1744", Moderate: "#FF6D00", Low: "#00C853" };
  const confidence = (out.confidence as number) ?? 0;
  const cat = out.saffir_simpson_category as number | null;

  return (
    <div>
      <div className="section-header">🌀 Cyclone Detection</div>
      {(session.provider_name === "demo" || session.data_mode === "sample") && (
        <div className="demo-banner">
          ⚠️ <strong>DEMO / SAMPLE DATA</strong> — This cyclone detection output is based on
          synthetic test data. It is <strong>not</strong> a real cyclone observation or official
          IMD bulletin.
        </div>
      )}

      {detected ? (
        <div className="alert-banner" style={{ borderColor: "#FF1744", background: "#FF174418", marginBottom: 12 }}>
          <strong style={{ color: "#FF1744", fontSize: "1.1em" }}>
            🚨 CYCLONE DETECTED: {out.storm_name as string}
          </strong>
        </div>
      ) : (
        <div className="alert-banner" style={{ borderColor: "#00C853", background: "#00C85318", marginBottom: 12 }}>
          <strong style={{ color: "#00C853" }}>✅ No active cyclone detected in available data.</strong>
        </div>
      )}

      <div className="card-grid">
        {[
          { label: "Intensity", value: out.current_intensity as string },
          { label: "Wind Speed", value: out.wind_speed_kmh != null ? `${out.wind_speed_kmh} km/h` : "?" },
          { label: "Pressure", value: out.pressure_hpa != null ? `${out.pressure_hpa} hPa` : "?" },
          { label: "Saffir-Simpson", value: cat ? `Category ${cat}` : "Below Cat 1" },
        ].map((m) => (
          <div key={m.label} className="metric-card">
            <div className="metric-label">{m.label}</div>
            <div className="metric-value" style={{ fontSize: "1.1em" }}>{m.value}</div>
          </div>
        ))}
      </div>

      <div className="grid-2" style={{ marginTop: 16 }}>
        <div className="card">
          <p style={{ fontWeight: 700, marginBottom: 8 }}>Detection Summary</p>
          <p style={{ color: "#90A4AE", marginBottom: 12 }}>{out.analysis_summary as string}</p>
          {pos.latitude != null && (
            <p><strong>Position:</strong> {pos.latitude}°N, {pos.longitude}°E</p>
          )}
          <p><strong>Movement:</strong> {out.movement_direction as string} at {typeof out.movement_speed_kmh === "number" || typeof out.movement_speed_kmh === "string" ? out.movement_speed_kmh : "?"} km/h</p>
          <p><strong>Intensity Trend:</strong> {out.intensity_trend as string}</p>
        </div>

        <div className="card">
          <p style={{ fontWeight: 700, marginBottom: 8 }}>Landfall Assessment</p>
          <div className="alert-banner" style={{
            borderColor: lpColor[lp] ?? "#607D8B",
            background: `${lpColor[lp] ?? "#607D8B"}18`,
            marginBottom: 8,
          }}>
            <strong style={{ color: lpColor[lp] ?? "#607D8B" }}>Probability: {lp}</strong>
          </div>
          <p><strong>Region:</strong> {out.landfall_region as string}</p>
          <p><strong>Est. Time:</strong> {out.landfall_time_est as string}</p>
          <p><strong>Confidence:</strong> {(confidence * 100).toFixed(0)}%</p>
          <p style={{ marginTop: 6, fontSize: "0.82em", color: "#90A4AE" }}>
            ⚠️ Uncertainty: {out.uncertainty as string}
          </p>
        </div>
      </div>

      <details style={{ marginTop: 16 }}>
        <summary style={{ cursor: "pointer", color: "#64B5F6", fontWeight: 600 }}>Raw Cyclone Agent JSON</summary>
        <pre style={{ marginTop: 8 }}>{JSON.stringify(out, null, 2)}</pre>
      </details>
    </div>
  );
}
