import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatType
from sqlalchemy import select, func, and_

from app.database import async_session_maker
from app.models.user import User
from app.models.subscription import Subscription
from app.models.taxi_limit import TaxiAdLimit
from app.models.payment import Payment
from app.models.setting import Setting
from app.models.moderation_log import ModerationLog
from app.models.ai_moderation_log import AIModerationLog
from app.services.subscription_service import (
    get_or_create_user,
    get_user_by_identifier,
    grant_subscription,
    revoke_subscription,
    has_active_subscription
)
from app.services.payment_service import get_tariff_prices
from app.keyboards.admin import (
    get_admin_main_menu,
    get_admin_taxis_menu,
    get_admin_advertisers_menu,
    get_admin_tariffs_menu,
    get_admin_settings_menu,
    get_admin_cancel_keyboard,
    get_back_to_admin_menu,
)
from app.utils.time import now_utc, format_tashkent, to_tashkent
from app.utils.text import normalize_username
from app.config import settings

logger = logging.getLogger(__name__)

router = Router(name="admin")


# FSM States for Admin Panel
class AdminStates(StatesGroup):
    waiting_for_add_taxi = State()
    waiting_for_remove_taxi = State()
    waiting_for_grant_target = State()
    waiting_for_grant_days = State()
    waiting_for_revoke_target = State()
    waiting_for_user_lookup = State()
    waiting_for_price_value = State()
    waiting_for_card_number = State()
    waiting_for_card_holder = State()
    waiting_for_notice_seconds = State()
    waiting_for_broadcast_text = State()


def is_admin(user_id: int) -> bool:
    """Validate administrator privilege."""
    return user_id == settings.ADMIN_ID


@router.message(F.chat.type == ChatType.PRIVATE, Command("admin"))
@router.message(F.chat.type == ChatType.PRIVATE, F.text.in_(["⚙️ Admin panel", "Admin panel", "admin", "Admin"]))
async def cmd_admin(message: Message):
    """Open main admin menu."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Kechirasiz, sizda administrator huquqi yo'q.")
        return

    text = (
        "🛠 <b>Administrator boshqaruv paneli:</b>\n\n"
        "Guruh moderatsiyasi va reklamalarni boshqarish uchun quyidagi bo'limlardan birini tanlang:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_main_menu())


@router.callback_query(F.data == "admin_menu:main")
async def cb_admin_main(callback: CallbackQuery, state: FSMContext):
    """Return to main admin menu."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return
    await state.clear()
    text = (
        "🛠 <b>Administrator boshqaruv paneli:</b>\n\n"
        "Kerakli bo'limni tanlang:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_main_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_cancel_fsm")
async def cb_admin_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel any active admin FSM input state."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Amal bekor qilindi.",
        reply_markup=get_back_to_admin_menu()
    )
    await callback.answer()


# ==========================================
# 📊 STATISTICS
# ==========================================

