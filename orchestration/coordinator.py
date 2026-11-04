"""
CycloneShield AI — Central Coordinator / Orchestrator
Sequential pipeline: Weather → Cyclone → Impact → Human Review

Architecture:
    WeatherAgent → CycloneAgent → ImpactAgent → Human Verification → Dashboard

Each agent receives the output of the previous one as input.
The coordinator maintains session memory and full execution log.
"""
import json
import time
from datetime import datetime, timezone
from typing import Optional, Callable
from dataclasses import dataclass, field

from providers.factory import get_provider
from providers.base import BaseLLMProvider
from agents.weather_agent import run_weather_agent
from agents.cyclone_agent import run_cyclone_agent
from agents.impact_agent import run_impact_agent
from utils.logging_config import (
    log_agent_event, get_execution_log, clear_execution_log, get_logger
)
from tools.weather_tools import load_sample_weather_data, load_live_weather_data
from tools.cyclone_tools import load_sample_track_data

logger = get_logger("Coordinator")

COORDINATOR_NAME = "CycloneShield Coordinator"


@dataclass
class AnalysisSession:
    """Holds the complete state of one analysis run (session memory)."""
    session_id: str = ""
    start_time: str = ""
    end_time: str = ""
    status: str = "idle"           # idle | running | complete | error | awaiting_review

    # Agent outputs
    weather_result: dict = field(default_factory=dict)
    cyclone_result: dict = field(default_factory=dict)
    impact_result: dict = field(default_factory=dict)

    # Human review
    human_review_status: str = "pending"  # pending | approved | rejected
    human_reviewer: str = ""
    human_notes: str = ""
    review_timestamp: str = ""

    # Meta
    provider_name: str = "demo"
    data_mode: str = "sample"      # sample | live
    location: str = "Bay of Bengal"
    total_duration_ms: float = 0.0
    errors: list = field(default_factory=list)
    execution_log: list = field(default_factory=list)

    # LLM Evaluation
    llm_eval: dict = field(default_factory=dict)


# Module-level session (persists across Streamlit reruns via st.session_state)
_current_session: Optional[AnalysisSession] = None


def get_current_session() -> Optional[AnalysisSession]:
    return _current_session


