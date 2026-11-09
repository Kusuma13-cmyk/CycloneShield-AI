"""
CycloneShield AI — IBM watsonx.ai / Granite Provider
Target model: ibm/granite-4-h-small
SDK: ibm-watsonx-ai >= 1.9.1

ibm/granite-4-h-small is a CHAT model.  It must be called via
ModelInference.chat(messages=[...]) which returns:
  {
    "choices": [
      {
        "message": {"role": "assistant", "content": "<generated text>"},
        "finish_reason": "stop"
      }
    ],
    "usage": {
      "prompt_tokens": <int>,
      "completion_tokens": <int>,
      "total_tokens": <int>
    }
  }

Older text-generation models use ModelInference.generate_text() which returns:
  {"results": [{"generated_text": "...", "generated_tokens_count": <int>, ...}]}

We detect which path is needed by attempting chat() first.  If the model
raises (e.g. unsupported for text-gen), we fall back to generate_text().

SDK 1.9.1 compatibility notes
------------------------------
* ModelInference(validate=True) is the SDK default.  With validate=True the
  constructor immediately calls foundation_models.get_model_specs() over the
  network and raises WMLClientError if the model string is absent from the
  server's list.  ibm/granite-4-h-small may be absent from the static enum
  shipped with older SDK releases but IS available on the live watsonx.ai
  service.  We pass validate=False to skip the client-side allowlist check.
"""
import os
import time
from providers.base import BaseLLMProvider, LLMResponse
from utils.logging_config import get_logger

logger = get_logger("providers.granite")

# Exact model ID required by the task specification
GRANITE_MODEL_ID = "ibm/granite-4-h-small"

# Token pricing estimates (USD per token) — approximate
IBM_PRICING = {
    "ibm/granite-4-h-small":       {"input": 0.10e-6, "output": 0.40e-6},
    "ibm/granite-3-8b-instruct":   {"input": 0.15e-6, "output": 0.60e-6},
    "ibm/granite-3-2b-instruct":   {"input": 0.05e-6, "output": 0.20e-6},
    "ibm/granite-13b-instruct-v2": {"input": 0.30e-6, "output": 0.90e-6},
}

# Known errors and user-friendly translations
_IBM_ERROR_MAP = {
    "401": "Invalid API key (HTTP 401). Check IBM_GRANITE_API_KEY in .env.",
    "403": "Access denied (HTTP 403). Verify IBM_GRANITE_PROJECT_ID and watsonx.ai access.",
    "404": "Model not found (HTTP 404). Verify model ID is ibm/granite-4-h-small and your account has access.",
    "429": "Rate limit exceeded (HTTP 429). Reduce request frequency or upgrade your IBM plan.",
    "500": "IBM watsonx.ai internal server error (HTTP 500). Retry later.",
    "503": "IBM watsonx.ai service unavailable (HTTP 503). Retry later.",
    "TIMEOUT": "Request timed out connecting to IBM watsonx.ai. Check network and IBM_GRANITE_URL.",
    "CONNECTION": "Cannot connect to IBM watsonx.ai. Check network connectivity and IBM_GRANITE_URL.",
    "NO_MODULE": "ibm-watsonx-ai SDK not installed. Run: pip install ibm-watsonx-ai>=1.9.1",
    "NO_KEY": "IBM_GRANITE_API_KEY not configured. Set it in .env (see .env.example).",
    "NO_PROJECT": "IBM_GRANITE_PROJECT_ID not configured. Set it in .env (see .env.example).",
    "STALE": "watsonx.ai response was empty or unparseable.",
    "MODEL_NOT_SUPPORTED": (
        "Model ibm/granite-4-h-small is not in the server-side model list for your "
        "watsonx.ai instance. Ensure your IBM Cloud account has access to this model "
        "at https://us-south.ml.cloud.ibm.com and that IBM_GRANITE_URL is correct."
    ),
}


