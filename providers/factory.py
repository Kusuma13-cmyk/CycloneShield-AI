"""
CycloneShield AI — LLM Provider Factory
Selects and returns the IBM watsonx.ai provider based on environment configuration.

Priority logic:
1. If APP_MODE=demo → Demo (explicit user choice)
2. If PRIMARY_LLM_PROVIDER=granite (or IBM credentials present) AND APP_MODE != demo → Granite (live)
3. If APP_MODE=live but credentials are missing → error raised (no silent demo fallback)
4. Otherwise → Demo (fallback, always labeled)

NEVER silently return demo results when the user expects live AI (APP_MODE=live).
"""
import os
from dotenv import load_dotenv
from providers.base import BaseLLMProvider

load_dotenv()


def get_provider_mode() -> dict:
    """
    Determine the current operating mode without instantiating providers.

    Returns a dict with:
        mode: "live" | "demo"
        provider_name: "granite" | "demo"
        model_name: model ID string
        reason: human-readable explanation of why this mode was chosen
        credentials_present: bool
        credentials_valid: bool (True only if key+project look non-placeholder)
    """
    from providers.granite import GRANITE_MODEL_ID

    app_mode = os.getenv("APP_MODE", "").lower().strip()
    primary = os.getenv("PRIMARY_LLM_PROVIDER", "").lower().strip()
    api_key = os.getenv("IBM_GRANITE_API_KEY", "").strip()
    project_id = os.getenv("IBM_GRANITE_PROJECT_ID", "").strip()

    # Explicit demo override
    if app_mode == "demo":
        return {
            "mode": "demo",
            "provider_name": "demo",
            "model_name": "cycloneshield-demo-v1",
            "reason": "APP_MODE=demo set explicitly in .env",
            "credentials_present": bool(api_key and project_id),
            "credentials_valid": False,
        }

    # Check credential presence and plausibility
    placeholder_values = {"", "your_ibm_api_key_here", "your_ibm_project_id_here"}
    key_ok = bool(api_key) and api_key not in placeholder_values
    pid_ok = bool(project_id) and project_id not in placeholder_values

    if key_ok and pid_ok:
        return {
            "mode": "live",
            "provider_name": "granite",
            "model_name": GRANITE_MODEL_ID,
            "reason": "IBM credentials found in environment — Live AI mode active",
            "credentials_present": True,
            "credentials_valid": True,
        }

    # No valid credentials — differentiate between live-requested and auto-detect
    missing = []
    if not key_ok:
        missing.append("IBM_GRANITE_API_KEY")
    if not pid_ok:
        missing.append("IBM_GRANITE_PROJECT_ID")

    # APP_MODE=live was explicitly requested but credentials are absent —
    # report as misconfigured (no silent demo fallback when live is required).
    # PRIMARY_LLM_PROVIDER alone without APP_MODE=live does not force this path.
    if app_mode == "live":
        return {
            "mode": "misconfigured",
            "provider_name": "demo",
            "model_name": "cycloneshield-demo-v1",
            "reason": (
                f"APP_MODE=live requested but IBM credentials are missing: "
                f"{', '.join(missing)}. Set these in .env to enable Live AI."
            ),
            "credentials_present": False,
            "credentials_valid": False,
        }

    return {
        "mode": "demo",
        "provider_name": "demo",
        "model_name": "cycloneshield-demo-v1",
        "reason": f"Demo mode — missing credentials: {', '.join(missing)}. Configure .env to enable Live AI.",
        "credentials_present": False,
        "credentials_valid": False,
    }


def get_provider(override: str = "") -> BaseLLMProvider:
    """
    Return an instantiated LLM provider.

    Rules:
    - override="demo"              → always return DemoProvider (explicit test request)
    - override="granite"           → return GraniteProvider (errors propagate, no demo fallback)
    - APP_MODE=demo                → DemoProvider
    - PRIMARY_LLM_PROVIDER=granite → GraniteProvider (errors propagate, no demo fallback)
    - APP_MODE=live                → GraniteProvider (errors propagate, no demo fallback)
    - IBM creds present            → GraniteProvider (live)
    - otherwise                    → DemoProvider (clearly labeled)

    IMPORTANT: Never silently returns DemoProvider when APP_MODE=live or
    PRIMARY_LLM_PROVIDER=granite is configured — errors propagate clearly instead.
    """
    from providers.demo_provider import DemoProvider
    from providers.granite import GraniteProvider

    ov = override.lower().strip()
    app_mode = os.getenv("APP_MODE", "").lower().strip()
    primary = os.getenv("PRIMARY_LLM_PROVIDER", "").lower().strip()

    # Explicit override takes priority over everything
    if ov == "granite":
        # Return GraniteProvider even if creds missing — errors propagate clearly
        return GraniteProvider()

    if ov == "demo":
        return DemoProvider()

    # APP_MODE=demo (no explicit override)
    if app_mode == "demo":
        return DemoProvider()

    # APP_MODE=live → hard requirement: must use Granite (no silent demo fallback).
    # GraniteProvider validates credentials and returns LLMResponse.error if missing.
    if app_mode == "live":
        return GraniteProvider()

    # PRIMARY_LLM_PROVIDER=granite is a preference signal.
    # Auto-detect: use Granite if credentials are valid; prefer Granite if PRIMARY says so.
    info = get_provider_mode()
    if info["mode"] == "live":
        return GraniteProvider()
    if primary == "granite" and info.get("credentials_valid"):
        return GraniteProvider()

    # Fallback to demo with reason logged
    from utils.logging_config import get_logger
    logger = get_logger("providers.factory")
    logger.info("Provider fallback to demo: %s", info["reason"])
    return DemoProvider()


def get_all_available_providers() -> dict[str, BaseLLMProvider]:
    """Return dict of all providers that have credentials configured."""
    from providers.demo_provider import DemoProvider
    providers = {"demo": DemoProvider()}

    info = get_provider_mode()
    if info["credentials_valid"]:
        from providers.granite import GraniteProvider
        providers["granite"] = GraniteProvider()

    return providers