@router.message(F.chat.type == ChatType.PRIVATE, Command("stats"))
@router.callback_query(F.data == "admin_menu:stats")
async def show_stats(event: Message | CallbackQuery):
    """Show comprehensive system stats."""
    user_id = event.from_user.id
    if not is_admin(user_id):
        if isinstance(event, Message):
            await event.answer("❌ Ruxsat berilmagan.")
        else:
            await event.answer("Ruxsat berilmagan!", show_alert=True)
        return

    current_time = now_utc()
    # Beginning of today in Tashkent time
    tashkent_now = to_tashkent(current_time)
    tashkent_today_start = tashkent_now.replace(hour=0, minute=0, second=0, microsecond=0)
    utc_today_start = tashkent_today_start.astimezone(timezone.utc)

    async with async_session_maker() as session:
        # Total users
        total_users_res = await session.execute(select(func.count(User.id)))
        total_users = total_users_res.scalar() or 0

        # Total taxis
        total_taxis_res = await session.execute(
            select(func.count(User.id)).where(User.role == "taxi")
        )
        total_taxis = total_taxis_res.scalar() or 0

        # Active subscriptions
        active_subs_res = await session.execute(
            select(func.count(Subscription.id)).where(
                and_(Subscription.active == True, Subscription.expires_at > current_time)
            )
        )
        active_subs = active_subs_res.scalar() or 0

        # Deleted ads today
        deleted_today_res = await session.execute(
            select(func.count(ModerationLog.id)).where(
                ModerationLog.deleted_at >= utc_today_start
            )
        )
        deleted_today = deleted_today_res.scalar() or 0

        # Media moderation breakdown
        photo_ads_res = await session.execute(
            select(func.count(ModerationLog.id)).where(
                ModerationLog.media_type.in_(["photo", "album"])
            )
        )
        photo_ads_count = photo_ads_res.scalar() or 0

        video_ads_res = await session.execute(
            select(func.count(ModerationLog.id)).where(
                ModerationLog.media_type.in_(["video", "animation"])
            )
        )
        video_ads_count = video_ads_res.scalar() or 0

        text_ads_res = await session.execute(
            select(func.count(ModerationLog.id)).where(
                (ModerationLog.media_type == "text") | (ModerationLog.media_type.is_(None))
            )
        )
        text_ads_count = text_ads_res.scalar() or 0

        # Top routes / locations from moderation logs
        top_locs_res = await session.execute(
            select(ModerationLog.detected_locations)
            .where(ModerationLog.detected_locations.isnot(None))
            .order_by(ModerationLog.deleted_at.desc())
            .limit(100)
        )
        loc_counts = {}
        for raw_loc in top_locs_res.scalars().all():
            if raw_loc:
                for l in raw_loc.split(","):
                    l_clean = l.strip().capitalize()
                    if l_clean:
                        loc_counts[l_clean] = loc_counts.get(l_clean, 0) + 1
        sorted_locs = sorted(loc_counts.items(), key=lambda x: x[1], reverse=True)[:4]
        top_routes_str = ", ".join(f"{name} ({cnt})" for name, cnt in sorted_locs) if sorted_locs else "Hozircha yo'q"

        # Payments confirmed today
        paid_today_res = await session.execute(
            select(func.sum(Payment.amount)).where(
                and_(
                    Payment.status == "confirmed",
                    Payment.confirmed_at >= utc_today_start
                )
            )
        )
        paid_today = paid_today_res.scalar() or 0

    paid_str = f"{paid_today:,}".replace(",", " ")

    text = (
        "📊 <b>Guruh va bot statistikasi:</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {total_users}\n"
        f"🚕 <b>Taksistlar:</b> {total_taxis}\n"
        f"💳 <b>Faol pullik obunalar:</b> {active_subs}\n"
        f"🗑 <b>Bugun o'chirilgan reklamalar:</b> {deleted_today}\n"
        f"💰 <b>Bugun qabul qilingan to'lovlar:</b> {paid_str} so'm\n\n"
        "🛡 <b>Media moderatsiya tafsilotlari:</b>\n"
        f"🖼 <b>Rasm / Albom reklamalari:</b> {photo_ads_count} ta\n"
        f"🎬 <b>Video reklamalari:</b> {video_ads_count} ta\n"
        f"📝 <b>Matnli reklamalar:</b> {text_ads_count} ta\n"
        f"📍 <b>Eng ko'p uchragan yo'nalishlar:</b> {top_routes_str}\n\n"
        f"<i>Yangilangan vaqt: {format_tashkent(current_time)}</i>"
    )

    kb = get_back_to_admin_menu()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=kb)


# ==========================================
# 🤖 AI STATISTICS
# ==========================================

