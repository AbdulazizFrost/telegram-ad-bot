import asyncio
import logging
from datetime import timedelta
from typing import Optional, Any
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.taxi_limit import TaxiAdLimit
from app.models.moderation_log import ModerationLog
from app.models.setting import Setting
from app.services.media_moderation import analyze_message_multimodal, UnifiedModerationDecision
from app.services.subscription_service import get_or_create_user, has_active_subscription
from app.services.ai_moderation import (
    should_escalate_to_ai,
    is_ai_moderation_enabled,
    is_photo_ai_moderation_enabled,
    ai_moderation_service,
)
from app.utils.time import now_utc, is_past_24_hours, next_available_free_ad_time, format_tashkent
from app.config import settings

logger = logging.getLogger(__name__)


def _clean_str(val: Any) -> Optional[str]:
    if val is None:
        return None
    if hasattr(val, "_mock_name") or "mock" in type(val).__name__.lower():
        return None
    return str(val)


import time
from typing import Optional, Any, Dict, Tuple

_ADMIN_CACHE: Dict[Tuple[int, int], Tuple[bool, float]] = {}
_MAX_ADMIN_CACHE_ENTRIES = 5000
_CACHED_BOT_USERNAME: Optional[str] = None


def clear_admin_cache():
    """Clear memory cache for group admin checks."""
    global _ADMIN_CACHE
    _ADMIN_CACHE.clear()


