"""
Unit tests for Multimodal Media Moderation:
- OCR engine preprocessing & graceful fallback
- Photo analyzer & caption short-circuiting
- Video analyzer keyframe extraction & temp file cleanup
- Media group (album) debounce buffer & aggregation
- Location & route detection
"""

import asyncio
import io
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from PIL import Image

from app.services.media_moderation.ocr_engine import (
    preprocess_image_for_ocr,
    sync_extract_text_from_image_bytes,
    extract_text_from_image,
    is_ocr_available,
)
from app.services.media_moderation.image_analyzer import (
    analyze_photo_message,
    MediaAnalysisResult,
)
from app.services.media_moderation.video_analyzer import (
    analyze_video_message,
    sync_extract_keyframes_and_ocr,
)
from app.services.media_moderation.album_manager import (
    AlbumManager,
    AlbumAnalysisResult,
)
from app.services.media_moderation.pipeline import analyze_message_multimodal
from app.services.locations.detector import detect_locations
from app.services.moderation_filter.classifier import classify_text
from app.services.moderation_service import process_group_message
from app.services.ai_moderation.prompt import build_multimodal_classification_prompt
from app.services.ai_moderation.base import AIClassificationResult
from app.services.ai_moderation.service import ai_moderation_service
from app.services.ai_moderation.mock_provider import MockAIProvider
from app.database import Base
from app.config import settings
from aiogram.types import PhotoSize
from aiogram.enums import ChatType, ChatMemberStatus
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


# ==========================================
# 1. OCR ENGINE TESTS
# ==========================================

def test_preprocess_image_dimensions():
    """Verify image larger than max_dim is resized proportionally without distorting aspect ratio."""
    large_img = Image.new("RGB", (3000, 2000), color="white")
    processed = preprocess_image_for_ocr(large_img, max_dim=1920)
    w, h = processed.size
    assert max(w, h) <= 1920
    assert abs((w / h) - (3000 / 2000)) < 0.01


def test_preprocess_image_rgba_conversion():
    """Verify RGBA transparent images are correctly converted to white-background RGB/grayscale."""
    rgba_img = Image.new("RGBA", (500, 500), color=(255, 0, 0, 128))
    processed = preprocess_image_for_ocr(rgba_img)
    assert processed.mode == "L"  # Grayscale for OCR legibility


def test_ocr_fallback_when_unavailable():
    """Verify OCR returns empty string and does not crash when Tesseract is missing."""
    with patch("app.services.media_moderation.ocr_engine.TESSERACT_AVAILABLE", False):
        res = sync_extract_text_from_image_bytes(b"dummy_bytes")
        assert res == ""


@pytest.mark.asyncio
async def test_async_extract_text_from_image():
    """Verify extract_text_from_image executes without blocking."""
    # Create valid 10x10 PNG bytes
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="white").save(buf, format="PNG")
    png_bytes = buf.getvalue()

    with patch("app.services.media_moderation.ocr_engine.TESSERACT_AVAILABLE", False):
        text = await extract_text_from_image(png_bytes)
        assert text == ""


# ==========================================
# 2. PHOTO ANALYZER TESTS
# ==========================================

@pytest.mark.asyncio
async def test_photo_caption_short_circuit():
    """If photo caption is a confirmed ad, it should classify immediately without downloading photo."""
    bot = AsyncMock()
    photo_size = MagicMock()
    photo_size.file_id = "test_photo_1"
    photo_size.file_size = 50000
    photo_size.width = 800
    photo_size.height = 600

    caption = "Toshkent Samarqand mashina bor 2 ta joy bor tel 90 123 45 67"
    res = await analyze_photo_message(bot, [photo_size], caption=caption)

    assert res.is_ad is True
    assert res.score >= 50.0
    bot.download.assert_not_called()  # Verified short-circuit!