@router.message(F.chat.type == ChatType.PRIVATE, Command("ai_stats"))
@router.callback_query(F.data == "admin_menu:ai_stats")
async def show_ai_stats(event: Message | CallbackQuery):
    """Show comprehensive Tier 2 AI moderation statistics."""
    user_id = event.from_user.id
    if not is_admin(user_id):
        if isinstance(event, Message):
            await event.answer("❌ Ruxsat berilmagan.")
        else:
            await event.answer("Ruxsat berilmagan!", show_alert=True)
        return

    async with async_session_maker() as session:
        # Aggregated AI statistics
        total_q = await session.execute(select(func.count(AIModerationLog.id)))
        total_checked = total_q.scalar() or 0

        ad_q = await session.execute(
            select(func.count(AIModerationLog.id)).where(AIModerationLog.classification == "AD")
        )
        ad_count = ad_q.scalar() or 0

        not_ad_q = await session.execute(
            select(func.count(AIModerationLog.id)).where(AIModerationLog.classification == "NOT_AD")
        )
        not_ad_count = not_ad_q.scalar() or 0

        uncertain_q = await session.execute(
            select(func.count(AIModerationLog.id)).where(AIModerationLog.classification == "UNCERTAIN")
        )
        uncertain_count = uncertain_q.scalar() or 0

        error_q = await session.execute(
            select(func.count(AIModerationLog.id)).where(AIModerationLog.error.isnot(None))
        )
        error_count = error_q.scalar() or 0

        last_error_q = await session.execute(
            select(AIModerationLog.error).where(AIModerationLog.error.isnot(None)).order_by(AIModerationLog.id.desc()).limit(1)
        )
        last_error = last_error_q.scalar()

        deleted_q = await session.execute(
            select(func.count(AIModerationLog.id)).where(AIModerationLog.was_deleted == True)
        )
        deleted_count = deleted_q.scalar() or 0

        avg_conf_q = await session.execute(
            select(func.avg(AIModerationLog.confidence)).where(AIModerationLog.error.is_(None))
        )
        avg_conf_val = avg_conf_q.scalar() or 0.0
        avg_conf = avg_conf_val * 100.0

        avg_time_q = await session.execute(
            select(func.avg(AIModerationLog.response_time_ms)).where(AIModerationLog.response_time_ms > 0)
        )
        avg_time = avg_time_q.scalar() or 0.0

    global_ai_status = "✅ ВКЛ (Yoniq)" if settings.AI_ENABLED else "❌ ВЫКЛ (O'chiq)"
    error_line = f"• ⚠️ <b>AI Xatolari (Ошибки):</b> {error_count} ta"
    if last_error:
        error_line += f" (<code>{last_error}</code>)"

    text = (
        "🤖 <b>AI Moderatsiya Statistikasi (Tier 2):</b>\n\n"
        f"🌐 <b>Global AI holati:</b> {global_ai_status}\n"
        f"⚙️ <b>Provayder:</b> <code>{settings.AI_PROVIDER}</code>\n"
        f"🧠 <b>Model:</b> <code>{settings.AI_MODEL}</code>\n"
        f"🎯 <b>O'chirish chegarasi:</b> <code>{settings.AI_AD_THRESHOLD:.0%}</code>\n\n"
        f"📊 <b>Ko'rsatkichlar:</b>\n"
        f"• 🔍 <b>Jami tekshirilgan (Проверено AI):</b> {total_checked} ta\n"
        f"• 🚫 <b>Reklama (AD):</b> {ad_count} ta\n"
        f"• ✅ <b>Oddiy xabar (NOT_AD):</b> {not_ad_count} ta\n"
        f"• ❓ <b>Noaniq (UNCERTAIN):</b> {uncertain_count} ta\n"
        f"{error_line}\n"

        f"• 🗑 <b>AI o'chirgan (Удалено AI):</b> {deleted_count} ta\n"
        f"• 📈 <b>O'rtacha ishonch (Средняя уверенность):</b> {avg_conf:.1f}%\n"
        f"• ⏱ <b>O'rtacha javob vaqti:</b> {avg_time:.0f} ms\n\n"
        f"<i>Eslatma: Guruhda AI-ni boshqarish uchun guruhda /settings yoki /ai buyrug'ini yuboring.</i>"
    )

    kb = get_back_to_admin_menu()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=kb)


# ==========================================
# 🚕 TAXI MANAGEMENT
# ==========================================

