"""
Unified Media and Text Moderation Pipeline.
Coordinates text classification, photo OCR, video keyframe sampling, and media group debounce.
Produces a unified moderation decision with full forensic details for logging.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from aiogram import Bot
from aiogram.types import Message

from app.services.moderation_filter.classifier import classify_message, ClassificationResult
from app.services.media_moderation.image_analyzer import analyze_photo_message, MediaAnalysisResult
from app.services.media_moderation.video_analyzer import analyze_video_message
from app.services.media_moderation.album_manager import album_manager, AlbumAnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class UnifiedModerationDecision:
    is_ad: bool = False
    score: float = 0.0
    reason: str = ""
    violation_type: str = "NORMAL_MESSAGE"
    media_type: str = "text"  # "text", "photo", "video", "animation", "album"
    extracted_ocr_text: str = ""
    original_text: str = ""
    combined_text: str = ""
    detected_locations: List[str] = field(default_factory=list)
    extracted_phones: List[str] = field(default_factory=list)
    extracted_links: List[str] = field(default_factory=list)
    target_message_ids: List[int] = field(default_factory=list)
    is_album: bool = False
    is_album_leader: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


async def analyze_message_multimodal(bot: Bot, message: Message) -> UnifiedModerationDecision:
    """
    Multimodal entry point:
    Inspects message type (text, photo, video, animation, or media group),
    extracts content via OCR if applicable, and classifies advertisement intent.
    """
    chat_id = message.chat.id
    msg_id = message.message_id
    raw_text = message.text or message.caption or ""

    # Helper to check real media objects (safely ignoring MagicMock in unit tests)
    mg_id = message.media_group_id if (isinstance(message.media_group_id, str) and message.media_group_id) else None
    has_photo = bool(getattr(message, "photo", None) and isinstance(message.photo, list))
    has_video = bool(getattr(message, "video", None) and not hasattr(message.video, "_mock_name"))
    has_animation = bool(getattr(message, "animation", None) and not hasattr(message.animation, "_mock_name"))

    # Case 1: Telegram Album (Media Group)
    if mg_id:
        album_res: Optional[AlbumAnalysisResult] = await album_manager.add_message(bot, message)
        if album_res is None:
            # Cancelled or debounce still in progress
            return UnifiedModerationDecision(is_ad=False, media_type="album")

        # Determine if this message is the leader (first message_id in album)
        is_leader = bool(album_res.message_ids and album_res.message_ids[0] == msg_id)

        return UnifiedModerationDecision(
            is_ad=album_res.is_ad,
            score=album_res.score,
            reason=album_res.reason,
            violation_type=album_res.violation_type,
            media_type="album",
            extracted_ocr_text=album_res.aggregated_ocr,
            original_text=album_res.aggregated_caption,
            combined_text=album_res.combined_text,
            detected_locations=album_res.detected_locations,
            extracted_phones=album_res.extracted_phones,
            extracted_links=album_res.extracted_links,
            target_message_ids=album_res.message_ids,
            is_album=True,
            is_album_leader=is_leader,
            metadata={"items_count": album_res.items_count, "media_group_id": album_res.media_group_id, **album_res.metadata}
        )

    # Case 2: Photo Message
    if has_photo:
        photo_res = await analyze_photo_message(
            bot=bot,
            photo_sizes=message.photo,
            caption=message.caption or "",
            entities=message.caption_entities
        )
        return UnifiedModerationDecision(
            is_ad=photo_res.is_ad,
            score=photo_res.score,
            reason=photo_res.reason,
            violation_type=photo_res.violation_type,
            media_type="photo",
            extracted_ocr_text=photo_res.ocr_text,
            original_text=photo_res.caption,
            combined_text=photo_res.combined_text,
            detected_locations=photo_res.detected_locations,
            extracted_phones=photo_res.extracted_phones,
            extracted_links=photo_res.extracted_links,
            target_message_ids=[msg_id],
            is_album=False,
            metadata=photo_res.metadata
        )

    # Case 3: Video or Animation Message
    if has_video or has_animation:
        video_obj = message.video if has_video else message.animation
        media_name = "animation" if has_animation else "video"
        video_res = await analyze_video_message(
            bot=bot,
            video=video_obj,
            caption=message.caption or "",
            entities=message.caption_entities
        )
        return UnifiedModerationDecision(
            is_ad=video_res.is_ad,
            score=video_res.score,
            reason=video_res.reason,
            violation_type=video_res.violation_type,
            media_type=media_name,
            extracted_ocr_text=video_res.ocr_text,
            original_text=video_res.caption,
            combined_text=video_res.combined_text,
            detected_locations=video_res.detected_locations,
            extracted_phones=video_res.extracted_phones,
            extracted_links=video_res.extracted_links,
            target_message_ids=[msg_id],
            is_album=False,
            metadata=video_res.metadata
        )

    # Case 4: Plain Text Message
    text_res: ClassificationResult = classify_message(message)
    return UnifiedModerationDecision(
        is_ad=text_res.is_ad,
        score=text_res.score,
        reason=text_res.reason,
        violation_type=text_res.violation_type,
        media_type="text",
        extracted_ocr_text="",
        original_text=raw_text,
        combined_text=raw_text,
        detected_locations=text_res.detected_locations,
        extracted_phones=text_res.extracted_phones,
        extracted_links=text_res.extracted_links,
        target_message_ids=[msg_id],
        is_album=False,
        metadata={}
    )
