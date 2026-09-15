import time
import hashlib
from typing import Dict, Tuple, Optional
from app.services.ai_moderation.base import AIClassificationResult
from app.services.moderation_filter.normalizer import full_normalize_text


class AICache:
    """
    In-memory LRU/TTL Cache for AI moderation decisions.
    Cache key incorporates: normalized_text + provider + model (as required by specifications).
    Bounded to MAX_ENTRIES to preserve 512MB RAM ceiling on Render.
    """

    MAX_ENTRIES = 5000

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        # key_hash -> (AIClassificationResult, expire_at)
        self._cache: Dict[str, Tuple[AIClassificationResult, float]] = {}

    def _make_key(self, text: str, provider: str, model: str) -> str:
        norm = full_normalize_text(text or "").strip()
        raw_key = f"{provider}:{model}:{norm}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(self, text: str, provider: str, model: str) -> Optional[AIClassificationResult]:
        """Look up cached classification if not expired."""
        key = self._make_key(text, provider, model)
        item = self._cache.get(key)
        if not item:
            return None

        result, expire_at = item
        if time.monotonic() > expire_at:
            self._cache.pop(key, None)
            return None

        return result

    def set(
        self,
        text: str,
        provider: str,
        model: str,
        result: AIClassificationResult,
        ttl: Optional[int] = None,
    ) -> None:
        """Store classification result in cache."""
        # Evict oldest 20% if capacity exceeded
        if len(self._cache) >= self.MAX_ENTRIES:
            keys_to_remove = list(self._cache.keys())[: (self.MAX_ENTRIES // 5)]
            for k in keys_to_remove:
                self._cache.pop(k, None)

        effective_ttl = ttl if ttl is not None else self.default_ttl
        key = self._make_key(text, provider, model)
        self._cache[key] = (result, time.monotonic() + effective_ttl)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)


# Global singleton cache instance
ai_cache = AICache()