def run_full_analysis(
    location: str = "Bay of Bengal coastal India",
    provider_override: str = "",
    data_mode: str = "sample",
    use_live_weather: bool = False,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> AnalysisSession:
    """
    Run the full sequential agent pipeline.

    Args:
        location: Geographic region to analyze.
        provider_override: Force a specific LLM provider (groq/gemini/granite/demo).
        data_mode: "sample" or "live".
        use_live_weather: If True, attempt live weather API call.
        progress_callback: Optional fn(message, progress_0_to_1) for UI updates.

    Returns:
        Completed AnalysisSession.
    """
    global _current_session

    clear_execution_log()
    session = AnalysisSession(
        session_id=f"CS-{int(time.time())}",
        start_time=datetime.now(timezone.utc).isoformat(),
        status="running",
        location=location,
        data_mode=data_mode,
    )
    _current_session = session

    def progress(msg: str, pct: float):
        log_agent_event(COORDINATOR_NAME, "progress", input_summary=msg, metadata={"pct": pct})
        if progress_callback:
            progress_callback(msg, pct)

    total_start = time.perf_counter()

    try:
        # ── Get LLM Provider ─────────────────────────────────────────────────
        progress("Initializing LLM provider...", 0.05)
        provider: BaseLLMProvider = get_provider(provider_override)
        session.provider_name = provider.provider_name
        log_agent_event(
            COORDINATOR_NAME, "tool_call",
            input_summary=f"Provider selected: {provider.provider_name} ({provider.model_name})"
        )

        # ── Load Weather Data ────────────────────────────────────────────────
        progress("Loading weather data...", 0.10)
        if use_live_weather:
            weather_data = load_live_weather_data(location)
            if not weather_data:
                log_agent_event(COORDINATOR_NAME, "tool_call",
                                input_summary="Live data unavailable — falling back to sample")
                weather_data = load_sample_weather_data()
                session.data_mode = "sample"
        else:
            weather_data = load_sample_weather_data()
            session.data_mode = "sample"

        log_agent_event(
            COORDINATOR_NAME, "tool_call",
            input_summary=f"Loaded {len(weather_data)} weather readings (mode: {session.data_mode})"
        )

        # ── Agent 1: Weather Intelligence ────────────────────────────────────
        progress("Agent 1: Weather Intelligence analyzing...", 0.20)
        weather_result = run_weather_agent(weather_data, provider, location)
        session.weather_result = weather_result

        if weather_result["status"] == "error":
            session.errors.append(f"Weather Agent: {weather_result.get('output', {}).get('error', 'Unknown error')}")
            # Continue pipeline with partial data

        progress(f"Weather Agent complete ✓ | Rec: {weather_result.get('output', {}).get('recommendation', '?')}", 0.40)

        # ── Load Track Data ──────────────────────────────────────────────────
        progress("Loading cyclone track data...", 0.45)
        track_data = load_sample_track_data()
        log_agent_event(
            COORDINATOR_NAME, "tool_call",
            input_summary=f"Loaded {len(track_data)} cyclone track points"
        )

        # ── Agent 2: Cyclone Detection & Tracking ────────────────────────────
        progress("Agent 2: Cyclone Detection analyzing...", 0.50)
        cyclone_result = run_cyclone_agent(
            weather_result.get("output", {}),
            track_data,
            provider,
        )
        session.cyclone_result = cyclone_result

        if cyclone_result["status"] == "error":
            session.errors.append(f"Cyclone Agent: {cyclone_result.get('output', {}).get('error', 'Unknown')}")

        progress(f"Cyclone Agent complete ✓ | Intensity: {cyclone_result.get('output', {}).get('current_intensity', '?')}", 0.70)

        # ── Agent 3: Impact Assessment ───────────────────────────────────────
        progress("Agent 3: Impact Assessment analyzing...", 0.75)
        impact_result = run_impact_agent(
            cyclone_result.get("output", {}),
            weather_result.get("output", {}),
            provider,
            target_region=location,
        )
        session.impact_result = impact_result

        if impact_result["status"] == "error":
            session.errors.append(f"Impact Agent: {impact_result.get('output', {}).get('error', 'Unknown')}")

        progress(f"Impact Agent complete ✓ | Risk: {impact_result.get('output', {}).get('overall_risk_level', '?')}", 0.90)

        # ── LLM Evaluation ───────────────────────────────────────────────────
        session.llm_eval = _compute_llm_eval(weather_result, cyclone_result, impact_result)

        # ── Session Complete ─────────────────────────────────────────────────
        session.status = "awaiting_review"
        session.human_review_status = "pending"
        session.end_time = datetime.now(timezone.utc).isoformat()
        session.total_duration_ms = (time.perf_counter() - total_start) * 1000
        session.execution_log = get_execution_log()

        progress(f"Analysis complete — awaiting human review", 1.0)
        log_agent_event(
            COORDINATOR_NAME, "complete",
            output_summary=f"Pipeline complete in {session.total_duration_ms:.0f} ms",
            status="ok", duration_ms=session.total_duration_ms
        )

    except Exception as e:
        session.status = "error"
        session.errors.append(f"Coordinator exception: {str(e)}")
        session.end_time = datetime.now(timezone.utc).isoformat()
        session.total_duration_ms = (time.perf_counter() - total_start) * 1000
        session.execution_log = get_execution_log()
        logger.exception("Coordinator pipeline failed: %s", e)
        log_agent_event(COORDINATOR_NAME, "error", status="error", error_msg=str(e))

    return session


def submit_human_review(
    session: AnalysisSession,
    decision: str,
    reviewer: str = "Operator",
    notes: str = "",
) -> AnalysisSession:
    """
    Record a human review decision.

    Args:
        session: The AnalysisSession to update.
        decision: "approved" or "rejected".
        reviewer: Name/role of reviewer.
        notes: Optional notes.

    Returns:
        Updated session.
    """
    if decision not in ("approved", "rejected"):
        raise ValueError("decision must be 'approved' or 'rejected'")

    session.human_review_status = decision
    session.human_reviewer = reviewer
    session.human_notes = notes
    session.review_timestamp = datetime.now(timezone.utc).isoformat()
    session.status = "complete" if decision == "approved" else "rejected"

    log_agent_event(
        "Human Review", "complete",
        input_summary=f"Reviewer: {reviewer}",
        output_summary=f"Decision: {decision} | Notes: {notes[:80]}",
        status="ok"
    )
    # Update session log
    session.execution_log = get_execution_log()
    return session


def _compute_llm_eval(
    weather_r: dict,
    cyclone_r: dict,
    impact_r: dict,
) -> dict:
    """Compute LLM evaluation metrics from agent responses."""
    agents = [weather_r, cyclone_r, impact_r]
    total_latency = sum(a.get("duration_ms", 0) for a in agents)
    total_tokens = sum(a.get("llm_response_meta", {}).get("tokens", 0) for a in agents)
    total_cost = sum(a.get("llm_response_meta", {}).get("cost_usd", 0) for a in agents)
    providers_used = list({a.get("llm_response_meta", {}).get("provider", "demo") for a in agents})
    models_used = list({a.get("llm_response_meta", {}).get("model", "demo") for a in agents})

    # JSON validity score (0–1): did each agent return valid parseable JSON?
    json_scores = []
    for a in agents:
        output = a.get("output", {})
        json_scores.append(1.0 if isinstance(output, dict) and len(output) > 3 else 0.0)
    json_score = sum(json_scores) / len(json_scores) if json_scores else 0.0

    # Completeness score: required keys present
    weather_keys = ["analysis_summary", "recommendation", "confidence"]
    cyclone_keys = ["cyclone_detected", "current_intensity", "confidence"]
    impact_keys = ["overall_risk_level", "preparedness_actions", "official_warning_note"]
    completeness_scores = []
    for a, keys in [(weather_r, weather_keys), (cyclone_r, cyclone_keys), (impact_r, impact_keys)]:
        out = a.get("output", {})
        completeness_scores.append(sum(1 for k in keys if k in out) / len(keys))
    completeness = sum(completeness_scores) / len(completeness_scores)

    return {
        "total_latency_ms": round(total_latency, 1),
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "providers_used": providers_used,
        "models_used": models_used,
        "json_validity_score": round(json_score, 2),
        "output_completeness_score": round(completeness, 2),
        "per_agent": {
            "weather": {
                "latency_ms": weather_r.get("duration_ms", 0),
                "tokens": weather_r.get("llm_response_meta", {}).get("tokens", 0),
                "provider": weather_r.get("llm_response_meta", {}).get("provider", "?"),
            },
            "cyclone": {
                "latency_ms": cyclone_r.get("duration_ms", 0),
                "tokens": cyclone_r.get("llm_response_meta", {}).get("tokens", 0),
                "provider": cyclone_r.get("llm_response_meta", {}).get("provider", "?"),
            },
            "impact": {
                "latency_ms": impact_r.get("duration_ms", 0),
                "tokens": impact_r.get("llm_response_meta", {}).get("tokens", 0),
                "provider": impact_r.get("llm_response_meta", {}).get("provider", "?"),
            },
        },
        "note": "Accuracy measured by output structure and completeness. Speed by end-to-end latency. Cost by token pricing.",
    }