class GraniteProvider(BaseLLMProvider):
    """
    IBM watsonx.ai Granite provider.

    Uses ibm-watsonx-ai SDK with ModelInference.
    Model: ibm/granite-4-h-small (exact ID required).

    ibm/granite-4-h-small is a chat model:
        - Primary path: ModelInference.chat(messages=[...])
        - Response: {"choices": [{"message": {"content": "..."}}], "usage": {...}}
    Fallback for older text-generation models:
        - ModelInference.generate_text(raw_response=True)
        - Response: {"results": [{"generated_text": "..."}]}

    Credentials are read from environment variables only — never hardcoded.
    All errors are returned in LLMResponse.error; no exceptions are raised.
    """

    provider_name = "granite"
    model_name = GRANITE_MODEL_ID

    def __init__(
        self,
        api_key: str | None = None,
        project_id: str | None = None,
        url: str | None = None,
        model: str | None = None,
    ):
        # Use explicit arg if provided (including explicit empty string), else fall back to env.
        # None means "not specified by caller → read from env".
        self.api_key = api_key if api_key is not None else os.getenv("IBM_GRANITE_API_KEY", "")
        self.project_id = project_id if project_id is not None else os.getenv("IBM_GRANITE_PROJECT_ID", "")
        self.url = url if url is not None else os.getenv("IBM_GRANITE_URL", "https://us-south.ml.cloud.ibm.com")
        self.model_name = model if model is not None else GRANITE_MODEL_ID

    def validate_credentials(self) -> tuple[bool, str]:
        """
        Check that required credentials are present (not empty strings).
        Does NOT make a network call — only checks for presence.
        Returns (ok, error_message).
        """
        if not self.api_key or self.api_key.strip() in ("", "your_ibm_api_key_here"):
            return False, _IBM_ERROR_MAP["NO_KEY"]
        if not self.project_id or self.project_id.strip() in ("", "your_ibm_project_id_here"):
            return False, _IBM_ERROR_MAP["NO_PROJECT"]
        return True, ""

    def complete(self, prompt: str, system_prompt: str = "", max_tokens: int = 1024) -> LLMResponse:
        """
        Call IBM watsonx.ai using the Chat API (required for ibm/granite-4-h-small).

        ibm/granite-4-h-small is a multimodal chat model.  We call
        ModelInference.chat(messages=[...]) with system + user messages.

        Chat response format:
          {
            "choices": [
              {"message": {"role": "assistant", "content": "<text>"}, "finish_reason": "stop"}
            ],
            "usage": {
              "prompt_tokens": <int>,
              "completion_tokens": <int>,
              "total_tokens": <int>
            }
          }

        If the model does not support the Chat API (older text-gen models),
        falls back to generate_text(raw_response=True) automatically.

        Returns LLMResponse with error set (and is_demo=False) on any failure.
        Never silently returns demo data — callers must check response.error.
        """
        # 1. Validate credentials before any network call
        creds_ok, creds_err = self.validate_credentials()
        if not creds_ok:
            logger.warning("Granite credentials missing: %s", creds_err)
            return LLMResponse(
                text="", model=self.model_name, provider=self.provider_name,
                error=creds_err, is_demo=False,
            )

        # 2. Import SDK — provide clear error if not installed
        try:
            from ibm_watsonx_ai import Credentials
            from ibm_watsonx_ai.foundation_models import ModelInference
            from ibm_watsonx_ai.foundation_models.schema import TextChatParameters
        except ImportError:
            return LLMResponse(
                text="", model=self.model_name, provider=self.provider_name,
                error=_IBM_ERROR_MAP["NO_MODULE"], is_demo=False,
            )

        # 3. Build credentials object
        try:
            credentials = Credentials(url=self.url, api_key=self.api_key)

            # validate=False: skip the client-side model-allowlist check.
            # The SDK's default (validate=True) calls get_model_specs() at
            # construction time and raises WMLClientError if the model string is
            # absent from the server's list — even when the model IS available
            # (e.g. newer models not yet in the SDK's static enum).  Passing
            # validate=False defers validation to the actual inference call.
            model_obj = ModelInference(
                model_id=self.model_name,
                credentials=credentials,
                project_id=self.project_id,
                validate=False,
            )
        except Exception as exc:
            err_str = str(exc)
            friendly = _translate_ibm_error(err_str)
            logger.error("IBM Granite credentials/init error: %s → %s", err_str[:200], friendly)
            return LLMResponse(
                text="", model=self.model_name, provider=self.provider_name,
                error=friendly, is_demo=False,
            )

        # 4. Call the Chat API (primary path for ibm/granite-4-h-small)
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            chat_params = TextChatParameters(
                temperature=0.1,
                max_tokens=max_tokens,
                repetition_penalty=1.1,
            )

            def _do_chat_call():
                return model_obj.chat(messages=messages, params=chat_params)

            raw, elapsed_ms = self._timed_complete(_do_chat_call)

            logger.info(
                "Granite chat() called: model=%s raw_type=%s latency=%.0fms",
                self.model_name, type(raw).__name__, elapsed_ms
            )

            text, prompt_tokens, completion_tokens = _parse_chat_response(raw)

            if not text.strip():
                logger.error(
                    "❌ Granite inference FAILED: model=%s reason=empty_response latency=%.0fms",
                    self.model_name, elapsed_ms
                )
                return LLMResponse(
                    text="", model=self.model_name, provider=self.provider_name,
                    error=_IBM_ERROR_MAP["STALE"], latency_ms=elapsed_ms, is_demo=False,
                )

            total_tokens = prompt_tokens + completion_tokens
            pricing = IBM_PRICING.get(self.model_name, {"input": 0.0, "output": 0.0})
            cost = prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]

            logger.info(
                "✅ Granite inference SUCCESS: model=%s prompt_tokens=%d completion_tokens=%d "
                "total_tokens=%d latency=%.0fms cost_usd=%.6f",
                self.model_name, prompt_tokens, completion_tokens, total_tokens, elapsed_ms, cost
            )

            return LLMResponse(
                text=text,
                model=self.model_name,
                provider=self.provider_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=elapsed_ms,
                estimated_cost_usd=cost,
                is_demo=False,
            )

        except Exception as exc:
            err_str = str(exc)
            # If chat() fails because this model doesn't support it, try text-gen fallback
            if _is_not_supported_error(err_str):
                logger.warning(
                    "Chat API not supported for %s — trying generate_text fallback: %s",
                    self.model_name, err_str[:100]
                )
                return self._complete_generate_text(model_obj, prompt, system_prompt, max_tokens)

            friendly = _translate_ibm_error(err_str)
            logger.error(
                "❌ Granite inference FAILED: model=%s error=%s friendly=%s",
                self.model_name, err_str[:200], friendly
            )
            return LLMResponse(
                text="", model=self.model_name, provider=self.provider_name,
                error=friendly, is_demo=False,
            )

    def _complete_generate_text(
        self,
        model_obj,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
    ) -> LLMResponse:
        """
        Fallback: use generate_text(raw_response=True) for older text-generation models.
        Response: {"results": [{"generated_text": "...", "generated_tokens_count": ..., "input_token_count": ...}]}
        """
        try:
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                full_prompt = prompt

            params = {
                "max_new_tokens": max_tokens,
                "temperature": 0.1,
                "repetition_penalty": 1.1,
            }

            def _do_generate():
                return model_obj.generate_text(prompt=full_prompt, params=params, raw_response=True)

            raw, elapsed_ms = self._timed_complete(_do_generate)
            text, prompt_tokens, completion_tokens = _parse_generate_response(raw)

            if not text.strip():
                return LLMResponse(
                    text="", model=self.model_name, provider=self.provider_name,
                    error=_IBM_ERROR_MAP["STALE"], latency_ms=elapsed_ms, is_demo=False,
                )

            total_tokens = prompt_tokens + completion_tokens
            pricing = IBM_PRICING.get(self.model_name, {"input": 0.0, "output": 0.0})
            cost = prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]

            return LLMResponse(
                text=text,
                model=self.model_name,
                provider=self.provider_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=elapsed_ms,
                estimated_cost_usd=cost,
                is_demo=False,
            )
        except Exception as exc:
            err_str = str(exc)
            friendly = _translate_ibm_error(err_str)
            logger.error("IBM Granite generate_text fallback error: %s → %s", err_str[:200], friendly)
            return LLMResponse(
                text="", model=self.model_name, provider=self.provider_name,
                error=friendly, is_demo=False,
            )


