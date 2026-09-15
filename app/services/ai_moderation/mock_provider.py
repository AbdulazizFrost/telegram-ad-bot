import asyncio
from typing import Optional, List, Dict, Callable
from app.services.ai_moderation.base import BaseAIProvider, AIContentInput, AIClassificationResult


class MockAIProvider(BaseAIProvider):
    """
    Configurable Mock AI Provider for deterministic unit & stress testing.
    Supports preset responses, forced errors, latency simulation, and rule-based simulation.
    """

    def __init__(self):
        self._preset_responses: List[AIClassificationResult] = []
        self._custom_handler: Optional[Callable[[AIContentInput], AIClassificationResult]] = None
        self.call_count: int = 0
        self.last_input: Optional[AIContentInput] = None
        self.simulate_latency_ms: float = 10.0
        self.force_timeout: bool = False
        self.force_error: Optional[str] = None

    def queue_response(self, result: AIClassificationResult):
        """Queue a specific response for the next classify call."""
        self._preset_responses.append(result)

    def set_handler(self, handler: Callable[[AIContentInput], AIClassificationResult]):
        """Set a dynamic handler function."""
        self._custom_handler = handler

    def reset(self):
        """Reset mock state."""
        self._preset_responses.clear()
        self._custom_handler = None
        self.call_count = 0
        self.last_input = None
        self.force_timeout = False
        self.force_error = None

    async def classify(self, content: AIContentInput) -> AIClassificationResult:
        self.call_count += 1
        self.last_input = content

        if self.simulate_latency_ms > 0:
            await asyncio.sleep(self.simulate_latency_ms / 1000.0)

        if self.force_timeout:
            return AIClassificationResult(
                classification="UNCERTAIN",
                reason="Simulated timeout",
                response_time_ms=self.simulate_latency_ms,
                error="TIMEOUT",
            )

        if self.force_error:
            return AIClassificationResult(
                classification="UNCERTAIN",
                reason=f"Simulated error: {self.force_error}",
                response_time_ms=self.simulate_latency_ms,
                error=self.force_error,
            )

        if self._preset_responses:
            res = self._preset_responses.pop(0)
            res.response_time_ms = self.simulate_latency_ms
            return res

        if self._custom_handler:
            res = self._custom_handler(content)
            res.response_time_ms = self.simulate_latency_ms
            return res

        # Default intelligent fallback simulation based on content intent:
        lower = (content.text or "").lower()
        if "sotib olamiz" in lower or "olamiz" in lower or "sotamiz" in lower or "narx" in lower or "aksiya" in lower:
            return AIClassificationResult(
                classification="AD",
                confidence=0.96,
                category="commercial",
                reason="Simulated commercial offer detection",
                response_time_ms=self.simulate_latency_ms,
            )
        elif "qayerga" in lower or "qayerda" in lower or "bormi" in lower or "?" in content.text:
            return AIClassificationResult(
                classification="NOT_AD",
                confidence=0.95,
                category="normal",
                reason="Simulated inquiry detection",
                response_time_ms=self.simulate_latency_ms,
            )
        else:
            return AIClassificationResult(
                classification="NOT_AD",
                confidence=0.85,
                category="normal",
                reason="Simulated conversational text",
                response_time_ms=self.simulate_latency_ms,
            )
