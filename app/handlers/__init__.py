from aiogram import Dispatcher
from app.handlers.admin import router as admin_router
from app.handlers.payments import router as payments_router
from app.handlers.user import router as user_router
from app.handlers.group_settings import router as group_settings_router
from app.handlers.moderation import router as moderation_router


def register_all_handlers(dp: Dispatcher):
    """
    Register routers with precise priority order:
    1. Admin router (private chat commands & controls)
    2. Payments router (FSM and callbacks)
    3. User router (private chat menu)
    4. Group settings router (group-level /settings & /ai commands)
    5. Moderation router (group message interceptor)
    """
    dp.include_router(admin_router)
    dp.include_router(payments_router)
    dp.include_router(user_router)
    dp.include_router(group_settings_router)
    dp.include_router(moderation_router)
