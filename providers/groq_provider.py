"""
CycloneShield AI — Groq LLM Provider
Uses groq Python SDK. Model: llama-3.3-70b-versatile (free tier available).
"""
import json
import os
from providers.base import BaseLLMProvider, LLMResponse
from utils.logging_config import get_logger

logger = get_logger("providers.groq")

# Groq pricing (as of 2024): llama-3.3-70b ~$0.59/1M input, $0.79/1M output tokens
GROQ_PRICING = {
    "llama-3.3-70b-versatile": {"input": 0.59e-6, "output": 0.79e-6},
    "llama-3.1-8b-instant":    {"input": 0.05e-6, "output": 0.08e-6},
    "mixtral-8x7b-32768":      {"input": 0.24e-6, "output": 0.24e-6},
}


class GroqProvider(BaseLLMProvider):
    """Groq inference provider using llama-3.3-70b-versatile."""

    provider_name = "groq"
    model_name = "llama-3.3-70b-versatile"

    def __init__(self, api_key: str = "", model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model_name = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("groq package not installed. Run: pip install groq")
        return self._client

    def complete(self, prompt: str, system_prompt: str = "", max_tokens: int = 1024) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(
                text="", model=self.model_name, provider=self.provider_name,
                error="GROQ_API_KEY not configured"
            )
        try:
            client = self._get_client()
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            def _call():
                return client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.1,
                )

            result, elapsed = self._timed_complete(_call)
            text = result.choices[0].message.content or ""
            usage = result.usage
            pt = usage.prompt_tokens if usage else 0
            ct = usage.completion_tokens if usage else 0

            pricing = GROQ_PRICING.get(self.model_name, {"input": 0, "output": 0})
            cost = pt * pricing["input"] + ct * pricing["output"]

            return LLMResponse(
                text=text,
                model=self.model_name,
                provider=self.provider_name,
                prompt_tokens=pt,
                completion_tokens=ct,
                total_tokens=pt + ct,
                latency_ms=elapsed,
                estimated_cost_usd=cost,
                raw={"id": result.id},
            )
        except Exception as e:
            logger.error("Groq API error: %s", e)
            return LLMResponse(
                text="", model=self.model_name, provider=self.provider_name,
                error=str(e)
            )