@router.callback_query(F.data == "admin_menu:taxis")
async def cb_admin_taxis(callback: CallbackQuery):
    """Show taxi options."""
    if not is_admin(callback.from_user.id):
        return
    text = (
        "🚕 <b>Taksistlarni boshqarish bo'limi:</b>\n\n"
        "— Taksistlar 24 soatda 1 ta bepul reklama berishi mumkin.\n"
        "— Qo'shish uchun username (@taxi_driver) yoki Telegram ID kiriting."
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_taxis_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_taxi:add")
async def cb_taxi_add_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_add_taxi)
    text = (
        "🚕 <b>Taksist qo'shish:</b>\n\n"
        "Taksistning <b>@username</b> yoki <b>Telegram ID</b> sini yuboring:\n"
        "<i>(Masalan: @taxi_ali yoki 123456789)</i>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_cancel_keyboard())
    await callback.answer()


@router.message(AdminStates.waiting_for_add_taxi)
async def process_taxi_add(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    identifier = message.text.strip()
    
    async with async_session_maker() as session:
        user = await get_user_by_identifier(session, identifier)
        if not user:
            # Create user with role taxi
            if identifier.lstrip('-').isdigit():
                user = User(telegram_id=int(identifier), role="taxi")
            else:
                clean_name = normalize_username(identifier)
                user = User(username=clean_name, role="taxi")
            session.add(user)
        else:
            user.role = "taxi"
            
        await session.commit()
        await session.refresh(user)

    await state.clear()
    target = f"@{user.username}" if user.username else f"ID: {user.telegram_id}"
    await message.answer(
        f"✅ <b>Taksist muvaffaqiyatli qo'shildi:</b> {target}\n"
        f"Unga har 24 soatda 1 ta bepul reklama ruxsati berildi.",
        parse_mode="HTML",
        reply_markup=get_back_to_admin_menu()
    )


@router.message(F.chat.type == ChatType.PRIVATE, Command("add_taxi"))
async def cmd_add_taxi(message: Message):
    """Shortcut command: /add_taxi @username or /add_taxi 123456789"""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Format: <code>/add_taxi @username</code> yoki <code>/add_taxi 123456789</code>", parse_mode="HTML")
        return

    identifier = parts[1].strip()
    async with async_session_maker() as session:
        user = await get_user_by_identifier(session, identifier)
        if not user:
            if identifier.lstrip('-').isdigit():
                user = User(telegram_id=int(identifier), role="taxi")
            else:
                user = User(username=normalize_username(identifier), role="taxi")
            session.add(user)
        else:
            user.role = "taxi"
        await session.commit()
        await session.refresh(user)

    target = f"@{user.username}" if user.username else f"ID: {user.telegram_id}"
    await message.answer(f"✅ Taksist qo'shildi: {target}", parse_mode="HTML")


@router.callback_query(F.data == "admin_taxi:remove")
async def cb_taxi_remove_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_remove_taxi)
    text = (
        "➖ <b>Taksistni o'chirish:</b>\n\n"
        "O'chirmoqchi bo'lgan taksistning <b>@username</b> yoki <b>Telegram ID</b> sini yuboring:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_cancel_keyboard())
    await callback.answer()


@router.message(AdminStates.waiting_for_remove_taxi)
async def process_taxi_remove(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    identifier = message.text.strip()
    async with async_session_maker() as session:
        user = await get_user_by_identifier(session, identifier)
        if not user or user.role != "taxi":
            await message.answer("❌ Taksist topilmadi.", reply_markup=get_back_to_admin_menu())
            await state.clear()
            return
        user.role = "user"
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Foydalanuvchi taksistlar ro'yxatidan chiqarildi.", reply_markup=get_back_to_admin_menu())


@router.message(F.chat.type == ChatType.PRIVATE, Command("remove_taxi"))
async def cmd_remove_taxi(message: Message):
    """Shortcut command: /remove_taxi @username"""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Format: <code>/remove_taxi @username</code>", parse_mode="HTML")
        return

    identifier = parts[1].strip()
    async with async_session_maker() as session:
        user = await get_user_by_identifier(session, identifier)
        if not user or user.role != "taxi":
            await message.answer("❌ Taksist topilmadi.")
            return
        user.role = "user"
        await session.commit()

    await message.answer(f"✅ Taksist o'chirildi: {identifier}")


@router.callback_query(F.data == "admin_taxi:list")
async def cb_taxi_list(callback: CallbackQuery):
    """Show list of taxi drivers."""
    if not is_admin(callback.from_user.id):
        return
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.role == "taxi").limit(50)
        )
        taxis = result.scalars().all()

    if not taxis:
        text = "🚕 Hozircha birorta ham taksist ro'yxatga olinmagan."
    else:
        lines = ["🚕 <b>Ro'yxatdagi taksistlar (oxirgi 50 ta):</b>\n"]
        for idx, t in enumerate(taxis, 1):
            name = f"@{t.username}" if t.username else f"ID: {t.telegram_id}"
            first = f" ({t.first_name})" if t.first_name else ""
            lines.append(f"{idx}. {name}{first}")
        text = "\n".join(lines)

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_taxis_menu())
    await callback.answer()


