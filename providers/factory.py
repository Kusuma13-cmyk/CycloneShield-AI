"""
CycloneShield AI — LLM Provider Factory
Selects and returns the IBM watsonx.ai provider based on environment configuration.
IBM watsonx.ai (Granite) is the only supported LLM provider.
"""
import os
from dotenv import load_dotenv
from providers.base import BaseLLMProvider

load_dotenv()


def get_provider(override: str = "") -> BaseLLMProvider:
    """
    Return an instantiated LLM provider.

    Priority:
    1. override parameter (if given and == "granite")
    2. IBM_GRANITE_API_KEY + IBM_GRANITE_PROJECT_ID env vars present
    3. Demo mode (fallback, always works)
    """
    from providers.demo_provider import DemoProvider

    choice = (override or os.getenv("PRIMARY_LLM_PROVIDER", "")).lower().strip()
    app_mode = os.getenv("APP_MODE", "").lower()

    if app_mode == "demo":
        return DemoProvider()

    # Explicit IBM granite choice
    if choice == "granite":
        key = os.getenv("IBM_GRANITE_API_KEY", "")
        pid = os.getenv("IBM_GRANITE_PROJECT_ID", "")
        if key and pid:
            from providers.granite import GraniteProvider
            return GraniteProvider(api_key=key, project_id=pid)

    # Auto-detect IBM credentials
    if os.getenv("IBM_GRANITE_API_KEY") and os.getenv("IBM_GRANITE_PROJECT_ID"):
        from providers.granite import GraniteProvider
        return GraniteProvider()

    # Fallback to demo
    return DemoProvider()


def get_all_available_providers() -> dict[str, BaseLLMProvider]:
    """Return dict of all providers that have credentials configured."""
    from providers.demo_provider import DemoProvider
    providers = {"demo": DemoProvider()}

    if os.getenv("IBM_GRANITE_API_KEY") and os.getenv("IBM_GRANITE_PROJECT_ID"):
        from providers.granite import GraniteProvider
        providers["granite"] = GraniteProvider()

    return providers
