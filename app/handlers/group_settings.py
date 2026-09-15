import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ChatType

from app.database import async_session_maker
from app.config import settings
from app.services.moderation_service import is_group_admin
from app.services.ai_moderation.group_settings import (
    is_ai_moderation_enabled,
    set_ai_moderation_enabled,
)

logger = logging.getLogger(__name__)

router = Router(name="group_settings")


def get_group_settings_keyboard(chat_id: int, ai_enabled: bool) -> InlineKeyboardMarkup:
    """Build toggle keyboard for group AI moderation."""
    if ai_enabled:
        btn_text = "🤖 AI-ni o'chirish (Выключить AI)"
    else:
        btn_text = "🤖 AI-ni yoqish (Включить AI)"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, callback_data=f"group_ai:toggle:{chat_id}")],
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"group_ai:refresh:{chat_id}")],
    ])


def format_settings_text(chat_title: str, ai_enabled: bool) -> str:
    """Format settings card text."""
    ai_status = "✅ ВКЛ (YONIQ)" if ai_enabled else "❌ ВЫКЛ (O'CHIQ)"
    return (
        f"⚙️ <b>Guruh sozlamalari ({chat_title}):</b>\n\n"
        f"🛡 <b>Anti-reklama:</b> ✅ ВКЛ (Doimiy faol)\n"
        f"🤖 <b>AI-moderatsiya:</b> {ai_status}\n\n"
        f"<i>AI-moderatsiya yoqilganda barcha shubhali e'lonlar "
        f"ikkinchi darajali AI semantik tahlili orqali tekshiriladi.</i>"
    )


@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    Command("settings", "ai", "ai_settings")
)
async def cmd_group_settings(message: Message, bot: Bot):
    """
    Display group moderation settings in group chat.
    Restricted to verified Telegram group administrators.
    """
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Verify admin status
    is_admin = (user_id == settings.ADMIN_ID) or await is_group_admin(bot, chat_id, user_id)
    if not is_admin:
        await message.reply(
            "❌ <b>Ruxsat berilmagan!</b>\n"
            "Guruh sozlamalarini faqat administratorlar o'zgartirishi mumkin.",
            parse_mode="HTML"
        )
        return

    async with async_session_maker() as session:
        ai_enabled = await is_ai_moderation_enabled(session, chat_id)

    chat_title = message.chat.title or "Guruh"
    text = format_settings_text(chat_title, ai_enabled)
    kb = get_group_settings_keyboard(chat_id, ai_enabled)

    await message.reply(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("group_ai:toggle:"))
async def cb_group_ai_toggle(callback: CallbackQuery, bot: Bot):
    """
    Toggle AI moderation for the group with strict server-side admin verification.
    """
    try:
        target_chat_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer("Noto'g'ri so'rov!", show_alert=True)
        return

    user_id = callback.from_user.id

    # Security check: verify user is genuinely an admin in the target chat
    is_admin = (user_id == settings.ADMIN_ID) or await is_group_admin(bot, target_chat_id, user_id)
    if not is_admin:
        await callback.answer(
            "❌ Ruxsat berilmagan!\nFaqat guruh administratorlari AI holatini o'zgartira oladi.",
            show_alert=True
        )
        return

    async with async_session_maker() as session:
        current_state = await is_ai_moderation_enabled(session, target_chat_id)
        new_state = not current_state
        await set_ai_moderation_enabled(session, target_chat_id, new_state)

    chat_title = callback.message.chat.title or "Guruh"
    text = format_settings_text(chat_title, new_state)
    kb = get_group_settings_keyboard(target_chat_id, new_state)

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass

    state_desc = "yoqildi (ВКЛ)" if new_state else "o'chirildi (ВЫКЛ)"
    await callback.answer(f"🤖 AI-moderatsiya {state_desc}!")


@router.callback_query(F.data.startswith("group_ai:refresh:"))
async def cb_group_ai_refresh(callback: CallbackQuery, bot: Bot):
    """Refresh group settings card."""
    try:
        target_chat_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer()
        return

    user_id = callback.from_user.id
    is_admin = (user_id == settings.ADMIN_ID) or await is_group_admin(bot, target_chat_id, user_id)
    if not is_admin:
        await callback.answer("❌ Faqat guruh adminlari uchun.", show_alert=True)
        return

    async with async_session_maker() as session:
        ai_enabled = await is_ai_moderation_enabled(session, target_chat_id)

    chat_title = callback.message.chat.title or "Guruh"
    text = format_settings_text(chat_title, ai_enabled)
    kb = get_group_settings_keyboard(target_chat_id, ai_enabled)

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer("Yangilandi!")


@router.message(
    F.chat.type == ChatType.PRIVATE,
    Command("settings", "ai", "ai_settings")
)
async def cmd_private_settings(message: Message):
    """Guide user when /settings is called in private chat."""
    text = (
        "⚙️ <b>Guruh sozlamalari (Настройки группы):</b>\n\n"
        "Ushbu buyruq <b>Telegram guruhlarida</b> AI-moderatsiyani yoqish yoki o'chirish uchun mo'ljallangan.\n\n"
        "📌 <b>Qanday ishlatiladi?</b>\n"
        "1. Bot admin bo'lgan <b>guruhingizga</b> kiring.\n"
        "2. Guruh ichiga <code>/settings</code> yoki <code>/ai</code> buyrug'ini yozib yuboring.\n"
        "3. Chiqqan tugma orqali AI-moderatsiyani yoqing (ВКЛ).\n\n"
        "💡 <i>Umumiy AI statistikasini ko'rish uchun /admin buyrug'ini yuboring.</i>"
    )
    await message.reply(text, parse_mode="HTML")

