import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatType

from app.database import async_session_maker
from app.models.user import User
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.services.subscription_service import get_or_create_user
from app.services.payment_service import (
    get_tariff_prices,
    get_payment_details,
    create_payment_request,
    confirm_payment,
    reject_payment,
)
from app.keyboards.payments import (
    get_cancel_payment_keyboard,
    get_admin_payment_review_keyboard,
)
from app.keyboards.user import get_user_inline_menu
from app.utils.time import now_utc, format_tashkent
from app.config import settings

logger = logging.getLogger(__name__)

router = Router(name="payments")


class PaymentStates(StatesGroup):
    waiting_for_receipt = State()


PLAN_TITLES = {
    "1_day": "1 kun (24 soat)",
    "7_days": "7 kun",
    "30_days": "30 kun (1 oy)",
}


@router.callback_query(F.data.startswith("buy_plan:"))
async def on_plan_selected(callback: CallbackQuery, state: FSMContext):
    """User selects a tariff plan."""
    plan = callback.data.split(":")[1]
    
    async with async_session_maker() as session:
        prices = await get_tariff_prices(session)
        payment_info = await get_payment_details(session)

    amount = prices.get(plan, 15000)
    amount_str = f"{amount:,}".replace(",", " ")
    plan_title = PLAN_TITLES.get(plan, plan)

    # Save selected plan in state
    await state.set_state(PaymentStates.waiting_for_receipt)
    await state.update_data(plan=plan, amount=amount)

    text = (
        f"💳 <b>Tanlangan tarif:</b> {plan_title}\n"
        f"💰 <b>To'lov summasi:</b> {amount_str} so'm\n\n"
        f"<b>To'lov uchun rekvizitlar:</b>\n"
        f"💳 Karta raqami: <code>{payment_info['card']}</code>\n"
        f"👤 Qabul qiluvchi: <b>{payment_info['holder']}</b>\n\n"
        f"❗️ <b>Muhim:</b> To'lovni amalga oshirganingizdan so'ng, to'lov cheki "
        f"(skrinshot yoki kvitansiya fayli)ni ushbu botga yuboring."
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_cancel_payment_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_payment")
async def on_cancel_payment(callback: CallbackQuery, state: FSMContext):
    """User cancels payment flow."""
    await state.clear()
    await callback.message.edit_text(
        "❌ To'lov jarayoni bekor qilindi.",
        reply_markup=get_user_inline_menu()
    )
    await callback.answer()


@router.message(PaymentStates.waiting_for_receipt, F.photo)
@router.message(PaymentStates.waiting_for_receipt, F.document)
async def on_receipt_received(message: Message, state: FSMContext, bot: Bot):
    """Handle receipt upload from user."""
    data = await state.get_data()
    plan = data.get("plan", "1_day")
    amount = data.get("amount", 15000)
    plan_title = PLAN_TITLES.get(plan, plan)
    amount_str = f"{amount:,}".replace(",", " ")

    # Determine file_id and type
    if message.photo:
        receipt_file_id = message.photo[-1].file_id
        receipt_type = "photo"
    else:
        receipt_file_id = message.document.file_id
        receipt_type = "document"

    async with async_session_maker() as session:
        user = await get_or_create_user(
            session=session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name
        )
        payment = await create_payment_request(
            session=session,
            user_id=user.id,
            plan=plan,
            amount=amount,
            receipt_file_id=receipt_file_id,
            receipt_type=receipt_type
        )
        payment_id = payment.id

    # Clear state
    await state.clear()

    # Confirm to user
    await message.answer(
        "✅ <b>To'lov cheki qabul qilindi!</b>\n\n"
        "Administrator chekni tekshirgandan so'ng tarifingiz avtomatik faollashtiriladi. "
        "Iltimos, tasdiqlanishini kuting.",
        parse_mode="HTML"
    )

    # Forward receipt to administrator
    admin_id = settings.ADMIN_ID
    if admin_id:
        username_str = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
        caption = (
            f"💳 <b>Yangi to'lov arizasi!</b>\n\n"
            f"👤 Foydalanuvchi: {username_str}\n"
            f"🆔 Telegram ID: <code>{message.from_user.id}</code>\n"
            f"📦 Tanlangan tarif: <b>{plan_title}</b>\n"
            f"💰 Summa: <b>{amount_str} so'm</b>\n"
            f"📅 Vaqt: {format_tashkent(now_utc())}"
        )
        kb = get_admin_payment_review_keyboard(payment_id)
        try:
            if receipt_type == "photo":
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=receipt_file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=kb
                )
            else:
                await bot.send_document(
                    chat_id=admin_id,
                    document=receipt_file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=kb
                )
        except Exception as e:
            logger.error(f"Failed to forward payment receipt to admin {admin_id}: {e}")


