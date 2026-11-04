"""
CycloneShield AI — IBM Watsonx / Granite Provider
Uses ibm-watsonx-ai SDK with granite-3-8b-instruct model.
"""
import os
from providers.base import BaseLLMProvider, LLMResponse
from utils.logging_config import get_logger

logger = get_logger("providers.granite")

IBM_PRICING = {
    "ibm/granite-3-8b-instruct":   {"input": 0.15e-6, "output": 0.60e-6},
    "ibm/granite-3-2b-instruct":   {"input": 0.05e-6, "output": 0.20e-6},
    "ibm/granite-13b-instruct-v2": {"input": 0.30e-6, "output": 0.90e-6},
}


class GraniteProvider(BaseLLMProvider):
    """IBM Watsonx Granite provider."""

    provider_name = "granite"
    model_name = "ibm/granite-3-8b-instruct"

    def __init__(
        self,
        api_key: str = "",
        project_id: str = "",
        url: str = "",
        model: str = "ibm/granite-3-8b-instruct",
    ):
        self.api_key = api_key or os.getenv("IBM_GRANITE_API_KEY", "")
        self.project_id = project_id or os.getenv("IBM_GRANITE_PROJECT_ID", "")
        self.url = url or os.getenv("IBM_GRANITE_URL", "https://us-south.ml.cloud.ibm.com")
        self.model_name = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from ibm_watsonx_ai import APIClient, Credentials
                credentials = Credentials(url=self.url, api_key=self.api_key)
                self._client = APIClient(credentials)
            except ImportError:
                raise RuntimeError("ibm-watsonx-ai not installed. Run: pip install ibm-watsonx-ai")
        return self._client

    def complete(self, prompt: str, system_prompt: str = "", max_tokens: int = 1024) -> LLMResponse:
        if not self.api_key or not self.project_id:
            return LLMResponse(
                text="", model=self.model_name, provider=self.provider_name,
                error="IBM_GRANITE_API_KEY or IBM_GRANITE_PROJECT_ID not configured"
            )
        try:
            from ibm_watsonx_ai.foundation_models import ModelInference
            from ibm_watsonx_ai import Credentials

            credentials = Credentials(url=self.url, api_key=self.api_key)

            def _call():
                model = ModelInference(
                    model_id=self.model_name,
                    credentials=credentials,
                    project_id=self.project_id,
                )
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                return model.generate_text(
                    prompt=full_prompt,
                    params={"max_new_tokens": max_tokens, "temperature": 0.1}
                )

            result, elapsed = self._timed_complete(_call)
            text = result if isinstance(result, str) else str(result)
            # Token counts not always available in basic generate_text
            est_tokens = len(prompt.split()) + len(text.split())
            pricing = IBM_PRICING.get(self.model_name, {"input": 0, "output": 0})
            cost = len(prompt.split()) * pricing["input"] + len(text.split()) * pricing["output"]

            return LLMResponse(
                text=text,
                model=self.model_name,
                provider=self.provider_name,
                prompt_tokens=len(prompt.split()),
                completion_tokens=len(text.split()),
                total_tokens=est_tokens,
                latency_ms=elapsed,
                estimated_cost_usd=cost,
            )
        except Exception as e:
            logger.error("IBM Granite API error: %s", e)
            return LLMResponse(
                text="", model=self.model_name, provider=self.provider_name,
                error=str(e)
            )
