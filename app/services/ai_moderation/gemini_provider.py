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
from app.services.ai_moderation.prompt import (
    SYSTEM_PROMPT,
    build_classification_prompt,
    build_multimodal_classification_prompt,
)

logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """
    Google Gemini Provider using official Google AI Studio REST API.
    Uses asynchronous HTTP with aiohttp (no heavy SDK dependency).
    """

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash", timeout: float = 8.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def classify(self, content: AIContentInput) -> AIClassificationResult:
        """Classify message via Gemini generateContent endpoint."""
        if not self.api_key:
            logger.warning("Gemini API key is not configured. Returning UNCERTAIN fallback.")
            return AIClassificationResult(
                classification="UNCERTAIN",
                confidence=0.0,
                category="uncertain",
                reason="Gemini API key not configured",
                error="MISSING_API_KEY",
            )

        model_name = self.model
        if model_name in ("gemini-2.5-flash", "gemini-2.5", "gemini-flash", ""):
            model_name = "gemini-1.5-flash"

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            f"?key={self.api_key}"
        )

        user_parts = []
        img_bytes = (content.metadata or {}).get("image_bytes") if content.metadata else None

        # Multimodal Vision support: if image bytes are present, pass to Gemini Vision
        if img_bytes:
            import base64
            # Determine MIME type from magic bytes
            mime = "image/jpeg"
            if img_bytes.startswith(b"\x89PNG"):
                mime = "image/png"
            elif img_bytes.startswith(b"RIFF") and b"WEBP" in img_bytes[:16]:
                mime = "image/webp"

            b64_str = base64.b64encode(img_bytes).decode("utf-8")
            user_parts.append({
                "inlineData": {
                    "mimeType": mime,
                    "data": b64_str
                }
            })
            user_prompt = build_multimodal_classification_prompt(content.text or "")
        else:
            user_prompt = build_classification_prompt(content.text or "")

        user_parts.append({"text": user_prompt})

        payload = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": user_parts
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
                "maxOutputTokens": 300,
            }
        }

        t_start = time.perf_counter()
        try:
            client_timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=client_timeout) as session:
                async with session.post(endpoint, json=payload) as resp:
                    latency_ms = (time.perf_counter() - t_start) * 1000.0

                    if resp.status == 429:
                        logger.warning(f"Gemini API returned 429 Too Many Requests (model: {model_name})")
                        return AIClassificationResult(
                            classification="UNCERTAIN",
                            confidence=0.0,
                            category="uncertain",
                            reason="Rate limit exceeded",
                            response_time_ms=latency_ms,
                            error="HTTP_429_RATE_LIMIT",
                        )

                    # Handle 404 model not found by falling back to gemini-1.5-flash
                    if resp.status == 404 and model_name != "gemini-1.5-flash":
                        logger.warning(f"Gemini model {model_name} returned 404, falling back to gemini-1.5-flash...")
                        fallback_url = (
                            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
                            f"?key={self.api_key}"
                        )
                        async with session.post(fallback_url, json=payload) as fb_resp:
                            if fb_resp.status == 200:
                                fb_data = await fb_resp.json()
                                return self._parse_gemini_response(fb_data, (time.perf_counter() - t_start) * 1000.0)

                    if resp.status != 200:
                        error_body = await resp.text()
                        # Ensure API key is never exposed in logs
                        safe_error = error_body.replace(self.api_key, "[REDACTED_API_KEY]")
                        logger.error(f"Gemini API returned HTTP {resp.status}: {safe_error[:300]}")
                        return AIClassificationResult(
                            classification="UNCERTAIN",
                            confidence=0.0,
                            category="uncertain",
                            reason="API request failed",
                            response_time_ms=latency_ms,
                            error=f"HTTP_{resp.status}",
                        )

                    data = await resp.json()
                    return self._parse_gemini_response(data, latency_ms)


        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - t_start) * 1000.0
            logger.warning(f"Gemini API request timed out after {self.timeout}s")
            return AIClassificationResult(
                classification="UNCERTAIN",
                confidence=0.0,
                category="uncertain",
                reason="Request timed out",
                response_time_ms=latency_ms,
                error="TIMEOUT",
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - t_start) * 1000.0
            logger.error(f"Gemini API unexpected connection error: {e}", exc_info=True)
            return AIClassificationResult(
                classification="UNCERTAIN",
                confidence=0.0,
                category="uncertain",
                reason="Connection error",
                response_time_ms=latency_ms,
                error=str(e),
            )

    def _parse_gemini_response(self, data: dict, latency_ms: float) -> AIClassificationResult:
        """Extract and validate structured JSON from Gemini response."""
        try:
            candidates = data.get("candidates", [])
            if not candidates:
                logger.warning("Gemini response contained no candidates")
                return AIClassificationResult(
                    classification="UNCERTAIN",
                    response_time_ms=latency_ms,
                    error="NO_CANDIDATES",
                )

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts or "text" not in parts[0]:
                return AIClassificationResult(
                    classification="UNCERTAIN",
                    response_time_ms=latency_ms,
                    error="EMPTY_CONTENT",
                )

            raw_text = parts[0]["text"].strip()

            # Strip markdown fences if present
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

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

        except json.JSONDecodeError as jde:
            logger.warning(f"Failed to parse Gemini response as JSON: {jde}")
            return AIClassificationResult(
                classification="UNCERTAIN",
                response_time_ms=latency_ms,
                error="MALFORMED_JSON",
            )
        except Exception as ex:
            logger.error(f"Error validating Gemini response structure: {ex}")
            return AIClassificationResult(
                classification="UNCERTAIN",
                response_time_ms=latency_ms,
                error=f"VALIDATION_ERROR: {ex}",
            )
