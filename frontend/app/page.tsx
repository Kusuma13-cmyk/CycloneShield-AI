"use client";
/**
 * CycloneShield AI — Main Dashboard
 * Client-side React app wrapping all dashboard pages.
 * Calls the Python API layer for all data.
 */
import { useState, useCallback } from "react";
import type { AnalysisSession } from "../lib/api";
import {
  runAnalysis,
  fetchWeather,
  fetchTrack,
  fetchHealth,
  submitReview,
} from "../lib/api";

// ── Sub-pages (lazy-ish via conditional render) ──────────────────────────────
import OverviewPage from "./components/OverviewPage";
import WeatherPage from "./components/WeatherPage";
import CycloneDetectionPage from "./components/CycloneDetectionPage";
import CycloneTrackPage from "./components/CycloneTrackPage";
import ImpactPage from "./components/ImpactPage";
import EarlyWarningPage from "./components/EarlyWarningPage";
import AgentActivityPage from "./components/AgentActivityPage";
import HumanVerificationPage from "./components/HumanVerificationPage";
import ModelEvalPage from "./components/ModelEvalPage";
import SettingsPage from "./components/SettingsPage";

type Page =
  | "Overview"
  | "Weather Intelligence"
  | "Cyclone Detection"
  | "Cyclone Tracking"
  | "Impact Assessment"
  | "Early Warning"
  | "Multi-Agent Activity"
  | "Human Verification"
  | "Model Evaluation"
  | "Settings";

const NAV_ITEMS: { icon: string; page: Page }[] = [
  { icon: "📊", page: "Overview" },
  { icon: "🌦️", page: "Weather Intelligence" },
  { icon: "🌀", page: "Cyclone Detection" },
  { icon: "🗺️", page: "Cyclone Tracking" },
  { icon: "⚠️", page: "Impact Assessment" },
  { icon: "🚨", page: "Early Warning" },
  { icon: "🤖", page: "Multi-Agent Activity" },
  { icon: "✅", page: "Human Verification" },
  { icon: "📈", page: "Model Evaluation" },
  { icon: "⚙️", page: "Settings" },
];

export default function Home() {
  const [currentPage, setCurrentPage] = useState<Page>("Overview");
  const [session, setSession] = useState<AnalysisSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [provider, setProvider] = useState<"demo" | "granite" | "">("demo");

  const handleRunAnalysis = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    setError(null);
    setLoadingMsg("Initializing CycloneShield AI pipeline...");

    try {
      setLoadingMsg("Running 3-agent pipeline (may take 15–30s)...");
      const result = await runAnalysis({
        provider_override: provider,
        location: "Odisha and Andhra Pradesh coast, Bay of Bengal",
      });
      setSession(result);
      setLoadingMsg("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }, [loading, provider]);

  const handleReviewUpdate = useCallback((updated: Partial<AnalysisSession>) => {
    if (!session) return;
    setSession({ ...session, ...updated });
  }, [session]);

  // Status info for sidebar
  const statusIcon = !session ? "⚪" :
    session.status === "complete" ? "🟢" :
    session.status === "awaiting_review" ? "🟡" :
    session.status === "error" ? "🔴" : "🔵";

  return (
    <div className="app-layout">
      {/* ── Sidebar ─────────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <h1>🌀 CycloneShield AI</h1>
          <p>Agentic Early Warning System</p>
        </div>

        <nav>
          {NAV_ITEMS.map(({ icon, page }) => (
            <button
              key={page}
              className={`nav-btn${currentPage === page ? " active" : ""}`}
              onClick={() => setCurrentPage(page)}
            >
              {icon} {page}
            </button>
          ))}
        </nav>

        <div className="sidebar-section" style={{ marginTop: "auto" }}>
          <h3>Quick Run</h3>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value as typeof provider)}
            style={{
              width: "100%", background: "#1E2A3A", color: "#E8F4F8",
              border: "1px solid #2A4A6A", borderRadius: 4, padding: "6px 8px",
              marginBottom: 8, fontSize: "0.85em",
            }}
          >
            <option value="demo">Demo (no API key)</option>
            <option value="granite">IBM Granite (live)</option>
            <option value="">Auto-detect</option>
          </select>
          <button
            className="btn-primary"
            style={{ width: "100%" }}
            onClick={handleRunAnalysis}
            disabled={loading}
          >
            {loading ? "⏳ Running..." : "🚀 Run Analysis"}
          </button>
        </div>

        <div className="sidebar-section" style={{ borderTop: "1px solid #2A4A6A", paddingTop: 12, marginTop: 12 }}>
          <p style={{ fontSize: "0.8em", color: "#90A4AE" }}>
            <strong>Status:</strong> {statusIcon} {session?.status?.replace("_", " ") ?? "Not started"}
          </p>
          {session && (
            <>
              <p style={{ fontSize: "0.78em", color: "#7A9BB5", marginTop: 4 }}>
                Provider: {session.provider_name}
              </p>
              <p style={{ fontSize: "0.78em", color: "#7A9BB5" }}>
                Session: {session.session_id}
              </p>
            </>
          )}
          <p style={{ fontSize: "0.72em", color: "#557", marginTop: 8 }}>
            CycloneShield AI v1.0
          </p>
        </div>
      </aside>

      {/* ── Main Content ─────────────────────────────────────── */}
      <main className="main-content">
        {/* Global loading bar */}
        {loading && (
          <div style={{ marginBottom: 16 }}>
            <div className="progress-outer">
              <div className="progress-inner" style={{ width: "60%" }} />
            </div>
            <p style={{ fontSize: "0.85em", color: "#90A4AE", marginTop: 4 }}>{loadingMsg}</p>
          </div>
        )}

        {/* Global error */}
        {error && (
          <div className="error-box" style={{ marginBottom: 16 }}>
            ❌ {error}
            <button
              onClick={() => setError(null)}
              style={{ marginLeft: 12, background: "transparent", color: "#ef9a9a",
                       fontSize: "0.9em", padding: "2px 8px" }}
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Page router */}
        {currentPage === "Overview" && (
          <OverviewPage session={session} onRunAnalysis={handleRunAnalysis} loading={loading} />
        )}
        {currentPage === "Weather Intelligence" && (
          <WeatherPage session={session} />
        )}
        {currentPage === "Cyclone Detection" && (
          <CycloneDetectionPage session={session} />
        )}
        {currentPage === "Cyclone Tracking" && (
          <CycloneTrackPage session={session} />
        )}
        {currentPage === "Impact Assessment" && (
          <ImpactPage session={session} />
        )}
        {currentPage === "Early Warning" && (
          <EarlyWarningPage session={session} />
        )}
        {currentPage === "Multi-Agent Activity" && (
          <AgentActivityPage session={session} />
        )}
        {currentPage === "Human Verification" && (
          <HumanVerificationPage session={session} onUpdate={handleReviewUpdate} />
        )}
        {currentPage === "Model Evaluation" && (
          <ModelEvalPage session={session} />
        )}
        {currentPage === "Settings" && (
          <SettingsPage />
        )}
      </main>
    </div>
  );
}
