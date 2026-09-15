from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


VALID_CLASSIFICATIONS = {"AD", "NOT_AD", "UNCERTAIN"}

VALID_CATEGORIES = {
    "commercial",
    "transport",
    "product_sale",
    "product_purchase",
    "service",
    "job",
    "real_estate",
    "other",
    "normal",
    "uncertain",
}


@dataclass
class AIContentInput:
    """Input payload for AI moderation (extensible for future multimodal media)."""
    text: str
    chat_id: int = 0
    message_id: int = 0
    media_type: str = "text"
    ocr_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AIClassificationResult:
    """Structured decision returned by AI moderation provider."""
    classification: str = "UNCERTAIN"  # AD, NOT_AD, UNCERTAIN
    confidence: float = 0.0           # 0.0 to 1.0
    category: str = "uncertain"       # commercial, transport, service, job, normal, etc.
    reason: str = ""                  # Brief explanation
    response_time_ms: float = 0.0
    error: Optional[str] = None
    raw_response: Optional[str] = None

    @property
    def is_ad(self) -> bool:
        return self.classification == "AD"


class BaseAIProvider(ABC):
    """Abstract interface for replaceable AI providers."""

    @abstractmethod
    async def classify(self, content: AIContentInput) -> AIClassificationResult:
        """Classify message content and return structured AIClassificationResult."""
        pass
