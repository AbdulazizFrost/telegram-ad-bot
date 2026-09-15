from typing import Dict
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_tariff_choice_keyboard(prices: Dict[str, int]) -> InlineKeyboardMarkup:
    """Keyboard allowing user to pick a tariff plan."""
    p1 = f"{prices.get('1_day', 15000):,}".replace(",", " ")
    p7 = f"{prices.get('7_days', 35000):,}".replace(",", " ")
    p30 = f"{prices.get('30_days', 100000):,}".replace(",", " ")

    buttons = [
        [InlineKeyboardButton(text=f"⚡️ 1 kun — {p1} so'm", callback_data="buy_plan:1_day")],
        [InlineKeyboardButton(text=f"🔥 7 kun — {p7} so'm", callback_data="buy_plan:7_days")],
        [InlineKeyboardButton(text=f"👑 30 kun — {p30} so'm", callback_data="buy_plan:30_days")],
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="user:menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_payment_keyboard() -> InlineKeyboardMarkup:
    """Cancel payment flow button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ To'lovni bekor qilish", callback_data="cancel_payment")]
    ])


def get_admin_payment_review_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    """Admin action buttons on payment receipts."""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admin_pay:confirm:{payment_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"admin_pay:reject:{payment_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
