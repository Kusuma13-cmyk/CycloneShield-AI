"""
CycloneShield AI — LLM Provider Factory
Selects and returns the appropriate provider based on environment configuration.
"""
import os
from dotenv import load_dotenv
from providers.base import BaseLLMProvider

load_dotenv()


def get_provider(override: str = "") -> BaseLLMProvider:
    """
    Return an instantiated LLM provider.

    Priority:
    1. override parameter (if given)
    2. PRIMARY_LLM_PROVIDER env var
    3. First available key (groq > gemini > granite)
    4. Demo mode (fallback, always works)
    """
    from providers.demo_provider import DemoProvider

    choice = (override or os.getenv("PRIMARY_LLM_PROVIDER", "")).lower().strip()
    app_mode = os.getenv("APP_MODE", "").lower()

    if app_mode == "demo":
        return DemoProvider()

    # Explicit choice
    if choice == "groq":
        key = os.getenv("GROQ_API_KEY", "")
        if key:
            from providers.groq_provider import GroqProvider
            return GroqProvider(api_key=key)
    elif choice == "gemini":
        key = os.getenv("GEMINI_API_KEY", "")
        if key:
            from providers.gemini_provider import GeminiProvider
            return GeminiProvider(api_key=key)
    elif choice == "granite":
        key = os.getenv("IBM_GRANITE_API_KEY", "")
        pid = os.getenv("IBM_GRANITE_PROJECT_ID", "")
        if key and pid:
            from providers.granite import GraniteProvider
            return GraniteProvider(api_key=key, project_id=pid)

    # Auto-detect first available
    if os.getenv("GROQ_API_KEY"):
        from providers.groq_provider import GroqProvider
        return GroqProvider()
    if os.getenv("GEMINI_API_KEY"):
        from providers.gemini_provider import GeminiProvider
        return GeminiProvider()
    if os.getenv("IBM_GRANITE_API_KEY") and os.getenv("IBM_GRANITE_PROJECT_ID"):
        from providers.granite import GraniteProvider
        return GraniteProvider()

    # Fallback to demo
    return DemoProvider()


def get_all_available_providers() -> dict[str, BaseLLMProvider]:
    """Return dict of all providers that have credentials configured."""
    from providers.demo_provider import DemoProvider
    providers = {"demo": DemoProvider()}

    if os.getenv("GROQ_API_KEY"):
        from providers.groq_provider import GroqProvider
        providers["groq"] = GroqProvider()
    if os.getenv("GEMINI_API_KEY"):
        from providers.gemini_provider import GeminiProvider
        providers["gemini"] = GeminiProvider()
    if os.getenv("IBM_GRANITE_API_KEY") and os.getenv("IBM_GRANITE_PROJECT_ID"):
        from providers.granite import GraniteProvider
        providers["granite"] = GraniteProvider()

    return providers