def _parse_chat_response(raw) -> tuple[str, int, int]:
    """
    Extract (content_text, prompt_tokens, completion_tokens) from the Chat API response.

    Chat response shape (SDK 1.9.1 / ibm/granite-4-h-small):
      {
        "choices": [
          {
            "message": {"role": "assistant", "content": "<text>"},
            "finish_reason": "stop"
          }
        ],
        "usage": {
          "prompt_tokens": <int>,
          "completion_tokens": <int>,
          "total_tokens": <int>
        }
      }

    Falls back gracefully if the structure differs.
    """
    if isinstance(raw, str):
        return raw, len(raw.split()), 0

    if isinstance(raw, dict):
        # Primary chat path
        choices = raw.get("choices", [])
        if choices and isinstance(choices, list):
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                message = first_choice.get("message", {})
                text = message.get("content", "") if isinstance(message, dict) else ""
            else:
                text = str(first_choice)

            usage = raw.get("usage", {})
            prompt_tokens = int(usage.get("prompt_tokens", len(text.split())))
            completion_tokens = int(usage.get("completion_tokens", len(text.split())))
            return text, prompt_tokens, completion_tokens

        # Some SDK versions wrap chat under a different key
        # Try the generate-style results key as a safety net
        results = raw.get("results", [])
        if results and isinstance(results, list):
            first = results[0]
            text = first.get("generated_text", "") if isinstance(first, dict) else str(first)
            prompt_tokens = int(first.get("input_token_count", len(text.split())))
            completion_tokens = int(first.get("generated_tokens_count", len(text.split())))
            return text, prompt_tokens, completion_tokens

        # Last resort: look for generated_text at top level
        text = raw.get("generated_text", str(raw))
        return text, len(text.split()), 0

    text = str(raw) if raw else ""
    return text, len(text.split()), 0