@pytest.mark.asyncio
async def test_photo_ocr_detection():
    """If caption is empty but OCR finds ad text, message must be classified as ad."""
    bot = AsyncMock()
    photo_size = MagicMock()
    photo_size.file_id = "ad_poster_123"
    photo_size.file_size = 5000
    photo_size.width = 600
    photo_size.height = 800

    # Mock download to populate buffer with blank image
    async def mock_download(file_id, destination):
        buf = io.BytesIO()
        Image.new("RGB", (100, 100), color="white").save(buf, format="PNG")
        destination.write(buf.getvalue())

    bot.download = AsyncMock(side_effect=mock_download)

    # Mock OCR returning advertising text
    ad_ocr = "Gurlan Toshkent taxi qatnovi 4 ta joy bor nomer: +998 90 123 45 67"
    with patch("app.services.media_moderation.image_analyzer.extract_text_from_image", new=AsyncMock(return_value=ad_ocr)):
        res = await analyze_photo_message(bot, [photo_size], caption="")
        assert res.is_ad is True
        assert res.score >= 50.0
        assert "toshkent" in res.detected_locations or "gurlan" in res.detected_locations
        assert "998901234567" in res.extracted_phones or "+998 90 123 45 67" in res.combined_text


# ==========================================
# 3. VIDEO ANALYZER TESTS
# ==========================================

@pytest.mark.asyncio
async def test_video_caption_short_circuit():
    """If video caption is an ad, it should classify without downloading the video file."""
    bot = AsyncMock()
    video = MagicMock()
    video.file_id = "video_123"
    video.file_size = 1000000

    caption = "Mebel sotiladi sifatli narxi arzon murojaat uchun tel: 93 111 22 33"
    res = await analyze_video_message(bot, video, caption=caption)

    assert res.is_ad is True
    bot.download.assert_not_called()


@pytest.mark.asyncio
async def test_video_tempfile_cleanup():
    """Verify temp video file is deleted even if error occurs during extraction."""
    bot = AsyncMock()
    video = MagicMock()
    video.file_id = "video_temp_test"
    video.file_size = 5000

    created_temp_file = None

    async def mock_download_video(file_id, destination):
        nonlocal created_temp_file
        created_temp_file = destination
        with open(destination, "wb") as f:
            f.write(b"dummy mp4 content")

    bot.download = AsyncMock(side_effect=mock_download_video)

    with patch("app.services.media_moderation.video_analyzer.sync_extract_keyframes_and_ocr", side_effect=RuntimeError("Test error")):
        res = await analyze_video_message(bot, video, caption="")
        # Temp file must be cleaned up!
        assert created_temp_file is not None
        assert not os.path.exists(created_temp_file)


# ==========================================
# 4. ALBUM DEBOUNCE & AGGREGATION TESTS
# ==========================================

@pytest.mark.asyncio
async def test_album_manager_debounce_and_aggregation():
    """
    Test album evasion:
    Photo 1 has route: 'Toshkentga ketamiz'
    Photo 2 has contact: 'tel 90 123 45 67'
    Together they form a confirmed ad, and both messages must be targeted for deletion.
    """
    manager = AlbumManager(debounce_seconds=0.1)
    bot = AsyncMock()

    msg1 = MagicMock()
    msg1.message_id = 101
    msg1.media_group_id = "album_999"
    msg1.chat.id = -1001
    msg1.from_user.id = 555
    msg1.caption = "Toshkentga ketamiz"
    msg1.caption_entities = []
    msg1.photo = []
    msg1.video = None

    msg2 = MagicMock()
    msg2.message_id = 102
    msg2.media_group_id = "album_999"
    msg2.chat.id = -1001
    msg2.from_user.id = 555
    msg2.caption = "aloqa uchun tel 90 123 45 67"
    msg2.caption_entities = []
    msg2.photo = []
    msg2.video = None

    # Dispatch both items concurrently
    task1 = asyncio.create_task(manager.add_message(bot, msg1))
    await asyncio.sleep(0.02)
    task2 = asyncio.create_task(manager.add_message(bot, msg2))

    res1, res2 = await asyncio.gather(task1, task2)

    assert res1 is not None
    assert res2 is not None
    assert res1.is_ad is True
    assert 101 in res1.message_ids
    assert any("90 123 45 67" in p or "998901234567" in p for p in res1.extracted_phones)


# ==========================================
# 5. LOCATION & ROUTE DETECTION TESTS
# ==========================================