@router.callback_query(F.data.startswith("admin_pay:"))
async def on_admin_payment_decision(callback: CallbackQuery, bot: Bot):
    """Admin confirms or rejects payment request."""
    # Ensure caller is the admin
    if callback.from_user.id != settings.ADMIN_ID:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return

    _, action, payment_id_str = callback.data.split(":")
    payment_id = int(payment_id_str)

    async with async_session_maker() as session:
        if action == "confirm":
            payment = await confirm_payment(session, payment_id)
            if not payment:
                await callback.answer("To'lov topilmadi yoki allaqachon ko'rib chiqilgan.", show_alert=True)
                return

            user = await session.get(User, payment.user_id)
            # Find the active subscription to get expiry time
            from app.services.subscription_service import has_active_subscription
            _, sub = await has_active_subscription(session, user.id)
            expiry_str = format_tashkent(sub.expires_at) if sub else "Noma'lum"

            plan_title = PLAN_TITLES.get(payment.plan, payment.plan)

            # Edit admin message
            try:
                await callback.message.edit_caption(
                    caption=f"{callback.message.caption or ''}\n\n✅ <b>TASDIQLANDI</b> (Admin tomonidan faollashtirildi)",
                    parse_mode="HTML",
                    reply_markup=None
                )
            except Exception:
                try:
                    await callback.message.edit_text(
                        text=f"{callback.message.text or ''}\n\n✅ <b>TASDIQLANDI</b> (Admin tomonidan faollashtirildi)",
                        parse_mode="HTML",
                        reply_markup=None
                    )
                except Exception:
                    pass

            # Notify user
            if user and user.telegram_id:
                user_msg = (
                    f"🎉 <b>To'lovingiz muvaffaqiyatli tasdiqlandi!</b>\n\n"
                    f"Sizning <b>{plan_title}</b> tarifi faollashtirildi.\n"
                    f"⏳ Amal qilish muddati: <b>{expiry_str}</b> gacha.\n\n"
                    f"Endi guruhda bemalol reklama e'lonlaringizni joylashtirishingiz mumkin!"
                )
                try:
                    await bot.send_message(chat_id=user.telegram_id, text=user_msg, parse_mode="HTML")
                except Exception as e:
                    logger.warning(f"Could not notify user {user.telegram_id}: {e}")

            await callback.answer("To'lov tasdiqlandi va tarif berildi!", show_alert=True)

        elif action == "reject":
            payment = await reject_payment(session, payment_id)
            if not payment:
                await callback.answer("To'lov topilmadi yoki allaqachon ko'rib chiqilgan.", show_alert=True)
                return

            user = await session.get(User, payment.user_id)

            # Edit admin message
            try:
                await callback.message.edit_caption(
                    caption=f"{callback.message.caption or ''}\n\n❌ <b>RAD ETILDI</b>",
                    parse_mode="HTML",
                    reply_markup=None
                )
            except Exception:
                try:
                    await callback.message.edit_text(
                        text=f"{callback.message.text or ''}\n\n❌ <b>RAD ETILDI</b>",
                        parse_mode="HTML",
                        reply_markup=None
                    )
                except Exception:
                    pass

            # Notify user
            if user and user.telegram_id:
                user_msg = (
                    "❌ <b>Afsuski, yuborilgan to'lov cheki tasdiqlanmadi.</b>\n\n"
                    "Chek noto'g'ri bo'lishi yoki to'lov hisobga tushmagan bo'lishi mumkin. "
                    "Qayta urinib ko'rishingiz yoki administrator bilan bog'lanishingiz mumkin."
                )
                try:
                    await bot.send_message(chat_id=user.telegram_id, text=user_msg, parse_mode="HTML")
                except Exception as e:
                    logger.warning(f"Could not notify user {user.telegram_id}: {e}")

            await callback.answer("To'lov rad etildi.", show_alert=True)