# ==========================================
# 📢 ADVERTISERS & SUBSCRIPTIONS
# ==========================================

@router.callback_query(F.data == "admin_menu:advertisers")
async def cb_admin_advertisers(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    text = (
        "📢 <b>Reklamachilar va obunalar bo'limi:</b>\n\n"
        "— Foydalanuvchilarga qo'lda tarif berish yoki bekor qilish;\n"
        "— Faol obunalar ro'yxatini ko'rish."
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_advertisers_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_sub:grant")
async def cb_grant_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_grant_target)
    text = (
        "➕ <b>Tarif berish:</b>\n\n"
        "Foydalanuvchining <b>@username</b> yoki <b>Telegram ID</b> sini kiriting:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_cancel_keyboard())
    await callback.answer()


@router.message(AdminStates.waiting_for_grant_target)
async def process_grant_target(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    target = message.text.strip()
    await state.update_data(target=target)
    await state.set_state(AdminStates.waiting_for_grant_days)
    text = (
        "Necha kunga tarif bermoqchisiz?\n"
        "Tanlang yoki kun sonini yozing: <b>1</b>, <b>7</b>, <b>30</b>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_cancel_keyboard())


@router.message(AdminStates.waiting_for_grant_days)
async def process_grant_days(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    target = data.get("target")
    days_input = message.text.strip()

    plan_map = {"1": "1_day", "7": "7_days", "30": "30_days"}
    plan = plan_map.get(days_input, "1_day")

    async with async_session_maker() as session:
        user = await get_user_by_identifier(session, target)
        if not user:
            # Create user
            if target.lstrip('-').isdigit():
                user = User(telegram_id=int(target), role="user")
            else:
                user = User(username=normalize_username(target), role="user")
            session.add(user)
            await session.commit()
            await session.refresh(user)

        sub = await grant_subscription(session, user.id, plan, price=0)
        expiry_str = format_tashkent(sub.expires_at)

    await state.clear()
    target_str = f"@{user.username}" if user.username else f"ID: {user.telegram_id}"
    await message.answer(
        f"✅ <b>Tarif berildi!</b>\n\n"
        f"👤 Foydalanuvchi: {target_str}\n"
        f"📦 Tarif: <b>{plan}</b>\n"
        f"⏳ Amal qilish muddati: <b>{expiry_str}</b> gacha",
        parse_mode="HTML",
        reply_markup=get_back_to_admin_menu()
    )

    # Notify user if tg_id available
    if user.telegram_id:
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=(
                    f"🎉 <b>Administrator sizga {plan} tarifini taqdim etdi!</b>\n"
                    f"Amal qilish muddati: <b>{expiry_str}</b> gacha.\n"
                    f"Guruhda bemalol reklama joylashtirishingiz mumkin."
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.message(F.chat.type == ChatType.PRIVATE, Command("grant"))
async def cmd_grant(message: Message, bot: Bot):
    """Shortcut: /grant @username 7"""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Format: <code>/grant @username <1|7|30></code>", parse_mode="HTML")
        return

    target, days = parts[1].strip(), parts[2].strip()
    plan_map = {"1": "1_day", "7": "7_days", "30": "30_days"}
    plan = plan_map.get(days, "1_day")

    async with async_session_maker() as session:
        user = await get_user_by_identifier(session, target)
        if not user:
            if target.lstrip('-').isdigit():
                user = User(telegram_id=int(target), role="user")
            else:
                user = User(username=normalize_username(target), role="user")
            session.add(user)
            await session.commit()
            await session.refresh(user)

        sub = await grant_subscription(session, user.id, plan, price=0)
        expiry_str = format_tashkent(sub.expires_at)

    await message.answer(
        f"✅ Tarif berildi: {target} ({plan}, {expiry_str} gacha)",
        parse_mode="HTML"
    )
    if user.telegram_id:
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=f"🎉 Administrator sizga <b>{plan}</b> tarifini faollashtirdi! Muddat: {expiry_str} gacha.",
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.callback_query(F.data == "admin_sub:revoke")
async def cb_revoke_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_revoke_target)
    text = (
        "➖ <b>Tarifni bekor qilish:</b>\n\n"
        "Foydalanuvchining <b>@username</b> yoki <b>Telegram ID</b> sini kiriting:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_cancel_keyboard())
    await callback.answer()


@router.message(AdminStates.waiting_for_revoke_target)
async def process_revoke_target(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    target = message.text.strip()
    async with async_session_maker() as session:
        user = await get_user_by_identifier(session, target)
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi.", reply_markup=get_back_to_admin_menu())
            await state.clear()
            return
        revoked = await revoke_subscription(session, user.id)

    await state.clear()
    if revoked:
        await message.answer("✅ Foydalanuvchining faol obunasi bekor qilindi.", reply_markup=get_back_to_admin_menu())
    else:
        await message.answer("ℹ️ Ushbu foydalanuvchida faol obuna mavjud emas edi.", reply_markup=get_back_to_admin_menu())


@router.message(F.chat.type == ChatType.PRIVATE, Command("revoke"))
async def cmd_revoke(message: Message):
    """Shortcut: /revoke @username"""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Format: <code>/revoke @username</code>", parse_mode="HTML")
        return

    target = parts[1].strip()
    async with async_session_maker() as session:
        user = await get_user_by_identifier(session, target)
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi.")
            return
        revoked = await revoke_subscription(session, user.id)

    if revoked:
        await message.answer(f"✅ Obuna bekor qilindi: {target}")
    else:
        await message.answer(f"ℹ️ {target} da faol obuna yo'q.")


@router.callback_query(F.data == "admin_sub:list")
async def cb_active_subs_list(callback: CallbackQuery):
    """List active subscriptions."""
    if not is_admin(callback.from_user.id):
        return
    current_time = now_utc()
    async with async_session_maker() as session:
        result = await session.execute(
            select(Subscription, User)
            .join(User, Subscription.user_id == User.id)
            .where(and_(Subscription.active == True, Subscription.expires_at > current_time))
            .order_by(Subscription.expires_at.asc())
            .limit(50)
        )
        subs = result.all()

    if not subs:
        text = "💳 Hozirda faol obunalar mavjud emas."
    else:
        lines = ["💳 <b>Faol pullik obunalar:</b>\n"]
        for idx, (s, u) in enumerate(subs, 1):
            name = f"@{u.username}" if u.username else f"ID: {u.telegram_id}"
            exp = format_tashkent(s.expires_at)
            lines.append(f"{idx}. {name} — <b>{s.plan}</b> ({exp} gacha)")
        text = "\n".join(lines)

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_advertisers_menu())
    await callback.answer()


# ==========================================
# 💳 TARIFF PRICES
# ==========================================

@router.callback_query(F.data == "admin_menu:tariffs")
async def cb_admin_tariffs(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    async with async_session_maker() as session:
        prices = await get_tariff_prices(session)

    p1 = f"{prices['1_day']:,}".replace(",", " ")
    p7 = f"{prices['7_days']:,}".replace(",", " ")
    p30 = f"{prices['30_days']:,}".replace(",", " ")

    text = (
        "💳 <b>Amaldagi tarif narxlari:</b>\n\n"
        f"⚡️ 1 kun: <b>{p1} so'm</b>\n"
        f"🔥 7 kun: <b>{p7} so'm</b>\n"
        f"👑 30 kun: <b>{p30} so'm</b>\n\n"
        "Narxni o'zgartirish uchun kerakli tugmani bosing:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_tariffs_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_price:"))
async def cb_price_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    plan = callback.data.split(":")[1]
    await state.update_data(change_plan=plan)
    await state.set_state(AdminStates.waiting_for_price_value)
    text = f"✏️ <b>{plan}</b> tarifi uchun yangi narxni faqat raqamlarda kiriting (so'mda):\n<i>Masalan: 40000</i>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_cancel_keyboard())
    await callback.answer()


@router.message(AdminStates.waiting_for_price_value)
async def process_new_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    val = message.text.strip().replace(" ", "")
    if not val.isdigit():
        await message.answer("❌ Iltimos, narxni faqat butun raqamlar bilan kiriting:", reply_markup=get_admin_cancel_keyboard())
        return

    data = await state.get_data()
    plan = data.get("change_plan", "1_day")
    key = f"price_{plan}"

    async with async_session_maker() as session:
        setting = await session.get(Setting, key)
        if not setting:
            setting = Setting(key=key, value=val)
            session.add(setting)
        else:
            setting.value = val
        await session.commit()

    await state.clear()
    num_str = f"{int(val):,}".replace(",", " ")
    await message.answer(
        f"✅ <b>{plan}</b> tarifi narxi <b>{num_str} so'm</b> ga o'zgartirildi.",
        parse_mode="HTML",
        reply_markup=get_back_to_admin_menu()
    )


@router.message(F.chat.type == ChatType.PRIVATE, Command("set_price"))
async def cmd_set_price(message: Message):
    """Shortcut: /set_price <1|7|30> <amount>"""
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Format: <code>/set_price <1|7|30> <summa></code>", parse_mode="HTML")
        return

    plan_map = {"1": "1_day", "7": "7_days", "30": "30_days"}
    plan = plan_map.get(parts[1], "1_day")
    amount = parts[2].strip()

    if not amount.isdigit():
        await message.answer("❌ Narx faqat raqam bo'lishi kerak.")
        return

    key = f"price_{plan}"
    async with async_session_maker() as session:
        setting = await session.get(Setting, key)
        if not setting:
            setting = Setting(key=key, value=amount)
            session.add(setting)
        else:
            setting.value = amount
        await session.commit()

    await message.answer(f"✅ {plan} narxi {amount} so'm qilindi.")


# ==========================================
# 👥 USER LOOKUP
# ==========================================

@router.callback_query(F.data == "admin_menu:users")
async def cb_user_lookup_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_user_lookup)
    text = (
        "👥 <b>Foydalanuvchini tekshirish:</b>\n\n"
        "Foydalanuvchining <b>@username</b> yoki <b>Telegram ID</b> sini yuboring:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_cancel_keyboard())
    await callback.answer()


@router.message(AdminStates.waiting_for_user_lookup)
@router.message(F.chat.type == ChatType.PRIVATE, Command("user"))
async def process_user_lookup(message: Message, state: Optional[FSMContext] = None):
    if not is_admin(message.from_user.id):
        return
    if state:
        await state.clear()

    if message.text.startswith("/user"):
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Format: <code>/user @username</code> yoki <code>/user 123456789</code>", parse_mode="HTML")
            return
        identifier = parts[1].strip()
    else:
        identifier = message.text.strip()

    async with async_session_maker() as session:
        user = await get_user_by_identifier(session, identifier)
        if not user:
            await message.answer("❌ Foydalanuvchi bazadan topilmadi.", reply_markup=get_back_to_admin_menu())
            return

        has_sub, sub = await has_active_subscription(session, user.id)
        result = await session.execute(select(TaxiAdLimit).where(TaxiAdLimit.user_id == user.id))
        taxi_limit = result.scalar_one_or_none()

    sub_info = f"✅ Faol ({sub.plan}) — {format_tashkent(sub.expires_at)} gacha" if has_sub and sub else "❌ Yo'q"
    taxi_info = ""
    if user.role == "taxi":
        last_ad = format_tashkent(taxi_limit.last_free_ad_at) if taxi_limit and taxi_limit.last_free_ad_at else "Hali berilmagan"
        taxi_info = f"\n🚕 So'nggi bepul e'lon: {last_ad}"

    text = (
        f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
        f"🆔 Baza ID: {user.id}\n"
        f"🆔 Telegram ID: <code>{user.telegram_id}</code>\n"
        f"👤 Username: @{user.username or 'Mavjud emas'}\n"
        f"🎭 Roli: <b>{user.role}</b>\n"
        f"💳 Faol obuna: {sub_info}"
        f"{taxi_info}\n"
        f"📅 Ro'yxatdan o'tgan: {format_tashkent(user.created_at)}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_back_to_admin_menu())


# ==========================================
# ⚙️ SETTINGS
# ==========================================

@router.callback_query(F.data == "admin_menu:settings")
async def cb_admin_settings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    async with async_session_maker() as session:
        c_set = await session.get(Setting, "payment_card")
        h_set = await session.get(Setting, "payment_card_holder")
        t_set = await session.get(Setting, "notice_delete_seconds")

    card = c_set.value if c_set else settings.PAYMENT_CARD
    holder = h_set.value if h_set else settings.PAYMENT_CARD_HOLDER
    notice_time = t_set.value if t_set else str(settings.NOTICE_DELETE_SECONDS)

    text = (
        "⚙️ <b>Tizim sozlamalari:</b>\n\n"
        f"💳 <b>Karta raqami:</b> <code>{card}</code>\n"
        f"👤 <b>Karta egasi:</b> <b>{holder}</b>\n"
        f"⏱ <b>Ogohlantirish xabarini o'chirish vaqti:</b> <b>{notice_time} soniya</b>\n\n"
        "O'zgartirmoqchi bo'lgan parametrni tanlang:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_settings_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_set:card")
async def cb_set_card_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_card_number)
    text = "💳 Yangi karta raqamini kiriting (masalan: <code>8600 1234 5678 9012</code>):"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_cancel_keyboard())
    await callback.answer()


@router.message(AdminStates.waiting_for_card_number)
async def process_new_card(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    card = message.text.strip()
    async with async_session_maker() as session:
        setting = await session.get(Setting, "payment_card")
        if not setting:
            setting = Setting(key="payment_card", value=card)
            session.add(setting)
        else:
            setting.value = card
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Karta raqami yangilandi: <code>{card}</code>", parse_mode="HTML", reply_markup=get_back_to_admin_menu())


@router.callback_query(F.data == "admin_set:holder")
async def cb_set_holder_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_card_holder)
    text = "👤 Karta egasining Ism Familiyasini kiriting:"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_cancel_keyboard())
    await callback.answer()


@router.message(AdminStates.waiting_for_card_holder)
async def process_new_holder(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    holder = message.text.strip()
    async with async_session_maker() as session:
        setting = await session.get(Setting, "payment_card_holder")
        if not setting:
            setting = Setting(key="payment_card_holder", value=holder)
            session.add(setting)
        else:
            setting.value = holder
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Karta egasi yangilandi: <b>{holder}</b>", parse_mode="HTML", reply_markup=get_back_to_admin_menu())


@router.callback_query(F.data == "admin_set:notice_time")
async def cb_set_notice_time_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_notice_seconds)
    text = "⏱ Guruhdagi ogohlantirish xabari necha soniyadan so'ng o'chirilishi kerak? (masalan: 10):"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_cancel_keyboard())
    await callback.answer()


@router.message(AdminStates.waiting_for_notice_seconds)
async def process_new_notice_time(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    val = message.text.strip()
    if not val.isdigit() or int(val) < 1:
        await message.answer("❌ Butun musbat son kiriting (masalan: 10):", reply_markup=get_admin_cancel_keyboard())
        return
    async with async_session_maker() as session:
        setting = await session.get(Setting, "notice_delete_seconds")
        if not setting:
            setting = Setting(key="notice_delete_seconds", value=val)
            session.add(setting)
        else:
            setting.value = val
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Xabar o'chirish vaqti <b>{val} soniya</b> ga o'rnatildi.", parse_mode="HTML", reply_markup=get_back_to_admin_menu())


# ==========================================
# 📢 BROADCAST
# ==========================================

@router.callback_query(F.data == "admin_menu:broadcast")
async def cb_broadcast_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    text = (
        "📢 <b>Barcha foydalanuvchilarga xabar yuborish:</b>\n\n"
        "Xabar matnini kiriting:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_cancel_keyboard())
    await callback.answer()


@router.message(AdminStates.waiting_for_broadcast_text)
@router.message(F.chat.type == ChatType.PRIVATE, Command("broadcast"))
async def process_broadcast(message: Message, state: Optional[FSMContext] = None, bot: Bot = None):
    if not is_admin(message.from_user.id):
        return
    if state:
        await state.clear()

    if message.text.startswith("/broadcast"):
        broadcast_text = message.text[len("/broadcast"):].strip()
        if not broadcast_text:
            await message.answer("Format: <code>/broadcast Matn</code>", parse_mode="HTML")
            return
    else:
        broadcast_text = message.text.strip()

    async with async_session_maker() as session:
        result = await session.execute(
            select(User.telegram_id).where(User.telegram_id.isnot(None))
        )
        user_ids = result.scalars().all()

    sent = 0
    failed = 0
    for uid in user_ids:
        if uid == message.from_user.id:
            continue
        try:
            await bot.send_message(chat_id=uid, text=broadcast_text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        f"📢 <b>Xabar yuborildi!</b>\n\n"
        f"✅ Muvaffaqiyatli: {sent}\n"
        f"❌ Yetib bormadi (bloklangan): {failed}",
        parse_mode="HTML",
        reply_markup=get_back_to_admin_menu()
    )





