"use client";
import type { AnalysisSession } from "../../lib/api";
import { useState } from "react";
import { submitReview } from "../../lib/api";

interface Props {
  session: AnalysisSession | null;
  onUpdate: (updated: Partial<AnalysisSession>) => void;
}

export default function HumanVerificationPage({ session, onUpdate }: Props) {
  const [reviewer, setReviewer] = useState("");
  const [decision, setDecision] = useState<"approved" | "rejected">("approved");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [reviewResult, setReviewResult] = useState<Record<string, string> | null>(null);

  if (!session) {
    return (
      <div>
        <div className="section-header">✅ Human Verification</div>
        <div className="info-box">Run the analysis first to enable human review.</div>
      </div>
    );
  }

  const reviewStatus = reviewResult?.human_review_status ?? session.human_review_status ?? "pending";
  const statusColor = reviewStatus === "approved" ? "#00C853" :
                      reviewStatus === "rejected" ? "#FF5252" : "#FFC400";

  const impact = (session.impact_result?.output ?? {}) as Record<string, unknown>;
  const cyclone = (session.cyclone_result?.output ?? {}) as Record<string, unknown>;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!reviewer.trim()) { setSubmitError("Please enter your name/role."); return; }
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await submitReview({
        session_data: session!,
        decision,
        reviewer: reviewer.trim(),
        notes,
      });
      setReviewResult(result as Record<string, string>);
      onUpdate({
        human_review_status: result.human_review_status as "approved" | "rejected",
        status: result.status as AnalysisSession["status"],
      });
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div className="section-header">✅ Human Verification</div>

      <div className="info-box" style={{ marginBottom: 16 }}>
        <strong>Why Human Verification?</strong> AI agents provide decision support only. Before
        any alert is marked <em>verified</em>, a human operator must review the AI outputs and
        approve or reject them. This prevents automated false alarms and ensures accountability.
      </div>

      {/* Review status */}
      <div className="card" style={{ borderColor: statusColor, background: `${statusColor}11`, marginBottom: 16 }}>
        <strong>Review Status: </strong>
        <span style={{ color: statusColor, fontWeight: 700 }}>{reviewStatus.toUpperCase()}</span>
        {reviewResult?.human_reviewer && (
          <span style={{ marginLeft: 12, color: "#90A4AE" }}>
            | Reviewer: {reviewResult.human_reviewer}
          </span>
        )}
        {reviewResult?.review_timestamp && (
          <span style={{ marginLeft: 12, color: "#90A4AE" }}>
            | {reviewResult.review_timestamp.slice(0, 19)} UTC
          </span>
        )}
      </div>

      {reviewStatus === "pending" ? (
        <>
          {/* Summary for review */}
          <div className="section-header">Analysis Summary for Review</div>
          <div className="grid-2">
            <div className="card">
              <p>Storm: <strong>{(cyclone.storm_name as string) ?? "?"}</strong></p>
              <p>Intensity: <strong>{(cyclone.current_intensity as string) ?? "?"}</strong></p>
              <p>Wind Speed: <strong>{(cyclone.wind_speed_kmh as number) ?? "?"} km/h</strong></p>
            </div>
            <div className="card">
              <p>Risk Level: <strong>{(impact.overall_risk_level as string) ?? "?"}</strong></p>
              <p>Alert Level (AI): <strong>{(impact.recommended_alert_level as string) || "Unknown"}</strong></p>
              <p>Provider: <strong>{session.provider_name}</strong> (demo={String(session.provider_name === "demo")})</p>
            </div>
          </div>

          <div className="demo-banner" style={{ marginTop: 12 }}>
            ⚠️ This is AI-generated analysis based on{" "}
            <strong>{session.data_mode === "sample" ? "SAMPLE" : "LIVE"}</strong> data.
            Verify against official IMD sources before taking any action.
          </div>

          {/* Review form */}
          <div className="section-header" style={{ marginTop: 16 }}>Submit Review Decision</div>
          <form onSubmit={handleSubmit} className="card" style={{ maxWidth: 520 }}>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", marginBottom: 4, fontWeight: 600 }}>
                Your Name / Role *
              </label>
              <input
                type="text"
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                placeholder="e.g., Duty Officer, SDMA"
                style={{ width: "100%", background: "#1E2A3A", color: "#E8F4F8",
                         border: "1px solid #2A4A6A", borderRadius: 4, padding: "8px 12px" }}
              />
            </div>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", marginBottom: 4, fontWeight: 600 }}>Decision</label>
              <div style={{ display: "flex", gap: 16 }}>
                {(["approved", "rejected"] as const).map((d) => (
                  <label key={d} style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
                    <input type="radio" name="decision" value={d} checked={decision === d}
                           onChange={() => setDecision(d)}
                           style={{ accentColor: d === "approved" ? "#00C853" : "#FF5252" }} />
                    <span style={{ color: d === "approved" ? "#00C853" : "#FF5252", fontWeight: 600 }}>
                      {d.charAt(0).toUpperCase() + d.slice(1)}
                    </span>
                  </label>
                ))}
              </div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: "block", marginBottom: 4, fontWeight: 600 }}>
                Notes / Observations
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add any notes about this analysis..."
                rows={3}
                style={{ width: "100%", background: "#1E2A3A", color: "#E8F4F8",
                         border: "1px solid #2A4A6A", borderRadius: 4, padding: "8px 12px",
                         resize: "vertical" }}
              />
            </div>
            {submitError && <div className="error-box" style={{ marginBottom: 12 }}>❌ {submitError}</div>}
            <button
              type="submit"
              className="btn-primary"
              disabled={submitting}
              style={{ width: "100%" }}
            >
              {submitting ? "⏳ Submitting..." : "Submit Review"}
            </button>
          </form>
        </>
      ) : (
        <div className="card">
          <p style={{ color: "#00C853", fontWeight: 700 }}>
            ✅ Review completed: <strong>{reviewStatus.toUpperCase()}</strong>
          </p>
          {reviewResult?.human_reviewer && (
            <p style={{ marginTop: 6, color: "#90A4AE" }}>By: {reviewResult.human_reviewer}</p>
          )}
          {notes && <p style={{ marginTop: 6, color: "#90A4AE" }}>Notes: {notes}</p>}
        </div>
      )}
    </div>
  );
}
