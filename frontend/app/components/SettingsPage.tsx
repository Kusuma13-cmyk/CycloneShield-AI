"use client";
import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "../../lib/api";

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((e) => setHealthError(e.message));
  }, []);

  const granite = health?.providers.ibm_granite ?? false;
  const openweather = health?.providers.openweather ?? false;

  return (
    <div>
      <div className="section-header">⚙️ Settings &amp; API Configuration</div>

      {/* API key status from /api/health */}
      <div className="section-header">API Key Status</div>
      {healthError ? (
        <div className="error-box">Could not reach API: {healthError}</div>
      ) : health ? (
        <div className="card">
          <p style={{ marginBottom: 4 }}>
            <span style={{ color: granite ? "#00C853" : "#607D8B" }}>{granite ? "🟢" : "⚪"}</span>{" "}
            <strong>IBM watsonx.ai (Granite):</strong> {granite ? "Configured" : "Not configured"}
          </p>
          <p>
            <span style={{ color: openweather ? "#00C853" : "#607D8B" }}>{openweather ? "🟢" : "⚪"}</span>{" "}
            <strong>OpenWeatherMap:</strong> {openweather ? "Configured" : "Not configured"}
          </p>
          <p style={{ marginTop: 8, color: "#90A4AE", fontSize: "0.85em" }}>
            App Mode: <code>{health.mode}</code> | Version: {health.version}
          </p>
        </div>
      ) : (
        <div className="spinner-wrap"><div className="spinner" /><span>Checking API...</span></div>
      )}

      {/* Setup instructions */}
      <div className="section-header" style={{ marginTop: 20 }}>.env Setup Instructions</div>
      <div className="card">
        <p style={{ marginBottom: 8, color: "#90A4AE" }}>
          API keys are read from a <code>.env</code> file in the project root.
          <strong> Never commit .env to GitHub.</strong>
        </p>
        <pre>{`# 1. Copy the example file:
cp .env.example .env

# 2. Add your IBM watsonx.ai credentials:
IBM_GRANITE_API_KEY=your_ibm_api_key
IBM_GRANITE_PROJECT_ID=your_project_id
IBM_GRANITE_URL=https://us-south.ml.cloud.ibm.com

# 3. Set primary provider:
PRIMARY_LLM_PROVIDER=granite

# 4. For demo mode (no real API):
APP_MODE=demo`}</pre>
      </div>

      {/* Guardrails */}
      <div className="section-header" style={{ marginTop: 20 }}>Guardrails &amp; Security</div>
      <div className="card">
        {[
          "API keys stored in .env (never in code or frontend)",
          "Prompt injection detection (regex pattern matching)",
          "Input length limits (max 10,000 characters)",
          "Output JSON schema validation",
          "Human-in-the-loop approval before alert verification",
          "Demo mode clearly labelled — never disguised as real data",
          "AI never issues official government warnings",
          "All outputs include uncertainty and source information",
        ].map((g) => (
          <p key={g} style={{ marginBottom: 6 }}>✅ {g}</p>
        ))}
      </div>

      {/* Vercel env vars needed */}
      <div className="section-header" style={{ marginTop: 20 }}>Vercel Environment Variables</div>
      <div className="card">
        <p style={{ marginBottom: 8, color: "#90A4AE" }}>
          Set these in your Vercel project dashboard → Settings → Environment Variables:
        </p>
        <table>
          <thead>
            <tr><th>Variable</th><th>Required</th><th>Notes</th></tr>
          </thead>
          <tbody>
            {[
              ["APP_MODE", "No", "Set to 'demo' to run without any API key"],
              ["IBM_GRANITE_API_KEY", "No (demo)", "From IBM Cloud dashboard"],
              ["IBM_GRANITE_PROJECT_ID", "No (demo)", "Your watsonx project GUID"],
              ["IBM_GRANITE_URL", "No", "Default: https://us-south.ml.cloud.ibm.com"],
              ["PRIMARY_LLM_PROVIDER", "No", "Set to 'granite' when using IBM"],
              ["OPENWEATHER_API_KEY", "No", "For live weather data (optional)"],
            ].map(([k, r, n]) => (
              <tr key={k}><td><code>{k}</code></td><td>{r}</td><td style={{ color: "#90A4AE" }}>{n}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
