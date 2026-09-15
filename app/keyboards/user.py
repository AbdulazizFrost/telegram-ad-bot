from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_user_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Bottom persistent menu for private chat."""
    kb = [
        [KeyboardButton(text="💳 Reklama sotib olish"), KeyboardButton(text="📊 Mening holatim")],
        [KeyboardButton(text="ℹ️ Guruh qoidalari"), KeyboardButton(text="📞 Bog'lanish")]
    ]
    if is_admin:
        kb.append([KeyboardButton(text="⚙️ Admin panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_user_inline_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Inline menu for /start command in PM."""
    buttons = [
        [InlineKeyboardButton(text="💳 Reklama tariflari", callback_data="user:tariffs")],
        [InlineKeyboardButton(text="📊 Mening holatim", callback_data="user:status")],
        [InlineKeyboardButton(text="ℹ️ Guruh qoidalari", callback_data="user:rules")],
        [InlineKeyboardButton(text="📞 Administrator", callback_data="user:contact")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Admin panel", callback_data="admin_menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_to_user_menu() -> InlineKeyboardMarkup:
    """Simple back button to main user menu."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="user:menu")]
    ])


def get_contact_menu(admin_username: str = "abdulaziz5335") -> InlineKeyboardMarkup:
    """Inline keyboard for contact section with direct chat link."""
    username = admin_username.lstrip("@")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Administratorga yozish", url=f"https://t.me/{username}")],
        [InlineKeyboardButton(text="🔙 Bosh menyu", callback_data="user:menu")]
    ])
