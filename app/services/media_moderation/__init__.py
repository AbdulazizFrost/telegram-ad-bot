"""
Media Moderation Package.
Provides autonomous local OCR, video keyframe inspection, and media group debounce moderation.
"""

from app.services.media_moderation.ocr_engine import (
    is_ocr_available,
    extract_text_from_image,
    extract_text_from_frame,
)
from app.services.media_moderation.image_analyzer import (
    analyze_photo_message,
    MediaAnalysisResult,
)
from app.services.media_moderation.video_analyzer import analyze_video_message
from app.services.media_moderation.album_manager import album_manager, AlbumAnalysisResult
from app.services.media_moderation.pipeline import (
    analyze_message_multimodal,
    UnifiedModerationDecision,
)

__all__ = [
    "is_ocr_available",
    "extract_text_from_image",
    "extract_text_from_frame",
    "analyze_photo_message",
    "MediaAnalysisResult",
    "analyze_video_message",
    "album_manager",
    "AlbumAnalysisResult",
    "analyze_message_multimodal",
    "UnifiedModerationDecision",
]