def test_location_affix_stripping():
    """Verify Uzbek case endings (-ga, -dan, -da, -gacha) are stripped and classified."""
    # Destination
    res_dest = detect_locations("Ertaga Toshkentga boramiz")
    assert "toshkent" in res_dest.destinations
    assert res_dest.is_transit_offer is True

    # Khorezmian / regional -a affix
    res_khorezm = detect_locations("Gurlanga taxi bor 2 ta joy bor")
    assert "gurlan" in res_dest.detected_locations or "gurlan" in res_khorezm.destinations
    assert res_khorezm.is_transit_offer is True

    # Origin & Destination pair
    res_route = detect_locations("Gurlandan Toshkentga yuramiz")
    assert "gurlan" in res_route.origins
    assert "toshkent" in res_route.destinations
    assert res_route.is_transit_offer is True


def test_location_russian_prepositions():
    """Verify Russian prepositions (v, do, iz) correctly set destination/origin roles."""
    res_ru = detect_locations("Edem v tashkent est mesta dlya 2 chelovek")
    assert "toshkent" in res_ru.destinations
    assert res_ru.is_transit_offer is True


def test_passenger_party_not_driver_ad():
    """Verify passenger inquiries ('Taqsi toshkentga 4 odam miz') are not flagged as driver ads."""
    res = detect_locations("Taqsi toshkentga 4 odam miz")
    assert res.is_transit_offer is False


# ==========================================
# 6. MULTIMODAL PHOTO AI MODERATION TESTS
# ==========================================

@asynccontextmanager
async def _get_test_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with sm() as session:
        yield session
    await engine.dispose()


def test_patterns_agricultural_sholi_oramiz():
    """Verify local classifier recognizes sholi o'ramiz harvesting services."""
    res = classify_text("sholi õramiz tel 97 787 96 21")
    assert res.is_ad is True
    assert res.score >= 50.0


def test_multimodal_prompt_builder():
    """Verify multimodal prompt builder produces clear instructions for image inspection."""
    prompt_no_caption = build_multimodal_classification_prompt("")
    assert "Examine the attached image" in prompt_no_caption
    assert "?" not in prompt_no_caption  # No question mark confusion

    prompt_with_caption = build_multimodal_classification_prompt("Aloqa uchun")
    assert "<user_text>" in prompt_with_caption
    assert "Aloqa uchun" in prompt_with_caption


@pytest.mark.asyncio
async def test_photo_multimodal_ad_deleted_by_ai(monkeypatch):
    """
    Verify that an incoming photo message without caption is passed to multimodal AI,
    classified as AD, and automatically deleted.
    """
    monkeypatch.setattr(settings, "AI_ENABLED", True)
    monkeypatch.setattr(settings, "AI_MODERATE_PHOTOS", True)

    mock_provider = MockAIProvider()
    mock_provider.queue_response(
        AIClassificationResult(
            classification="AD",
            confidence=0.98,
            category="service",
            reason="Qishloq xo'jaligi xizmati (sholi o'rish) va telefon raqami reklama qilingan",
        )
    )
    ai_moderation_service.set_provider(mock_provider)

    try:
        # Create mock photo message
        msg = MagicMock()
        msg.message_id = 9999
        msg.chat.id = -100999111
        msg.chat.type = ChatType.SUPERGROUP
        msg.chat.title = "Test Group"

        user = MagicMock()
        user.id = 555444
        user.username = "harvester_uz"
        user.first_name = "Farmer"
        user.last_name = None
        user.is_bot = False
        msg.from_user = user

        msg.text = None
        msg.caption = None
        msg.media_group_id = None
        msg.entities = None
        msg.caption_entities = None
        msg.video = None
        msg.animation = None

        photo = PhotoSize(file_id="photo_file_99", file_unique_id="uniq99", width=1024, height=768, file_size=40960)
        msg.photo = [photo]

        bot = AsyncMock()
        bot.get_chat_member.return_value.status = ChatMemberStatus.MEMBER
        bot.get_me.return_value.username = "ad_bot"

        # Mock download to return valid JPEG bytes
        async def mock_download(file_id, destination):
            img = Image.new("RGB", (100, 100), color="blue")
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            destination.write(buf.getvalue())

        bot.download.side_effect = mock_download

        async with _get_test_session() as session:
            deleted = await process_group_message(bot, msg, session)

            assert deleted is True
            bot.delete_message.assert_called_once_with(chat_id=-100999111, message_id=9999)
            assert mock_provider.call_count == 1
    finally:
        ai_moderation_service.set_provider(None)