async def is_group_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """Check if a user is an administrator or owner of the Telegram group (5-minute TTL cache)."""
    now = time.monotonic()
    key = (chat_id, user_id)
    cached = _ADMIN_CACHE.get(key)
    if cached and now < cached[1]:
        return cached[0]

    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        is_adm = member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)

        # Evict oldest entries if cache exceeds bound to prevent unbounded memory growth
        if len(_ADMIN_CACHE) >= _MAX_ADMIN_CACHE_ENTRIES:
            # First remove expired entries
            expired = [k for k, v in _ADMIN_CACHE.items() if now >= v[1]]
            for k in expired:
                _ADMIN_CACHE.pop(k, None)
            # If still over limit, remove oldest 20%
            if len(_ADMIN_CACHE) >= _MAX_ADMIN_CACHE_ENTRIES:
                for k in list(_ADMIN_CACHE.keys())[: (_MAX_ADMIN_CACHE_ENTRIES // 5)]:
                    _ADMIN_CACHE.pop(k, None)

        _ADMIN_CACHE[key] = (is_adm, now + 300.0)
        return is_adm
    except Exception as e:
        logger.warning(f"Error checking group admin status for user {user_id} in {chat_id}: {e}")
        return False



async def get_cached_bot_username(bot: Bot) -> str:
    """Cache bot username to avoid redundant network calls on message moderation."""
    global _CACHED_BOT_USERNAME
    if _CACHED_BOT_USERNAME:
        return _CACHED_BOT_USERNAME
    try:
        bot_info = await bot.get_me()
        _CACHED_BOT_USERNAME = bot_info.username or "bot"
        return _CACHED_BOT_USERNAME
    except Exception:
        return "bot"


_active_background_tasks = set()


def schedule_auto_delete_notice(bot: Bot, chat_id: int, message_id: int, delay_seconds: int):
    """Schedule auto-deletion of temporary notice, retaining strong reference to prevent GC loss."""
    task = asyncio.create_task(auto_delete_notice(bot, chat_id, message_id, delay_seconds))
    _active_background_tasks.add(task)
    task.add_done_callback(_active_background_tasks.discard)
    return task


async def auto_delete_notice(bot: Bot, chat_id: int, message_id: int, delay_seconds: int):
    """Sleep for delay_seconds and quietly delete the temporary warning notice."""
    try:
        await asyncio.sleep(delay_seconds)
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Auto-deleted temporary notice {message_id} in chat {chat_id} after {delay_seconds}s.")
    except (TelegramBadRequest, TelegramForbiddenError) as e:
        logger.debug(f"Notice {message_id} already deleted or forbidden in {chat_id}: {e}")
    except Exception as e:
        logger.error(f"Error auto-deleting notice {message_id} in {chat_id}: {e}", exc_info=True)


async def cleanup_old_moderation_logs(session: AsyncSession, retention_days: Optional[int] = None) -> int:
    """
    Automatically delete moderation logs older than retention_days.
    Reads setting from database or falls back to config.
    """
    if retention_days is None:
        setting = await session.get(Setting, "moderation_log_retention_days")
        if setting and setting.value.isdigit():
            retention_days = int(setting.value)
        else:
            retention_days = settings.MODERATION_LOG_RETENTION_DAYS

    cutoff_date = now_utc() - timedelta(days=retention_days)
    try:
        result = await session.execute(
            delete(ModerationLog).where(ModerationLog.deleted_at < cutoff_date)
        )
        await session.commit()
        deleted_count = result.rowcount or 0
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired moderation logs (older than {retention_days} days).")
        return deleted_count
    except Exception as e:
        logger.error(f"Error cleaning up old moderation logs: {e}", exc_info=True)
        return 0


async def process_group_message(bot: Bot, message: Message, session: AsyncSession) -> bool:
    """
    Main group moderation pipeline:
    1. Check if group message & ignore admins.
    2. Run score-based ad detector with anti-evasion normalization.
    3. Check user roles and active subscriptions.
    4. Apply 24h rolling limit for taxi or 0-free rule for regular users.
    5. Delete ad ONLY if unauthorized and Telegram permissions allow.
    6. Record detailed log ONLY upon successful deletion (safe against DB log errors).
    
    Returns True if message was moderated/deleted, False if allowed.
    """
    # Only moderate groups and supergroups
    if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return False
        
    # Ignore bot's own messages or service messages
    if not message.from_user or message.from_user.is_bot:
        return False

    chat_id = message.chat.id
    user_id = message.from_user.id
    username = _clean_str(message.from_user.username)
    first_name = _clean_str(message.from_user.first_name)
    last_name = _clean_str(message.from_user.last_name)
    original_text = message.text or message.caption or ""

    # Step 1: Check Telegram Chat Admin permissions (never moderate group admins)
    if user_id == settings.ADMIN_ID or await is_group_admin(bot, chat_id, user_id):
        logger.debug(f"User {user_id} is group administrator; skipping moderation.")
        return False

    # Step 2: Analyze message content with multimodal scoring classifier (Tier 1)
    decision: UnifiedModerationDecision = await analyze_message_multimodal(bot, message)
    
    ai_result = None
    if not decision.is_ad:
        # Tier 2: Check if message is suspicious/borderline and group has AI enabled
        eval_text = decision.combined_text or original_text
        has_photo_bytes = bool(decision.metadata and decision.metadata.get("image_bytes"))

        # For photos: multimodal AI is active if global AI is on (unless group explicitly turned AI off)
        # For text: AI is active if explicitly enabled for the group
        if has_photo_bytes:
            ai_allowed = await is_photo_ai_moderation_enabled(session, chat_id)
            needs_ai = True
        else:
            ai_allowed = await is_ai_moderation_enabled(session, chat_id)
            needs_ai = should_escalate_to_ai(
                raw_text=eval_text,
                local_score=decision.score,
                threshold=settings.AD_DETECTION_THRESHOLD,
                extracted_phones=decision.extracted_phones,
                extracted_links=decision.extracted_links,
                detected_locations=decision.detected_locations,
            )

        if needs_ai and ai_allowed:
            logger.info(f"Escalating message {message.message_id} in {chat_id} (media={decision.media_type}, photo_bytes={has_photo_bytes}) to Tier 2 AI...")
            ai_result = await ai_moderation_service.evaluate_message(
                text=eval_text,
                chat_id=chat_id,
                message_id=message.message_id,
                media_type=decision.media_type,
                ocr_text=decision.extracted_ocr_text,
                session=session,
                metadata=decision.metadata,
            )
            # Evaluate threshold
            if ai_result.classification == "AD" and ai_result.confidence >= settings.AI_AD_THRESHOLD:
                decision.is_ad = True
                decision.reason = f"AI aniqlagan reklama ({ai_result.category}): {ai_result.reason} ({ai_result.confidence:.0%})"
                decision.score = max(decision.score, round(ai_result.confidence * 100.0, 1))
                decision.violation_type = "AI_DETECTED_AD"
            else:
                # Log non-ad AI decision and allow message
                await ai_moderation_service.record_log(
                    session=session,
                    chat_id=chat_id,
                    message_id=message.message_id,
                    result=ai_result,
                    was_deleted=False,
                )
                return False
        else:
            return False  # Regular conversation or questions -> allow without touch

    logger.info(
        f"Advertisement detected from user {user_id} (@{username}): "
        f"{decision.reason} (score={decision.score}, type={decision.violation_type}, media={decision.media_type})"
    )

    # Step 3: Get or create user record (with lazy binding of username to telegram_id)
    user = await get_or_create_user(
        session=session,
        telegram_id=user_id,
        username=username,
        first_name=first_name
    )

    # Check bot admin role
    if user.role == "admin":
        return False

    # Step 4: Check if user has an active paid subscription
    has_sub, subscription = await has_active_subscription(session, user.id)
    if has_sub:
        logger.info(f"User {user.id} (@{username}) has active subscription ({subscription.plan}); ad allowed.")
        return False

    # Step 5: Check Role Rules (Taxi vs Regular User)
    bot_username = await get_cached_bot_username(bot)
    mention_display = f"@{username}" if username else f"<a href='tg://user?id={user_id}'>{first_name or 'Foydalanuvchi'}</a>"

    sub_status = subscription.plan if (has_sub and subscription) else "none"
    was_taxi = (user.role == "taxi")

    # Payment link keyboard: [💳 Joylashtirishni to'lash]
    pay_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="💳 Joylashtirishni to'lash",
                url=f"https://t.me/{bot_username}?start=tariffs"
            )
        ]]
    )

    # Determine notice delete delay from DB settings or config fallback
    notice_delay = settings.NOTICE_DELETE_SECONDS
    try:
        t_setting = await session.get(Setting, "notice_delete_seconds")
        if t_setting and t_setting.value and t_setting.value.isdigit():
            notice_delay = int(t_setting.value)
    except Exception:
        pass

    # All message IDs to delete (e.g. all photos/videos in an album)
    target_message_ids = decision.target_message_ids or [message.message_id]
    log_text = decision.combined_text or original_text
    locs_str = ",".join(decision.detected_locations) if decision.detected_locations else None
    phones_str = ",".join(decision.extracted_phones) if decision.extracted_phones else None
    links_str = ",".join(decision.extracted_links) if decision.extracted_links else None
    meta_str = str(decision.metadata) if decision.metadata else None

    # --- TAXI DRIVER RULES ---
    if user.role == "taxi":
        result = await session.execute(
            select(TaxiAdLimit).where(TaxiAdLimit.user_id == user.id)
        )
        taxi_limit = result.scalar_one_or_none()
        if not taxi_limit:
            taxi_limit = TaxiAdLimit(user_id=user.id, last_free_ad_at=None)
            session.add(taxi_limit)
            await session.commit()
            await session.refresh(taxi_limit)

        # Check rolling 24 hours
        if is_past_24_hours(taxi_limit.last_free_ad_at):
            # First free ad of the 24-hour cycle allowed!
            taxi_limit.last_free_ad_at = now_utc()
            await session.commit()
            logger.info(f"Taxi user {user.id} (@{username}) published free 24h advertisement.")
            return False
        else:
            # 24 hours haven't elapsed yet! Delete message(s).
            next_time = next_available_free_ad_time(taxi_limit.last_free_ad_at)
            next_time_str = format_tashkent(next_time)

            violation_type = "TAXI_FREE_LIMIT_EXCEEDED"
            reason = f"Taksi 24 soatlik bepul limit tugagan. {decision.reason}"

            # Attempt physical deletion of all album/message items
            deleted_ok = False
            for mid in target_message_ids:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=mid)
                    deleted_ok = True
                except Exception as e:
                    logger.error(f"Failed to delete taxi ad message {mid} in {chat_id}: {e}")

            # Only log and notify if actual deletion succeeded!
            if deleted_ok:
                if settings.SAVE_MODERATION_LOGS:
                    try:
                        log_entry = ModerationLog(
                            telegram_message_id=message.message_id,
                            chat_id=chat_id,
                            user_id=user_id,
                            username=username,
                            first_name=first_name,
                            last_name=last_name,
                            message_text=log_text,
                            deleted_at=now_utc(),
                            reason=reason,
                            violation_type=violation_type,
                            user_role=user.role,
                            subscription_status=sub_status,
                            was_taxi=True,
                            detector_score=decision.score,
                            media_type=decision.media_type,
                            extracted_ocr_text=decision.extracted_ocr_text or None,
                            detected_locations=locs_str,
                            detected_phones=phones_str,
                            detected_links=links_str,
                            media_metadata=meta_str,
                        )
                        session.add(log_entry)
                        await session.commit()
                    except Exception as log_err:
                        logger.error(f"Error saving moderation log: {log_err}", exc_info=True)
                if ai_result is not None:
                    await ai_moderation_service.record_log(
                        session=session,
                        chat_id=chat_id,
                        message_id=message.message_id,
                        result=ai_result,
                        was_deleted=True,
                    )

                # Send temporary notice (only once for an album, not for each photo in it)
                if not decision.is_album or decision.is_album_leader:
                    notice_text = (
                        f"⚠️ <b>{mention_display}, bugungi bepul reklama limitingizdan foydalangansiz!</b>\n\n"
                        f"⏳ Keyingi bepul reklama: <code>{next_time_str}</code>\n"
                        f"💳 Reklamani cheklovsiz joylashtirish uchun tarif sotib olishingiz mumkin: @{bot_username}"
                    )
                    try:
                        notice = await message.answer(notice_text, reply_markup=pay_keyboard, parse_mode="HTML")
                        schedule_auto_delete_notice(bot, chat_id, notice.message_id, notice_delay)
                    except Exception as e:
                        logger.error(f"Failed to send temporary notice: {e}")

                return True
            else:
                # Could not delete due to lack of permissions
                return False

    # --- REGULAR USER / BUSINESS RULES ---
    else:
        # Commercial advertising is strictly forbidden without active paid tariff
        violation_type = decision.violation_type
        if violation_type in ("NORMAL_MESSAGE", "OTHER_AD_VIOLATION"):
            violation_type = "BUSINESS_AD_WITHOUT_SUBSCRIPTION"
        reason = f"Tarifsiz reklama. {decision.reason}"

        # Attempt physical deletion of all album/message items
        deleted_ok = False
        for mid in target_message_ids:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=mid)
                deleted_ok = True
            except Exception as e:
                logger.error(f"Failed to delete unauthorized ad message {mid} in {chat_id}: {e}")

        # Only log and notify if actual deletion succeeded!
        if deleted_ok:
            if settings.SAVE_MODERATION_LOGS:
                try:
                    log_entry = ModerationLog(
                        telegram_message_id=message.message_id,
                        chat_id=chat_id,
                        user_id=user_id,
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        message_text=log_text,
                        deleted_at=now_utc(),
                        reason=reason,
                        violation_type=violation_type,
                        user_role=user.role,
                        subscription_status=sub_status,
                        was_taxi=False,
                        detector_score=decision.score,
                        media_type=decision.media_type,
                        extracted_ocr_text=decision.extracted_ocr_text or None,
                        detected_locations=locs_str,
                        detected_phones=phones_str,
                        detected_links=links_str,
                        media_metadata=meta_str,
                    )
                    session.add(log_entry)
                    await session.commit()
                except Exception as log_err:
                    logger.error(f"Error saving moderation log: {log_err}", exc_info=True)
            if ai_result is not None:
                await ai_moderation_service.record_log(
                    session=session,
                    chat_id=chat_id,
                    message_id=message.message_id,
                    result=ai_result,
                    was_deleted=True,
                )

            # Send temporary notice (only once for an album)
            if not decision.is_album or decision.is_album_leader:
                notice_text = (
                    f"⚠️ <b>{mention_display}, reklama xabari o'chirildi!</b>\n\n"
                    f"Guruhda reklama joylashtirish faqat faol tarif bilan ruxsat etiladi.\n"
                    f"💳 Tarif sotib olish uchun quyidagi tugmani bosing:"
                )
                try:
                    notice = await message.answer(notice_text, reply_markup=pay_keyboard, parse_mode="HTML")
                    schedule_auto_delete_notice(bot, chat_id, notice.message_id, notice_delay)
                except Exception as e:
                    logger.error(f"Failed to send temporary notice: {e}")

            return True
        else:
            return False
