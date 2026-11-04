"""
CycloneShield AI — Google Gemini Provider
Uses google-generativeai SDK. Model: gemini-1.5-flash (free tier available).
"""
import os
from providers.base import BaseLLMProvider, LLMResponse
from utils.logging_config import get_logger

logger = get_logger("providers.gemini")

GEMINI_PRICING = {
    "gemini-1.5-flash": {"input": 0.075e-6, "output": 0.30e-6},
    "gemini-1.5-pro":   {"input": 1.25e-6,  "output": 5.00e-6},
    "gemini-2.0-flash": {"input": 0.075e-6, "output": 0.30e-6},
}


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider using google-generativeai SDK."""

    provider_name = "gemini"
    model_name = "gemini-1.5-flash"

    def __init__(self, api_key: str = "", model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel(self.model_name)
            except ImportError:
                raise RuntimeError("google-generativeai not installed. Run: pip install google-generativeai")
        return self._model

    def complete(self, prompt: str, system_prompt: str = "", max_tokens: int = 1024) -> LLMResponse:
        if not self.api_key:
            return LLMResponse(
                text="", model=self.model_name, provider=self.provider_name,
                error="GEMINI_API_KEY not configured"
            )
        try:
            model = self._get_model()
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

            def _call():
                return model.generate_content(
                    full_prompt,
                    generation_config={"max_output_tokens": max_tokens, "temperature": 0.1}
                )

            result, elapsed = self._timed_complete(_call)
            text = result.text or ""
            pt = getattr(result.usage_metadata, "prompt_token_count", 0) or 0
            ct = getattr(result.usage_metadata, "candidates_token_count", 0) or 0

            pricing = GEMINI_PRICING.get(self.model_name, {"input": 0, "output": 0})
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
            )
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            return LLMResponse(
                text="", model=self.model_name, provider=self.provider_name,
                error=str(e)
            )
