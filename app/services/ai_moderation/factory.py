import logging
from typing import Optional
from app.config import settings
from app.services.ai_moderation.base import BaseAIProvider
from app.services.ai_moderation.gemini_provider import GeminiProvider
from app.services.ai_moderation.groq_provider import GroqProvider
from app.services.ai_moderation.mock_provider import MockAIProvider

logger = logging.getLogger(__name__)

# Global singleton mock provider for test suites
_GLOBAL_MOCK_PROVIDER: Optional[MockAIProvider] = None


def get_global_mock_provider() -> MockAIProvider:
    global _GLOBAL_MOCK_PROVIDER
    if _GLOBAL_MOCK_PROVIDER is None:
        _GLOBAL_MOCK_PROVIDER = MockAIProvider()
    return _GLOBAL_MOCK_PROVIDER


def create_ai_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
) -> BaseAIProvider:
    """
    Factory creating configured BaseAIProvider instance.
    Defaults to settings from app.config.
    """
    prov = (provider_name or settings.AI_PROVIDER).lower().strip()
    key = api_key if api_key is not None else settings.AI_API_KEY
    mdl = model or settings.AI_MODEL
    tm = timeout if timeout is not None else settings.AI_TIMEOUT

    if prov == "mock":
        return get_global_mock_provider()
    elif prov == "groq":
        return GroqProvider(api_key=key, model=mdl, timeout=tm)
    elif prov in ("gemini", "google"):
        return GeminiProvider(api_key=key, model=mdl, timeout=tm)
    else:
        logger.warning(f"Unknown AI provider '{prov}', falling back to GeminiProvider")
        return GeminiProvider(api_key=key, model=mdl, timeout=tm)
