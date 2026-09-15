from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatType
from sqlalchemy import select

from app.database import async_session_maker
from app.models.user import User
from app.models.taxi_limit import TaxiAdLimit
from app.services.subscription_service import get_or_create_user, has_active_subscription
from app.services.payment_service import get_tariff_prices
from app.keyboards.user import (
    get_user_main_keyboard,
    get_user_inline_menu,
    get_back_to_user_menu,
)
from app.keyboards.payments import get_tariff_choice_keyboard
from app.utils.time import format_tashkent, is_past_24_hours, next_available_free_ad_time
from app.config import settings

router = Router(name="user")


@router.message(F.chat.type == ChatType.PRIVATE, CommandStart())
async def cmd_start(message: Message):
    """Handler for /start in PM."""
    async with async_session_maker() as session:
        user = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )

    first_name = message.from_user.first_name or "foydalanuvchi"
    user_is_admin = (message.from_user.id == settings.ADMIN_ID)
    text = (
        f"👋 <b>Assalomu alaykum, {first_name}!</b>\n\n"
        f"Bu bot guruhdagi reklama xabarlarini tartibga soladi va tozalikni ta'minlaydi.\n\n"
        f"<b>Qoidalar:</b>\n"
        f"🚕 <b>Taksi haydovchilari:</b> har 24 soatda 1 ta bepul reklama berish huquqiga ega.\n"
        f"📢 <b>Biznes / Savdo:</b> guruhda reklama faqat faol tarif bilan ruxsat etiladi.\n\n"
        f"Quyidagi tugmalar orqali kerakli bo'limni tanlang:"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_user_main_keyboard(is_admin=user_is_admin)
    )
    await message.answer(
        "Bo'limni tanlang:",
        reply_markup=get_user_inline_menu(is_admin=user_is_admin)
    )


@router.message(F.chat.type == ChatType.PRIVATE, Command("help"))
async def cmd_help(message: Message):
    """Handler for /help in PM."""
    text = (
        "📖 <b>Botdan foydalanish bo'yicha qo'llanma:</b>\n\n"
        "1. <b>Oddiy foydalanuvchilar</b> guruhda istalgancha suhbatlashishi va savol berishi mumkin. "
        "Masalan: <i>'Kim kartoshka narxini biladi?'</i> yoki <i>'Samarqandga kim boryapti?'</i> kabi savollar o'chirilmaydi.\n\n"
        "2. <b>Taksi haydovchilari</b> har 24 soatda 1 marta bepul e'lon berishi mumkin. "
        "Agar ko'proq reklama bermoqchi bo'lsangiz, qulay tariflardan birini xarid qilishingiz mumkin.\n\n"
        "3. <b>Savdo va xizmatlar (Biznes):</b> Mahsulot yoki xizmatlarni reklama qilish faqat pullik tariflar orqali amalga oshiriladi.\n\n"
        "Buyruqlar:\n"
        "/start - Botni ishga tushirish\n"
        "/help - Yordam va qoidalar"
    )
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "user:menu")
async def cb_user_menu(callback: CallbackQuery):
    """Return to user menu."""
    text = (
        "Kerakli bo'limni tanlang:\n\n"
        "💳 <b>Reklama tariflari</b> — e'lon berish uchun tariflar\n"
        "📊 <b>Mening holatim</b> — obuna va limitlar holati\n"
        "ℹ️ <b>Guruh qoidalari</b> — batafsil tartib-qoidalar"
    )
    user_is_admin = (callback.from_user.id == settings.ADMIN_ID)
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_user_inline_menu(is_admin=user_is_admin)
    )
    await callback.answer()


