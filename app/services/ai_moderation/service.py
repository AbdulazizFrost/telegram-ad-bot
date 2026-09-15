import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai_moderation_log import AIModerationLog
from app.services.ai_moderation.base import BaseAIProvider, AIContentInput, AIClassificationResult
from app.services.ai_moderation.cache import ai_cache
from app.services.ai_moderation.limiter import ai_rate_limiter
from app.services.ai_moderation.factory import create_ai_provider

logger = logging.getLogger(__name__)


class AIModerationService:
    """
    Tier 2 AI Moderation Service.
    Orchestrates provider selection, caching, rate limiting, and database logging.
    """

    def __init__(self, provider: Optional[BaseAIProvider] = None):
        self._custom_provider = provider
        self.limiter = ai_rate_limiter

    def get_provider(self) -> BaseAIProvider:
        if self._custom_provider is not None:
            return self._custom_provider
        return create_ai_provider()

    def set_provider(self, provider: Optional[BaseAIProvider]):
        """Override provider (e.g. for unit tests with MockAIProvider)."""
        self._custom_provider = provider

    async def evaluate_message(
        self,
        text: str,
        chat_id: int,
        message_id: int,
        media_type: str = "text",
        ocr_text: Optional[str] = None,
        session: Optional[AsyncSession] = None,
        metadata: Optional[dict] = None,
    ) -> AIClassificationResult:
        """
        Run Tier 2 AI evaluation on suspicious message.
        Checks cache -> rate-limited execution -> updates cache -> logs to DB.
        """
        provider = self.get_provider()
        provider_name = getattr(provider, "__class__", type(provider)).__name__
        model_name = getattr(provider, "model", settings.AI_MODEL)

        # 1. Cache lookup (only for text-only messages to avoid caching huge images)
        cached = ai_cache.get(text, provider_name, model_name) if text and not (metadata and metadata.get("image_bytes")) else None
        if cached is not None:
            logger.debug(f"AI Cache Hit for message {message_id} in {chat_id}: {cached.classification} ({cached.confidence:.2f})")
            return cached

        # 2. Execute via rate limiter
        content = AIContentInput(
            text=text,
            chat_id=chat_id,
            message_id=message_id,
            media_type=media_type,
            ocr_text=ocr_text,
            metadata=metadata,
        )

        result = await ai_rate_limiter.execute_with_protection(provider, content)

        # 3. Cache successful results
        if not result.error:
            ai_cache.set(text, provider_name, model_name, result, ttl=settings.AI_CACHE_TTL)

        return result

    async def record_log(
        self,
        session: AsyncSession,
        chat_id: int,
        message_id: int,
        result: AIClassificationResult,
        was_deleted: bool,
    ) -> None:
        """Persist AI moderation record into ai_moderation_logs table."""
        try:
            log_entry = AIModerationLog(
                chat_id=chat_id,
                message_id=message_id,
                classification=result.classification,
                confidence=result.confidence,
                category=result.category,
                reason=result.reason,
                response_time_ms=result.response_time_ms,
                was_deleted=was_deleted,
                error=result.error,
            )
            session.add(log_entry)
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to record AI moderation log: {e}", exc_info=True)


# Global service instance
ai_moderation_service = AIModerationService()
