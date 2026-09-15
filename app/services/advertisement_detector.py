from typing import Tuple, Optional
from aiogram.types import Message

from app.services.moderation_filter.classifier import (
    classify_text,
    classify_message,
    ClassificationResult,
)


def is_ad_text(text: str, threshold: Optional[int] = None) -> Tuple[bool, str]:
    """
    Backwards-compatible interface returning (is_ad, reason).
    """
    result = classify_text(raw_text=text, threshold=threshold)
    return result.is_ad, result.reason


def is_advertisement(message: Message, threshold: Optional[int] = None) -> Tuple[bool, str]:
    """
    Backwards-compatible interface returning (is_ad, reason).
    """
    result = classify_message(message=message, threshold=threshold)
    return result.is_ad, result.reason


__all__ = [
    "is_ad_text",
    "is_advertisement",
    "classify_text",
    "classify_message",
    "ClassificationResult",
]
