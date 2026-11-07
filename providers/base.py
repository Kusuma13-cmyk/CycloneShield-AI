"""
CycloneShield AI — Base LLM Provider Interface
All provider implementations must subclass BaseLLMProvider.
"""
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    text: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    is_demo: bool = False
    error: str = ""
    raw: dict = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return bool(self.text) and not self.error


class BaseLLMProvider(ABC):
    """Abstract base for all LLM provider adapters."""

    provider_name: str = "base"
    model_name: str = "unknown"

    @abstractmethod
    def complete(self, prompt: str, system_prompt: str = "", max_tokens: int = 1024) -> LLMResponse:
        """
        Send a prompt and return a structured LLMResponse.
        Must never raise — return LLMResponse with error set instead.
        """
        ...

    def _timed_complete(self, fn, *args, **kwargs) -> tuple[any, float]:
        """Helper: call fn, return (result, elapsed_ms)."""
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        return result, elapsed
