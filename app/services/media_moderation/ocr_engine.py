"""
Local OCR Engine using Pillow and pytesseract.
Runs purely locally within Render 512MB RAM constraints (no PyTorch, no cloud APIs).
Runs in background threads via asyncio.to_thread to avoid blocking aiogram event loop.
Provides graceful fallback if Tesseract binary is not installed on host.
"""

import asyncio
import io
import logging
import os
import shutil
from typing import Optional
from PIL import Image, ImageOps, ImageFilter

logger = logging.getLogger(__name__)

# Check if pytesseract is installed
try:
    import pytesseract
    PYTESSERACT_INSTALLED = True
except ImportError:
    pytesseract = None
    PYTESSERACT_INSTALLED = False

# Auto-configure tesseract path if on Windows or custom path
TESSERACT_AVAILABLE = False
_TESSERACT_WARNED = False

if PYTESSERACT_INSTALLED:
    custom_cmd = os.environ.get("TESSERACT_CMD")
    if custom_cmd and os.path.isfile(custom_cmd):
        pytesseract.pytesseract.tesseract_cmd = custom_cmd
        TESSERACT_AVAILABLE = True
    elif shutil.which("tesseract"):
        TESSERACT_AVAILABLE = True
    else:
        # Standard Windows installation path fallback
        win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.isfile(win_path):
            pytesseract.pytesseract.tesseract_cmd = win_path
            TESSERACT_AVAILABLE = True
        else:
            TESSERACT_AVAILABLE = False


def is_ocr_available() -> bool:
    """Return True if local OCR engine is ready for use."""
    return PYTESSERACT_INSTALLED and TESSERACT_AVAILABLE


def preprocess_image_for_ocr(img: Image.Image, max_dim: int = 1920) -> Image.Image:
    """
    Preprocess image to maximize OCR legibility while clamping memory usage:
    1. Downscale if dimension > max_dim (saves RAM, keeps RAM < 25MB).
    2. Convert RGBA to RGB on white background.
    3. Convert to grayscale and apply contrast enhancement.
    """
    # 1. Clamp dimensions
    w, h = img.size
    if w > max_dim or h > max_dim:
        scale = max_dim / max(w, h)
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 2. Alpha handling (convert transparent PNG/stickers to white background)
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        background = Image.new("RGB", img.size, (255, 255, 255))
        converted = img.convert("RGBA")
        background.paste(converted, mask=converted.split()[-1])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # 3. Grayscale and auto-contrast
    gray = ImageOps.grayscale(img)
    enhanced = ImageOps.autocontrast(gray, cutoff=2)
    return enhanced


def sync_extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """
    Synchronous OCR text extraction from raw image bytes.
    Should be executed inside asyncio.to_thread.
    """
    global _TESSERACT_WARNED

    if not PYTESSERACT_INSTALLED or not TESSERACT_AVAILABLE:
        if not _TESSERACT_WARNED:
            logger.warning(
                "Tesseract OCR is not installed or available on this system. "
                "Media moderation will gracefully fall back to captions and metadata."
            )
            _TESSERACT_WARNED = True
        return ""

    if not image_bytes or len(image_bytes) == 0:
        return ""

    try:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            processed = preprocess_image_for_ocr(pil_img)

            # Try languages in descending preference: uzb+rus+eng -> rus+eng -> eng
            languages_to_try = ["uzb+rus+eng", "rus+eng", "eng"]
            ocr_text = ""

            for lang in languages_to_try:
                try:
                    ocr_text = pytesseract.image_to_string(
                        processed,
                        lang=lang,
                        config="--psm 11 --oem 3"  # Sparse text finding on posters/banners
                    )
                    if ocr_text.strip():
                        break
                except Exception as e:
                    # Specific language pack might be missing in host tesseract
                    logger.debug(f"Tesseract lang '{lang}' failed: {e}. Trying fallback...")
                    continue

            return ocr_text.strip()
    except Exception as e:
        logger.warning(f"Error during OCR extraction: {e}")
        return ""


async def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Asynchronously extract text from image bytes using a background worker thread.
    Never blocks the aiogram event loop.
    """
    return await asyncio.to_thread(sync_extract_text_from_image_bytes, image_bytes)


def sync_extract_text_from_pil_image(pil_img: Image.Image) -> str:
    """Extract text directly from an in-memory PIL Image (e.g. video keyframe)."""
    global _TESSERACT_WARNED

    if not PYTESSERACT_INSTALLED or not TESSERACT_AVAILABLE:
        if not _TESSERACT_WARNED:
            logger.warning("Tesseract OCR is not available. Skipping keyframe OCR.")
            _TESSERACT_WARNED = True
        return ""

    try:
        processed = preprocess_image_for_ocr(pil_img)
        for lang in ["uzb+rus+eng", "rus+eng", "eng"]:
            try:
                text = pytesseract.image_to_string(
                    processed,
                    lang=lang,
                    config="--psm 11 --oem 3"
                )
                if text.strip():
                    return text.strip()
            except Exception:
                continue
        return ""
    except Exception as e:
        logger.warning(f"Error during PIL Image OCR: {e}")
        return ""


async def extract_text_from_frame(pil_img: Image.Image) -> str:
    """Asynchronous OCR on a PIL Image keyframe."""
    return await asyncio.to_thread(sync_extract_text_from_pil_image, pil_img)
