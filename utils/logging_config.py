"""
CycloneShield AI — Logging Configuration
Provides structured, timestamped execution logs for all agents and tools.
"""
import logging
import json
import time
from datetime import datetime, timezone
from typing import Any, Optional
from pathlib import Path

# ── Execution log store (in-memory for session) ──────────────────────────────
_execution_log: list[dict] = []


def get_logger(name: str) -> logging.Logger:
    """Return a named logger with consistent formatting."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_agent_event(
    agent_name: str,
    event_type: str,          # "start" | "complete" | "error" | "tool_call"
    input_summary: str = "",
    output_summary: str = "",
    status: str = "ok",       # "ok" | "error" | "skipped"
    duration_ms: float = 0.0,
    error_msg: str = "",
    metadata: Optional[dict] = None,
) -> dict:
    """Record an agent execution event and return the entry."""
    entry = {
        "id": len(_execution_log) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent_name,
        "event": event_type,
        "input_summary": input_summary[:300] if input_summary else "",
        "output_summary": output_summary[:300] if output_summary else "",
        "status": status,
        "duration_ms": round(duration_ms, 1),
        "error": error_msg[:200] if error_msg else "",
        "metadata": metadata or {},
    }
    _execution_log.append(entry)
    logger = get_logger(agent_name)
    if status == "error":
        logger.error("%s | %s | %s", event_type, input_summary[:80], error_msg[:80])
    else:
        logger.info("%s | %s", event_type, output_summary[:80])
    return entry


def get_execution_log() -> list[dict]:
    """Return all logged events for the current session."""
    return list(_execution_log)


def clear_execution_log() -> None:
    """Clear the session log (called when starting a new analysis)."""
    _execution_log.clear()


class AgentTimer:
    """Context manager: measures elapsed time for an agent block."""
    def __init__(self, agent_name: str, step: str):
        self.agent_name = agent_name
        self.step = step
        self._start = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        log_agent_event(self.agent_name, "start", input_summary=self.step)
        return self

    def __exit__(self, exc_type, exc_val, _tb):
        elapsed = (time.perf_counter() - self._start) * 1000
        if exc_type:
            log_agent_event(
                self.agent_name, "error",
                status="error", duration_ms=elapsed,
                error_msg=str(exc_val)
            )
        else:
            log_agent_event(
                self.agent_name, "complete",
                status="ok", duration_ms=elapsed,
                output_summary=f"Completed in {elapsed:.0f} ms"
            )
        return False  # do not suppress exceptions
