"""
Image analyzer for photo and animation moderation.
Extracts in-image text via local OCR engine, aggregates with caption, and classifies.
"""

import io
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from aiogram import Bot
from aiogram.types import PhotoSize, Animation

from app.services.media_moderation.ocr_engine import extract_text_from_image
from app.services.moderation_filter.classifier import classify_text, ClassificationResult
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MediaAnalysisResult:
    is_ad: bool = False
    score: float = 0.0
    reason: str = ""
    violation_type: str = "NORMAL_MESSAGE"
    ocr_text: str = ""
    caption: str = ""
    combined_text: str = ""
    detected_locations: List[str] = field(default_factory=list)
    extracted_phones: List[str] = field(default_factory=list)
    extracted_links: List[str] = field(default_factory=list)
    media_type: str = "photo"
    metadata: Dict[str, Any] = field(default_factory=dict)


async def analyze_photo_message(
    bot: Bot,
    photo_sizes: List[PhotoSize],
    caption: str = "",
    entities: Optional[List] = None
) -> MediaAnalysisResult:
    """
    Download photo, run local OCR, combine with caption, and classify.
    Selects optimal photo size (medium/large, clamped < 25MB).
    """
    caption = caption or ""
    metadata = {}

    # Stage 1: Cheap check on caption alone
    if caption:
        caption_result = classify_text(caption, entities=entities)
        # If caption alone is a definite ad (score >= 60), we can short-circuit
        if caption_result.is_ad and caption_result.score >= 60.0:
            return MediaAnalysisResult(
                is_ad=True,
                score=caption_result.score,
                reason=f"[Caption] {caption_result.reason}",
                violation_type=caption_result.violation_type,
                ocr_text="",
                caption=caption,
                combined_text=caption,
                detected_locations=caption_result.detected_locations,
                extracted_phones=caption_result.extracted_phones,
                extracted_links=caption_result.extracted_links,
                media_type="photo",
                metadata={"file_size": 0, "source": "caption_short_circuit"}
            )

    # If OCR is disabled in config, fallback to caption classification
    if not getattr(settings, "OCR_ENABLED", True):
        res = classify_text(caption, entities=entities)
        return MediaAnalysisResult(
            is_ad=res.is_ad,
            score=res.score,
            reason=res.reason,
            violation_type=res.violation_type,
            caption=caption,
            combined_text=caption,
            detected_locations=res.detected_locations,
            extracted_phones=res.extracted_phones,
            extracted_links=res.extracted_links,
            media_type="photo",
            metadata={"ocr": "disabled"}
        )

    # Pick best photo size (Telegram provides thumbs in ascending size order)
    # The last one is the highest resolution
    target_photo = photo_sizes[-1] if photo_sizes else None
    if not target_photo:
        res = classify_text(caption, entities=entities)
        return MediaAnalysisResult(
            is_ad=res.is_ad,
            score=res.score,
            reason=res.reason,
            violation_type=res.violation_type,
            caption=caption,
            combined_text=caption,
            media_type="photo"
        )

    max_bytes = getattr(settings, "MAX_MEDIA_DOWNLOAD_MB", 25) * 1024 * 1024
    if target_photo.file_size and target_photo.file_size > max_bytes:
        logger.warning(f"Photo size {target_photo.file_size} exceeds limit {max_bytes} bytes; skipping OCR.")
        res = classify_text(caption, entities=entities)
        return MediaAnalysisResult(
            is_ad=res.is_ad,
            score=res.score,
            reason=res.reason,
            violation_type=res.violation_type,
            caption=caption,
            combined_text=caption,
            media_type="photo",
            metadata={"skipped_reason": "file_too_large"}
        )

    # Download into memory buffer
    ocr_text = ""
    try:
        buffer = io.BytesIO()
        await bot.download(target_photo.file_id, destination=buffer)
        image_bytes = buffer.getvalue()
        metadata = {
            "width": target_photo.width,
            "height": target_photo.height,
            "file_size": len(image_bytes),
            "file_id": target_photo.file_id
        }
        ocr_text = await extract_text_from_image(image_bytes)
    except Exception as e:
        logger.warning(f"Failed to download/OCR photo {target_photo.file_id}: {e}")

    # Stage 2: Combine Caption + OCR Text
    combined_parts = []
    if caption.strip():
        combined_parts.append(caption.strip())
    if ocr_text.strip():
        combined_parts.append(ocr_text.strip())

    combined_text = "\n".join(combined_parts)
    classification = classify_text(combined_text, entities=entities)

    reason = classification.reason
    if ocr_text.strip() and not caption.strip():
        reason = f"[Rasm matni] {classification.reason}"
    elif ocr_text.strip() and caption.strip():
        reason = f"[Rasm+Matn] {classification.reason}"

    return MediaAnalysisResult(
        is_ad=classification.is_ad,
        score=classification.score,
        reason=reason,
        violation_type=classification.violation_type,
        ocr_text=ocr_text,
        caption=caption,
        combined_text=combined_text,
        detected_locations=classification.detected_locations,
        extracted_phones=classification.extracted_phones,
        extracted_links=classification.extracted_links,
        media_type="photo",
        metadata=metadata
    )
