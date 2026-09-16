import time
import logging
from typing import Dict, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.setting import Setting
from app.config import settings

logger = logging.getLogger(__name__)

# In-memory TTL cache: chat_id -> (is_enabled, expire_timestamp)
_GROUP_AI_CACHE: Dict[int, Tuple[bool, float]] = {}
CACHE_TTL = 60.0  # 1 minute


def clear_group_settings_cache(chat_id: Optional[int] = None):
    """Clear memory cache for a group or all groups."""
    global _GROUP_AI_CACHE
    if chat_id is not None:
        _GROUP_AI_CACHE.pop(chat_id, None)
    else:
        _GROUP_AI_CACHE.clear()


async def is_ai_moderation_enabled(session: AsyncSession, chat_id: int) -> bool:
    """
    Check if AI moderation is enabled for a specific Telegram group.
    - If global settings.AI_ENABLED is False -> always False (master killswitch).
    - If global settings.AI_ENABLED is True -> per-group setting defaults to False (OFF)
      until an admin of the group explicitly enables it.
    - Uses in-memory TTL caching to avoid per-message DB queries.
    """
    # 1. Global Master Switch: if disabled in config, never run AI for any group
    if not settings.AI_ENABLED:
        return False

    now = time.monotonic()
    cached = _GROUP_AI_CACHE.get(chat_id)
    if cached and now < cached[1]:
        return cached[0]

    key = f"group_{chat_id}_ai_enabled"
    try:
        setting_obj = await session.get(Setting, key)
        if setting_obj is not None:
            val = setting_obj.value.strip().lower()
            enabled = val in ("1", "true", "yes", "on")
        else:
            # Per-group default is strictly OFF (False)
            enabled = False

        _GROUP_AI_CACHE[chat_id] = (enabled, now + CACHE_TTL)
        return enabled
    except Exception as e:
        logger.error(f"Error querying AI moderation status for chat {chat_id}: {e}")
        return False


async def is_photo_ai_moderation_enabled(session: AsyncSession, chat_id: int) -> bool:
    """
    Check if multimodal AI moderation is enabled for incoming photos.
    - If global settings.AI_ENABLED is False -> False.
    - If global settings.AI_MODERATE_PHOTOS is False -> fallback to is_ai_moderation_enabled.
    - For photos, multimodal AI is active by default UNLESS a group administrator
      has explicitly disabled AI for this group (value is '0', 'false', 'off', or 'no').
    """
    if not settings.AI_ENABLED:
        return False
    if not getattr(settings, "AI_MODERATE_PHOTOS", True):
        return await is_ai_moderation_enabled(session, chat_id)

    now = time.monotonic()
    cached = _GROUP_AI_CACHE.get(chat_id)
    if cached and now < cached[1]:
        return cached[0]

    key = f"group_{chat_id}_ai_enabled"
    try:
        setting_obj = await session.get(Setting, key)
        if setting_obj is not None:
            val = setting_obj.value.strip().lower()
            enabled = val in ("1", "true", "yes", "on")
        else:
            # By default for photos, if global AI is on, photos are inspected
            enabled = True

        _GROUP_AI_CACHE[chat_id] = (enabled, now + CACHE_TTL)
        return enabled
    except Exception as e:
        logger.error(f"Error querying photo AI status for chat {chat_id}: {e}")
        return True


async def set_ai_moderation_enabled(session: AsyncSession, chat_id: int, enabled: bool) -> None:
    """
    Update AI moderation state for a specific Telegram group and invalidate memory cache.
    """
    key = f"group_{chat_id}_ai_enabled"
    val = "1" if enabled else "0"
    setting_obj = await session.get(Setting, key)
    if setting_obj is None:
        setting_obj = Setting(key=key, value=val)
        session.add(setting_obj)
    else:
        setting_obj.value = val

    await session.commit()

    # Update in-memory cache immediately
    _GROUP_AI_CACHE[chat_id] = (enabled, time.monotonic() + CACHE_TTL)
    logger.info(f"AI moderation for group {chat_id} set to: {'ENABLED' if enabled else 'DISABLED'}")
