from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_admin_main_menu() -> InlineKeyboardMarkup:
    """Main Admin Panel Inline Keyboard."""
    buttons = [
        [
            InlineKeyboardButton(text="🚕 Taksistlar", callback_data="admin_menu:taxis"),
            InlineKeyboardButton(text="📢 Reklamachilar", callback_data="admin_menu:advertisers")
        ],
        [
            InlineKeyboardButton(text="💳 Tariflar", callback_data="admin_menu:tariffs"),
            InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_menu:users")
        ],
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_menu:stats"),
            InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin_menu:settings")
        ],
        [
            InlineKeyboardButton(text="📋 Moderatsiya jurnali", callback_data="admin_logs:page:1")
        ],
        [
            InlineKeyboardButton(text="📢 Xabar tarqatish (Broadcast)", callback_data="admin_menu:broadcast")
        ],
        [
            InlineKeyboardButton(text="🏠 Foydalanuvchi menyusi", callback_data="user:menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_taxis_menu() -> InlineKeyboardMarkup:
    """Taxi management menu."""
    buttons = [
        [
            InlineKeyboardButton(text="➕ Taksist qo'shish", callback_data="admin_taxi:add"),
            InlineKeyboardButton(text="➖ O'chirish", callback_data="admin_taxi:remove")
        ],
        [
            InlineKeyboardButton(text="📋 Taksistlar ro'yxati", callback_data="admin_taxi:list")
        ],
        [
            InlineKeyboardButton(text="🔙 Asosiy admin menyu", callback_data="admin_menu:main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_advertisers_menu() -> InlineKeyboardMarkup:
    """Advertisers / subscriptions menu."""
    buttons = [
        [
            InlineKeyboardButton(text="➕ Tarif berish", callback_data="admin_sub:grant"),
            InlineKeyboardButton(text="➖ Tarifni bekor qilish", callback_data="admin_sub:revoke")
        ],
        [
            InlineKeyboardButton(text="📋 Faol obunalar", callback_data="admin_sub:list")
        ],
        [
            InlineKeyboardButton(text="🔙 Asosiy admin menyu", callback_data="admin_menu:main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_tariffs_menu() -> InlineKeyboardMarkup:
    """Tariffs price setting menu."""
    buttons = [
        [InlineKeyboardButton(text="✏️ 1 kun narxini o'zgartirish", callback_data="admin_price:1_day")],
        [InlineKeyboardButton(text="✏️ 7 kun narxini o'zgartirish", callback_data="admin_price:7_days")],
        [InlineKeyboardButton(text="✏️ 30 kun narxini o'zgartirish", callback_data="admin_price:30_days")],
        [InlineKeyboardButton(text="🔙 Asosiy admin menyu", callback_data="admin_menu:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_settings_menu() -> InlineKeyboardMarkup:
    """Settings menu."""
    buttons = [
        [InlineKeyboardButton(text="💳 Karta raqamini o'zgartirish", callback_data="admin_set:card")],
        [InlineKeyboardButton(text="👤 Karta egasini o'zgartirish", callback_data="admin_set:holder")],
        [InlineKeyboardButton(text="⏱ Xabar o'chirish vaqtini o'zgartirish", callback_data="admin_set:notice_time")],
        [InlineKeyboardButton(text="🔙 Asosiy admin menyu", callback_data="admin_menu:main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_logs_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Pagination and action keyboard for moderation logs."""
    buttons = []
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"admin_logs:page:{page - 1}"))
    nav_row.append(InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"admin_logs:page:{page}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="▶️ Oldinga", callback_data=f"admin_logs:page:{page + 1}"))
    buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text="🗑 Jurnalni tozalash", callback_data="admin_logs:clear_confirm")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Asosiy admin menyu", callback_data="admin_menu:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_clear_logs_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirmation prompt before clearing moderation logs."""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Ha, butunlay tozalansin", callback_data="admin_logs:clear_execute"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_logs:page:1")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_cancel_keyboard() -> InlineKeyboardMarkup:
    """Cancel admin input operation button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_cancel_fsm")]
    ])


def get_back_to_admin_menu() -> InlineKeyboardMarkup:
    """Simple back to admin main menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Asosiy admin menyu", callback_data="admin_menu:main")]
    ])
