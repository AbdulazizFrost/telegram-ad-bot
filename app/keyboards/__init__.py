from app.keyboards.user import (
    get_user_main_keyboard,
    get_user_inline_menu,
    get_back_to_user_menu,
)
from app.keyboards.payments import (
    get_tariff_choice_keyboard,
    get_cancel_payment_keyboard,
    get_admin_payment_review_keyboard,
)
from app.keyboards.admin import (
    get_admin_main_menu,
    get_admin_taxis_menu,
    get_admin_advertisers_menu,
    get_admin_tariffs_menu,
    get_admin_settings_menu,
    get_admin_cancel_keyboard,
    get_back_to_admin_menu,
)

__all__ = [
    "get_user_main_keyboard",
    "get_user_inline_menu",
    "get_back_to_user_menu",
    "get_tariff_choice_keyboard",
    "get_cancel_payment_keyboard",
    "get_admin_payment_review_keyboard",
    "get_admin_main_menu",
    "get_admin_taxis_menu",
    "get_admin_advertisers_menu",
    "get_admin_tariffs_menu",
    "get_admin_settings_menu",
    "get_admin_cancel_keyboard",
    "get_back_to_admin_menu",
]