@router.message(F.chat.type == ChatType.PRIVATE, F.text == "💳 Reklama sotib olish")
@router.callback_query(F.data == "user:tariffs")
async def show_tariffs(event: Message | CallbackQuery):
    """Show available subscription tariffs."""
    async with async_session_maker() as session:
        prices = await get_tariff_prices(session)

    p1 = f"{prices['1_day']:,}".replace(",", " ")
    p7 = f"{prices['7_days']:,}".replace(",", " ")
    p30 = f"{prices['30_days']:,}".replace(",", " ")

    text = (
        "💳 <b>Guruhda reklama joylashtirish tariflari:</b>\n\n"
        f"⚡️ <b>1 kun</b> — {p1} so'm\n"
        f"<i>(24 soat davomida cheklovsiz reklama)</i>\n\n"
        f"🔥 <b>7 kun</b> — {p7} so'm\n"
        f"<i>(7 kun davomida cheklovsiz reklama)</i>\n\n"
        f"👑 <b>30 kun</b> — {p30} so'm\n"
        f"<i>(30 kun davomida cheklovsiz reklama, eng qulay narx!)</i>\n\n"
        "O'zingizga ma'qul bo'lgan tarifni tanlang:"
    )

    kb = get_tariff_choice_keyboard(prices)
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.chat.type == ChatType.PRIVATE, F.text == "📊 Mening holatim")
@router.callback_query(F.data == "user:status")
async def show_user_status(event: Message | CallbackQuery):
    """Show current subscription status and taxi free ad limits."""
    user_id = event.from_user.id
    async with async_session_maker() as session:
        user = await get_or_create_user(
            session=session,
            telegram_id=user_id,
            username=event.from_user.username,
            first_name=event.from_user.first_name
        )
        has_sub, sub = await has_active_subscription(session, user.id)
        
        # Check taxi limits
        result = await session.execute(select(TaxiAdLimit).where(TaxiAdLimit.user_id == user.id))
        taxi_limit = result.scalar_one_or_none()

    role_names = {
        "admin": "👑 Administrator",
        "taxi": "🚕 Taksi haydovchisi",
        "user": "👤 Oddiy foydalanuvchi"
    }
    role_str = role_names.get(user.role, "👤 Oddiy foydalanuvchi")

    if has_sub and sub:
        sub_status = f"✅ Faol ({sub.plan})\nTugash vaqti: <b>{format_tashkent(sub.expires_at)}</b>"
    else:
        sub_status = "❌ Faol tarif mavjud emas"

    extra_info = ""
    if user.role == "taxi":
        if taxi_limit and taxi_limit.last_free_ad_at:
            if is_past_24_hours(taxi_limit.last_free_ad_at):
                extra_info = "\n\n🚕 <b>Taksi bepul e'lon holati:</b> Bepul reklama hozir <b>mavjud</b>!"
            else:
                next_time = next_available_free_ad_time(taxi_limit.last_free_ad_at)
                extra_info = (
                    f"\n\n🚕 <b>Taksi bepul e'lon holati:</b>\n"
                    f"So'nggi bepul reklama: {format_tashkent(taxi_limit.last_free_ad_at)}\n"
                    f"Keyingi bepul reklama: <b>{format_tashkent(next_time)}</b>"
                )
        else:
            extra_info = "\n\n🚕 <b>Taksi bepul e'lon holati:</b> Bepul reklama hozir <b>mavjud</b>!"

    text = (
        f"📊 <b>Sizning profilingiz holati:</b>\n\n"
        f"🆔 Telegram ID: <code>{user.telegram_id}</code>\n"
        f"🎭 Roli: <b>{role_str}</b>\n"
        f"💳 Reklama tarifi: {sub_status}"
        f"{extra_info}"
    )

    kb = get_back_to_user_menu()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.chat.type == ChatType.PRIVATE, F.text == "ℹ️ Guruh qoidalari")
@router.callback_query(F.data == "user:rules")
async def show_rules(event: Message | CallbackQuery):
    """Show group rules."""
    text = (
        "ℹ️ <b>Guruhda e'lon berish qoidalari:</b>\n\n"
        "1. <b>Oddiy a'zolar:</b>\n"
        "— Guruhda erkin muloqot qilishingiz, narxlar va xizmatlar haqida savol berishingiz mumkin.\n"
        "— Tijoriy sotuv, mahsulot va xizmatlarni reklama qilish uchun tarif talab etiladi.\n\n"
        "2. <b>Taksi haydovchilari:</b>\n"
        "— Har 24 soatda 1 ta bepul reklama e'loni berish huquqiga egasiz.\n"
        "— Bepul e'londan keyin 24 soat ichida yuborilgan qayta reklamalar avtomatik o'chiriladi.\n"
        "— Cheklovlarsiz reklama qilish uchun pullik tarif xarid qilishingiz mumkin.\n\n"
        "3. <b>Savdo, do'kon, kafe va ustalar:</b>\n"
        "— Har qanday tijoriy e'lonlar va havolalar faqat faol tarif orqali joylashtiriladi."
    )
    kb = get_back_to_user_menu()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.chat.type == ChatType.PRIVATE, F.text == "📞 Bog'lanish")
@router.callback_query(F.data == "user:contact")
async def show_contact(event: Message | CallbackQuery, bot: Bot):
    """Show contact details."""
    admin_id = settings.ADMIN_ID
    text = (
        "📞 <b>Administrator bilan bog'lanish:</b>\n\n"
        "Savol, taklif yoki to'lov masalalari bo'yicha guruh ma'muriyatiga murojaat qilishingiz mumkin."
    )
    kb = get_back_to_user_menu()
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=kb)
