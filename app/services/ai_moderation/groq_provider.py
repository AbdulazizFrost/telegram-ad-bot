import json
import time
import logging
import asyncio
from typing import Optional
import aiohttp

from app.services.ai_moderation.base import (
    BaseAIProvider,
    AIContentInput,
    AIClassificationResult,
    VALID_CLASSIFICATIONS,
    VALID_CATEGORIES,
)
from app.services.ai_moderation.prompt import SYSTEM_PROMPT, build_classification_prompt

logger = logging.getLogger(__name__)


class GroqProvider(BaseAIProvider):
    """
    OpenAI-compatible provider supporting Groq Cloud (e.g. llama-3.1-8b-instant, llama-3.3-70b-versatile).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.1-8b-instant",
        base_url: str = "https://api.groq.com/openai/v1",
        timeout: float = 8.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def classify(self, content: AIContentInput) -> AIClassificationResult:
        if not self.api_key:
            return AIClassificationResult(
                classification="UNCERTAIN",
                reason="Groq API key not configured",
                error="MISSING_API_KEY",
            )

        endpoint = f"{self.base_url}/chat/completions"
        user_prompt = build_classification_prompt(content.text)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "max_tokens": 300,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        t_start = time.perf_counter()
        try:
            client_timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=client_timeout) as session:
                async with session.post(endpoint, json=payload, headers=headers) as resp:
                    latency_ms = (time.perf_counter() - t_start) * 1000.0

                    if resp.status == 429:
                        return AIClassificationResult(
                            classification="UNCERTAIN",
                            reason="Rate limit exceeded",
                            response_time_ms=latency_ms,
                            error="HTTP_429_RATE_LIMIT",
                        )

                    if resp.status != 200:
                        error_body = await resp.text()
                        safe_error = error_body.replace(self.api_key, "[REDACTED_API_KEY]")
                        logger.error(f"Groq API error HTTP {resp.status}: {safe_error[:300]}")
                        return AIClassificationResult(
                            classification="UNCERTAIN",
                            reason="API request failed",
                            response_time_ms=latency_ms,
                            error=f"HTTP_{resp.status}",
                        )

                    data = await resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        return AIClassificationResult(
                            classification="UNCERTAIN",
                            response_time_ms=latency_ms,
                            error="NO_CHOICES",
                        )

                    raw_text = choices[0].get("message", {}).get("content", "").strip()
                    parsed = json.loads(raw_text)

                    classification = str(parsed.get("classification", "UNCERTAIN")).upper().strip()
                    if classification not in VALID_CLASSIFICATIONS:
                        classification = "UNCERTAIN"

                    try:
                        confidence = float(parsed.get("confidence", 0.0))
                        confidence = max(0.0, min(1.0, confidence))
                    except (ValueError, TypeError):
                        confidence = 0.0

                    category = str(parsed.get("category", "uncertain")).lower().strip()
                    if category not in VALID_CATEGORIES:
                        category = "other"

                    reason = str(parsed.get("reason", ""))

                    return AIClassificationResult(
                        classification=classification,
                        confidence=confidence,
                        category=category,
                        reason=reason,
                        response_time_ms=latency_ms,
                        raw_response=raw_text,
                    )

        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - t_start) * 1000.0
            return AIClassificationResult(
                classification="UNCERTAIN",
                reason="Request timed out",
                response_time_ms=latency_ms,
                error="TIMEOUT",
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - t_start) * 1000.0
            logger.error(f"Groq provider error: {e}", exc_info=True)
            return AIClassificationResult(
                classification="UNCERTAIN",
                reason="Provider error",
                response_time_ms=latency_ms,
                error=str(e),
            )
