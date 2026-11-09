"use client";
import type { AnalysisSession } from "../../lib/api";

interface Props { session: AnalysisSession | null; }

export default function ModelEvalPage({ session }: Props) {
  if (!session || !session.llm_eval) {
    return (
      <div>
        <div className="section-header">📈 Model Evaluation</div>
        <div className="info-box">Run the analysis first to see evaluation metrics.</div>
      </div>
    );
  }

  const ev = session.llm_eval;
  const perAgent = ev.per_agent ?? {};

  return (
    <div>
      <div className="section-header">📈 Model Evaluation</div>

      <div className="info-box" style={{ marginBottom: 16 }}>
        Evaluation measures <strong>structure accuracy</strong> (did the LLM return valid JSON?),{" "}
        <strong>output completeness</strong> (required fields present?), <strong>speed</strong>{" "}
        (end-to-end latency), and <strong>estimated cost</strong> (token pricing where available).
        <br /><em>No fabricated accuracy metrics — these are objective, measurable properties.</em>
      </div>

      <div className="card-grid">
        {[
          { label: "Total Latency", value: `${ev.total_latency_ms.toFixed(0)} ms` },
          { label: "Total Tokens", value: String(ev.total_tokens) },
          { label: "Est. Cost", value: `$${ev.total_cost_usd.toFixed(6)}` },
          { label: "JSON Validity", value: `${(ev.json_validity_score * 100).toFixed(0)}%` },
          { label: "Completeness", value: `${(ev.output_completeness_score * 100).toFixed(0)}%` },
        ].map((m) => (
          <div key={m.label} className="metric-card">
            <div className="metric-label">{m.label}</div>
            <div className="metric-value" style={{ fontSize: "1.3em" }}>{m.value}</div>
          </div>
        ))}
      </div>

      <div className="card" style={{ marginTop: 8 }}>
        <p><strong>Provider(s):</strong> {ev.providers_used?.join(", ") ?? "?"}</p>
        <p><strong>Model(s):</strong> {ev.models_used?.join(", ") ?? "?"}</p>
      </div>

      {/* Per-agent breakdown */}
      <div className="section-header" style={{ marginTop: 20 }}>Per-Agent Breakdown</div>
      {Object.keys(perAgent).length > 0 ? (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table>
            <thead>
              <tr><th>Agent</th><th>Latency (ms)</th><th>Tokens</th><th>Provider</th></tr>
            </thead>
            <tbody>
              {Object.entries(perAgent).map(([name, data]) => (
                <tr key={name}>
                  <td>{name.replace("_", " ").charAt(0).toUpperCase() + name.replace("_", " ").slice(1)}</td>
                  <td>{(data.latency_ms ?? 0).toFixed(1)}</td>
                  <td>{data.tokens ?? 0}</td>
                  <td>{data.provider ?? "?"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p style={{ color: "#90A4AE" }}>No per-agent data available.</p>
      )}

      {/* Provider comparison */}
      <div className="section-header" style={{ marginTop: 20 }}>Multi-Provider Comparison</div>
      <div className="card" style={{ color: "#90A4AE" }}>
        {session.provider_name === "demo"
          ? "Demo mode active. Configure IBM_GRANITE_API_KEY in .env to enable provider comparison."
          : "Live provider active. Configure additional API keys to enable head-to-head comparison."}
      </div>

      {ev.note && (
        <p style={{ marginTop: 12, fontSize: "0.82em", color: "#7A9BB5" }}>{ev.note}</p>
      )}
    </div>
  );
}