def _parse_generate_response(raw) -> tuple[str, int, int]:
    """
    Extract (text, prompt_tokens, completion_tokens) from generate_text(raw_response=True).

    Response shape:
      {
        "results": [
          {
            "generated_text": "...",
            "generated_tokens_count": <int>,
            "input_token_count": <int>
          }
        ]
      }
    """
    if isinstance(raw, str):
        return raw, len(raw.split()), 0

    if isinstance(raw, dict):
        results = raw.get("results", [])
        if results and isinstance(results, list):
            first = results[0]
            text = first.get("generated_text", "") if isinstance(first, dict) else str(first)
            prompt_tokens = int(first.get("input_token_count", len(text.split())))
            completion_tokens = int(first.get("generated_tokens_count", len(text.split())))
            return text, prompt_tokens, completion_tokens
        text = raw.get("generated_text", str(raw))
        return text, len(text.split()), 0

    text = str(raw) if raw else ""
    return text, len(text.split()), 0


def _is_not_supported_error(err_str: str) -> bool:
    """Return True if the error indicates the API type is not supported for this model."""
    lower = err_str.lower()
    return any(kw in lower for kw in (
        "not supported", "not available", "text generation is not supported",
        "chat is not supported", "generation is not supported"
    ))


def _translate_ibm_error(raw: str) -> str:
    """Map raw exception message to a friendly error string."""
    r = raw.lower()
    if "401" in r or "unauthorized" in r:
        return _IBM_ERROR_MAP["401"]
    if "403" in r or "forbidden" in r:
        return _IBM_ERROR_MAP["403"]
    if "404" in r or "not found" in r:
        return _IBM_ERROR_MAP["404"]
    if "429" in r or "rate limit" in r or "too many" in r:
        return _IBM_ERROR_MAP["429"]
    if "500" in r:
        return _IBM_ERROR_MAP["500"]
    if "503" in r or "unavailable" in r:
        return _IBM_ERROR_MAP["503"]
    if "timeout" in r or "timed out" in r:
        return _IBM_ERROR_MAP["TIMEOUT"]
    if "connectionerror" in r or "connection refused" in r or "failed to connect" in r:
        return _IBM_ERROR_MAP["CONNECTION"]
    # WMLClientError: model not in server-side supported list
    if "not supported for this environment" in r or "supported models" in r:
        return _IBM_ERROR_MAP["MODEL_NOT_SUPPORTED"]
    # Return sanitized version of raw error (max 200 chars, no key-like tokens)
    api_key = os.getenv("IBM_GRANITE_API_KEY", "")
    safe = raw[:200]
    if api_key:
        safe = safe.replace(api_key, "[REDACTED]")
    return f"IBM watsonx.ai error: {safe}"
