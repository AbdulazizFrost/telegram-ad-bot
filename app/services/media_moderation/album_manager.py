"""
Media Group (Album) Debounce and Aggregation Manager.
Aggregates split album items (photos/videos) within a debounced time window (0.4s)
to detect fragmented cross-item ads and delete all album messages together.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from aiogram import Bot
from aiogram.types import Message

from app.services.media_moderation.image_analyzer import (
    MediaAnalysisResult,
    analyze_photo_message,
)
from app.services.media_moderation.video_analyzer import analyze_video_message
from app.services.moderation_filter.classifier import classify_text
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AlbumEntry:
    media_group_id: str
    chat_id: int
    user_id: int
    messages: List[Message] = field(default_factory=list)
    future: Optional[asyncio.Future] = None
    timer_task: Optional[asyncio.Task] = None


@dataclass
class AlbumAnalysisResult:
    is_ad: bool = False
    score: float = 0.0
    reason: str = ""
    violation_type: str = "NORMAL_MESSAGE"
    media_group_id: str = ""
    message_ids: List[int] = field(default_factory=list)
    aggregated_caption: str = ""
    aggregated_ocr: str = ""
    combined_text: str = ""
    detected_locations: List[str] = field(default_factory=list)
    extracted_phones: List[str] = field(default_factory=list)
    extracted_links: List[str] = field(default_factory=list)
    media_type: str = "album"
    items_count: int = 0


class AlbumManager:
    """
    Manages buffering and aggregation of media group (album) messages.
    """
    def __init__(self, debounce_seconds: float = 0.4):
        self.debounce_seconds = debounce_seconds
        self._albums: Dict[str, AlbumEntry] = {}
        self._lock = asyncio.Lock()

    async def add_message(
        self,
        bot: Bot,
        message: Message,
        on_album_ready: Optional[Callable[[AlbumAnalysisResult], Any]] = None
    ) -> Optional[AlbumAnalysisResult]:
        """
        Add an album message to the buffer.
        Only the last debounced caller will process the album and return AlbumAnalysisResult.
        All other callers receive None while waiting or let the debounce worker handle it.
        """
        mg_id = message.media_group_id
        if not mg_id:
            return None

        async with self._lock:
            if mg_id not in self._albums:
                loop = asyncio.get_running_loop()
                entry = AlbumEntry(
                    media_group_id=mg_id,
                    chat_id=message.chat.id,
                    user_id=message.from_user.id if message.from_user else 0,
                    future=loop.create_future(),
                )
                self._albums[mg_id] = entry
            else:
                entry = self._albums[mg_id]

            entry.messages.append(message)

            # Cancel existing timer task and restart with fresh debounce window
            if entry.timer_task and not entry.timer_task.done():
                entry.timer_task.cancel()

            entry.timer_task = asyncio.create_task(
                self._debounced_process(bot, mg_id)
            )

        # Await the shared future so all handlers for this album know the final result
        try:
            return await asyncio.shield(entry.future)
        except asyncio.CancelledError:
            return None

    async def _debounced_process(self, bot: Bot, media_group_id: str):
        """Wait debounce_seconds and then analyze all buffered album items."""
        await asyncio.sleep(self.debounce_seconds)

        async with self._lock:
            entry = self._albums.get(media_group_id)
            if not entry:
                return

        try:
            result = await self._analyze_album(bot, entry)
            if entry.future and not entry.future.done():
                entry.future.set_result(result)
        except Exception as e:
            logger.error(f"Error analyzing album {media_group_id}: {e}", exc_info=True)
            if entry.future and not entry.future.done():
                entry.future.set_result(AlbumAnalysisResult(media_group_id=media_group_id))
        finally:
            async with self._lock:
                self._albums.pop(media_group_id, None)

    async def _analyze_album(self, bot: Bot, entry: AlbumEntry) -> AlbumAnalysisResult:
        """Process all items in the album, aggregate text, and classify."""
        captions: List[str] = []
        ocr_texts: List[str] = []
        message_ids: List[int] = []
        all_entities = []

        for msg in entry.messages:
            message_ids.append(msg.message_id)
            if msg.caption:
                captions.append(msg.caption.strip())
            if msg.caption_entities:
                all_entities.extend(msg.caption_entities)

            # Analyze media per message
            if msg.photo:
                res = await analyze_photo_message(bot, msg.photo, caption="")
                if res.ocr_text:
                    ocr_texts.append(res.ocr_text)
            elif msg.video:
                res = await analyze_video_message(bot, msg.video, caption="")
                if res.ocr_text:
                    ocr_texts.append(res.ocr_text)

        aggregated_caption = "\n".join(dict.fromkeys(captions))  # Deduplicated
        aggregated_ocr = "\n".join(dict.fromkeys(ocr_texts))

        combined_parts = []
        if aggregated_caption.strip():
            combined_parts.append(aggregated_caption.strip())
        if aggregated_ocr.strip():
            combined_parts.append(aggregated_ocr.strip())

        combined_text = "\n".join(combined_parts)
        classification = classify_text(combined_text, entities=all_entities)

        reason = classification.reason
        if classification.is_ad:
            reason = f"[Albom / {len(entry.messages)} ta fayl] {classification.reason}"

        return AlbumAnalysisResult(
            is_ad=classification.is_ad,
            score=classification.score,
            reason=reason,
            violation_type=classification.violation_type,
            media_group_id=entry.media_group_id,
            message_ids=message_ids,
            aggregated_caption=aggregated_caption,
            aggregated_ocr=aggregated_ocr,
            combined_text=combined_text,
            detected_locations=classification.detected_locations,
            extracted_phones=classification.extracted_phones,
            extracted_links=classification.extracted_links,
            media_type="album",
            items_count=len(entry.messages)
        )


# Global album manager instance
album_manager = AlbumManager(debounce_seconds=getattr(settings, "ALBUM_DEBOUNCE_SECONDS", 0.4))
