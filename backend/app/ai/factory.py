"""Factory that instantiates the configured AI provider. This is the single place that reads
AI_PROVIDER -- callers should never branch on provider name themselves."""
from functools import lru_cache

from app.ai.base import AIProvider
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    provider = settings.AI_PROVIDER.lower()

    try:
        if provider == "openai":
            from app.ai.openai_provider import OpenAIProvider
            return OpenAIProvider()
        if provider == "anthropic":
            from app.ai.anthropic_provider import AnthropicProvider
            return AnthropicProvider()
        if provider == "gemini":
            from app.ai.gemini_provider import GeminiProvider
            return GeminiProvider()
        if provider == "local":
            from app.ai.local_provider import LocalLLMProvider
            return LocalLLMProvider()
        if provider == "mock":
            from app.ai.mock_provider import MockAIProvider
            return MockAIProvider()
    except Exception as exc:
        logger.error("Failed to initialize AI provider '%s': %s", provider, type(exc).__name__)

    from app.ai.none_provider import NoAIProvider
    return NoAIProvider()
