import time
import asyncio
import logging
from typing import Optional, List
from collections import deque
from app.config import settings
from app.services.ai_moderation.base import BaseAIProvider, AIContentInput, AIClassificationResult

logger = logging.getLogger(__name__)


class AIRateLimiter:
    """
    Sliding window rate limiter and concurrency semaphore for AI requests.
    Prevents API quota exhaustion and manages exponential backoff on 429s.
    """

    def __init__(self, max_rpm: int = 12, max_concurrent: int = 3):
        self.max_rpm = max_rpm
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._request_timestamps: deque = deque()
        self._lock = asyncio.Lock()

    def update_limits(self, max_rpm: Optional[int] = None, max_concurrent: Optional[int] = None):
        """Dynamically update limits if config changes."""
        if max_rpm is not None:
            self.max_rpm = max_rpm
        if max_concurrent is not None and max_concurrent != self.max_concurrent:
            self.max_concurrent = max_concurrent
            self._semaphore = asyncio.Semaphore(max_concurrent)

    async def _wait_for_rate_slot(self) -> bool:
        """
        Check and wait if necessary to respect the sliding-window rate limit.
        Returns True if a slot was secured, or False if queue is too saturated.
        """
        async with self._lock:
            now = time.monotonic()
            window_start = now - 60.0

            # Prune timestamps older than 60 seconds
            while self._request_timestamps and self._request_timestamps[0] < window_start:
                self._request_timestamps.popleft()

            if len(self._request_timestamps) >= self.max_rpm:
                # Calculate sleep duration to next available slot
                oldest = self._request_timestamps[0]
                wait_time = (oldest + 60.0) - now
                if wait_time > 5.0:
                    # Don't wait too long for Telegram chat messages; drop to UNCERTAIN fallback
                    logger.warning(
                        f"AI Rate limit saturated ({len(self._request_timestamps)}/{self.max_rpm} RPM). "
                        f"Wait time {wait_time:.1f}s exceeds threshold; escalating to UNCERTAIN."
                    )
                    return False
                if wait_time > 0:
                    logger.debug(f"Rate limiter pacing: sleeping {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)

            self._request_timestamps.append(time.monotonic())
            return True

    async def execute_with_protection(
        self,
        provider: BaseAIProvider,
        content: AIContentInput,
        max_retries: int = 2,
    ) -> AIClassificationResult:
        """
        Execute AI request under concurrency semaphore, rate limiting, and exponential backoff retry.
        """
        slot_ok = await self._wait_for_rate_slot()
        if not slot_ok:
            return AIClassificationResult(
                classification="UNCERTAIN",
                confidence=0.0,
                category="uncertain",
                reason="Rate limit saturated",
                error="RATE_LIMIT_QUEUE_EXCEEDED",
            )

        attempt = 0
        backoff = 1.0

        while attempt <= max_retries:
            try:
                async with self._semaphore:
                    result = await provider.classify(content)

                # Check if rate-limited by upstream API (HTTP 429)
                if result.error == "HTTP_429_RATE_LIMIT" and attempt < max_retries:
                    attempt += 1
                    logger.warning(f"Upstream 429 received. Backing off for {backoff:.1f}s (attempt {attempt}/{max_retries})...")
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue

                return result

            except Exception as e:
                logger.error(f"Unexpected error executing AI request: {e}", exc_info=True)
                if attempt < max_retries:
                    attempt += 1
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue

                return AIClassificationResult(
                    classification="UNCERTAIN",
                    confidence=0.0,
                    category="uncertain",
                    reason="Execution failed after retries",
                    error=str(e),
                )

        return AIClassificationResult(
            classification="UNCERTAIN",
            confidence=0.0,
            category="uncertain",
            reason="Retries exhausted",
            error="RETRIES_EXHAUSTED",
        )


# Global limiter instance
ai_rate_limiter = AIRateLimiter(
    max_rpm=settings.AI_RATE_LIMIT_RPM,
    max_concurrent=settings.AI_MAX_CONCURRENT,
)
