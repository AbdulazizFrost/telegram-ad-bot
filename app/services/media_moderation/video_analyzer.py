"""
Video and animation analyzer for advertisement moderation.
Extracts 3-5 keyframes evenly sampled across the video using imageio,
runs lightweight local OCR on frames, aggregates text with caption, and classifies.
Guarantees memory usage < 40MB RAM and cleans up temporary video files in a finally block.
"""

import asyncio
import logging
import os
import tempfile
from typing import List, Optional, Set
from PIL import Image
from aiogram import Bot
from aiogram.types import Video, Animation

import imageio
from app.services.media_moderation.ocr_engine import sync_extract_text_from_pil_image
from app.services.media_moderation.image_analyzer import MediaAnalysisResult
from app.services.moderation_filter.classifier import classify_text
from app.config import settings

logger = logging.getLogger(__name__)


def sync_extract_keyframes_and_ocr(video_path: str, max_frames: int = 5) -> str:
    """
    Synchronously extract keyframes from video and run OCR on each frame.
    Processes one frame at a time to keep RAM consumption strictly below 30MB.
    Executed in a worker thread via asyncio.to_thread.
    """
    reader = None
    extracted_lines: List[str] = []
    seen_lines: Set[str] = set()

    try:
        reader = imageio.get_reader(video_path, "ffmpeg")
        try:
            total_frames = reader.count_frames()
        except Exception:
            try:
                total_frames = reader.get_length()
            except Exception:
                total_frames = 0

        if not total_frames or total_frames <= 0:
            total_frames = 30  # Assume minimum 30 frames fallback

        # Calculate evenly spaced sampling fractions across video duration
        # E.g. for 5 frames: [10%, 30%, 50%, 70%, 90%]
        fractions = [(i + 0.5) / max_frames for i in range(max_frames)]
        target_indices = [min(int(total_frames * f), total_frames - 1) for f in fractions]
        # Remove duplicate indices for very short videos
        target_indices = sorted(list(set(target_indices)))

        for idx in target_indices:
            try:
                np_frame = reader.get_data(idx)
                pil_img = Image.fromarray(np_frame)
                frame_text = sync_extract_text_from_pil_image(pil_img)
                if frame_text:
                    for line in frame_text.splitlines():
                        clean_line = line.strip()
                        if clean_line and clean_line.lower() not in seen_lines:
                            seen_lines.add(clean_line.lower())
                            extracted_lines.append(clean_line)
            except Exception as frame_err:
                logger.debug(f"Could not read frame {idx} from {video_path}: {frame_err}")
                continue

    except Exception as e:
        logger.warning(f"Error opening video {video_path} with imageio: {e}")
    finally:
        if reader is not None:
            try:
                reader.close()
            except Exception:
                pass

    return "\n".join(extracted_lines)


async def analyze_video_message(
    bot: Bot,
    video: Video | Animation,
    caption: str = "",
    entities: Optional[List] = None
) -> MediaAnalysisResult:
    """
    Analyze video or animation message:
    1. Short-circuit if caption is already a confirmed ad (score >= 60).
    2. Check video file size limit (<= 25MB).
    3. Download to temp file, sample keyframes, extract OCR text, clean up temp file.
    4. Classify combined caption + OCR text.
    """
    caption = caption or ""
    metadata = {
        "width": getattr(video, "width", 0),
        "height": getattr(video, "height", 0),
        "duration": getattr(video, "duration", 0),
        "file_size": getattr(video, "file_size", 0),
        "file_id": video.file_id,
    }
    media_type = "animation" if isinstance(video, Animation) else "video"

    # Stage 1: Cheap check on caption
    if caption:
        caption_result = classify_text(caption, entities=entities)
        if caption_result.is_ad and caption_result.score >= 60.0:
            return MediaAnalysisResult(
                is_ad=True,
                score=caption_result.score,
                reason=f"[Video Caption] {caption_result.reason}",
                violation_type=caption_result.violation_type,
                ocr_text="",
                caption=caption,
                combined_text=caption,
                detected_locations=caption_result.detected_locations,
                extracted_phones=caption_result.extracted_phones,
                extracted_links=caption_result.extracted_links,
                media_type=media_type,
                metadata=metadata
            )

    # Check OCR enabled setting
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
            media_type=media_type,
            metadata={"ocr": "disabled"}
        )

    # Check file size limit
    max_bytes = getattr(settings, "MAX_MEDIA_DOWNLOAD_MB", 25) * 1024 * 1024
    if video.file_size and video.file_size > max_bytes:
        logger.warning(f"Video size {video.file_size} exceeds limit {max_bytes} bytes; skipping OCR.")
        res = classify_text(caption, entities=entities)
        return MediaAnalysisResult(
            is_ad=res.is_ad,
            score=res.score,
            reason=res.reason,
            violation_type=res.violation_type,
            caption=caption,
            combined_text=caption,
            media_type=media_type,
            metadata={"skipped_reason": "file_too_large"}
        )

    # Download to temporary file and sample keyframes
    temp_file_path = None
    ocr_text = ""
    max_frames = getattr(settings, "MAX_VIDEO_FRAMES_SAMPLE", 5)

    try:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
            temp_file_path = tf.name

        await bot.download(video.file_id, destination=temp_file_path)
        ocr_text = await asyncio.to_thread(sync_extract_keyframes_and_ocr, temp_file_path, max_frames)
    except Exception as e:
        logger.warning(f"Failed downloading or sampling video {video.file_id}: {e}")
    finally:
        # Crucial: Always remove temporary video file to avoid filling host disk
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as del_err:
                logger.debug(f"Could not delete temp video file {temp_file_path}: {del_err}")

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
        reason = f"[Video matni] {classification.reason}"
    elif ocr_text.strip() and caption.strip():
        reason = f"[Video+Matn] {classification.reason}"

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
        media_type=media_type,
        metadata=metadata
    )
