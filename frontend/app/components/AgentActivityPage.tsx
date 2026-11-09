"use client";
import type { AnalysisSession, LogEntry } from "../../lib/api";
import { useState } from "react";

interface Props { session: AnalysisSession | null; }

const AGENT_SHORT: Record<string, string> = {
  "Weather Intelligence Agent": "Weather",
  "Cyclone Detection & Tracking Agent": "Cyclone",
  "Impact Assessment & Early Warning Agent": "Impact",
  "CycloneShield Coordinator": "Coordinator",
  "Human Review": "Human Review",
};

export default function AgentActivityPage({ session }: Props) {
  const [filterAgent, setFilterAgent] = useState("All");

  if (!session) {
    return (
      <div>
        <div className="section-header">🤖 Multi-Agent Activity</div>
        <div className="info-box">Run the analysis first to see agent activity.</div>
      </div>
    );
  }

  const log: LogEntry[] = session.execution_log ?? [];
  const agentNames = ["All", ...Array.from(new Set(log.map((e) => e.agent).filter(Boolean)))];
  const filtered = filterAgent === "All" ? log : log.filter((e) => e.agent === filterAgent);

  const agentCards = [
    "Weather Intelligence Agent",
    "Cyclone Detection & Tracking Agent",
    "Impact Assessment & Early Warning Agent",
    "CycloneShield Coordinator",
  ];

  return (
    <div>
      <div className="section-header">🤖 Multi-Agent Activity Monitor</div>

      {/* Agent summary cards */}
      <div className="card-grid">
        {agentCards.map((agent) => {
          const events = log.filter((e) => e.agent === agent);
          const statusEvents = events.filter((e) => ["complete", "error"].includes(e.event));
          const status = statusEvents.length > 0 ? statusEvents[statusEvents.length - 1].status : "ok";
          const duration = events.filter((e) => e.event === "complete")
                                 .reduce((s, e) => s + (e.duration_ms ?? 0), 0);
          const color = status === "ok" ? "#00C853" : "#FF5252";
          return (
            <div key={agent} className="card" style={{ textAlign: "center", borderColor: color }}>
              <p style={{ fontSize: "0.75em", color: "#aab", marginBottom: 4 }}>
                {AGENT_SHORT[agent] ?? agent}
              </p>
              <p style={{ fontWeight: 700, color }}>{status === "ok" ? "✓ OK" : "✗ ERROR"}</p>
              <p style={{ fontSize: "0.82em", color: "#7AB" }}>{duration.toFixed(0)} ms</p>
            </div>
          );
        })}
      </div>

      {/* Execution log */}
      <div className="section-header" style={{ marginTop: 20 }}>📜 Execution Log</div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
        <select
          value={filterAgent}
          onChange={(e) => setFilterAgent(e.target.value)}
          style={{ background: "#1E2A3A", color: "#E8F4F8", border: "1px solid #2A4A6A",
                   borderRadius: 4, padding: "5px 10px", fontSize: "0.85em" }}
        >
          {agentNames.map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
      </div>

      <div>
        {[...filtered].reverse().slice(0, 50).map((entry) => {
          const color = entry.status === "ok" ? "#00C853" : entry.status === "error" ? "#FF5252" : "#FFC400";
          const ts = entry.timestamp?.slice(0, 19) ?? "";
          const summary = entry.output_summary || entry.input_summary || "";
          return (
            <div key={entry.id} className="log-entry" style={{ borderLeftColor: color }}>
              <span style={{ color: "#7AB" }}>[{ts}]</span>{" "}
              <strong style={{ color }}>{(entry.agent ?? "?").slice(0, 30)}</strong>{" "}
              — {entry.event}
              {summary ? ` | ${summary.slice(0, 100)}` : ""}
              {entry.duration_ms ? ` | ⏱ ${entry.duration_ms.toFixed(0)}ms` : ""}
              {entry.error ? <span style={{ color: "#FF5252" }}> | ❌ {entry.error.slice(0, 60)}</span> : null}
            </div>
          );
        })}
        {filtered.length === 0 && (
          <p style={{ color: "#90A4AE" }}>No log entries for this filter.</p>
        )}
      </div>

      {/* Communication diagram */}
      <details style={{ marginTop: 20 }}>
        <summary style={{ cursor: "pointer", color: "#64B5F6", fontWeight: 600 }}>🔗 Agent Communication Flow</summary>
        <pre style={{ marginTop: 8 }}>{`
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
        `}</pre>
      </details>
    </div>
  );
}
