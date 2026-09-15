import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.database import init_db, close_db
from app.handlers import register_all_handlers

logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    """Create and configure Telegram Bot instance."""
    if not settings.BOT_TOKEN:
        logger.warning("BOT_TOKEN is not configured! Please set it in .env file.")
    return Bot(
        token=settings.BOT_TOKEN or "123456789:dummy_token_for_init",
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )


def create_dispatcher() -> Dispatcher:
    """Create Dispatcher with memory FSM storage and registered handlers."""
    dp = Dispatcher(storage=MemoryStorage())
    register_all_handlers(dp)
    return dp


async def setup_bot_commands(bot: Bot):
    """Set up Telegram bot commands menu."""
    try:
        default_commands = [
            BotCommand(command="start", description="Botni ishga tushirish"),
            BotCommand(command="help", description="Yordam va qoidalar"),
        ]
        await bot.set_my_commands(default_commands, scope=BotCommandScopeDefault())

        if settings.ADMIN_ID:
            admin_commands = [
                BotCommand(command="admin", description="⚙️ Admin panel"),
                BotCommand(command="stats", description="📊 Guruh statistikasi"),
                BotCommand(command="tariffs", description="💳 Tariflar narxi"),
                BotCommand(command="start", description="🏠 Bosh menyu"),
                BotCommand(command="help", description="ℹ️ Yordam"),
            ]
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=settings.ADMIN_ID))
        logger.info("Bot commands menu configured successfully.")
    except Exception as e:
        logger.warning(f"Could not set bot commands: {e}")


async def on_startup(bot: Bot):
    """Actions performed on bot launch."""
    logger.info("Starting up application...")
    await init_db()
    try:
        bot_user = await bot.get_me()
        logger.info(f"Bot authorized as @{bot_user.username} (ID: {bot_user.id})")
        await setup_bot_commands(bot)
    except Exception as e:
        logger.warning(f"Could not connect to Telegram on startup: {e}")
    logger.info("Bot is ready to process updates.")


async def on_shutdown(bot: Bot):
    """Actions performed on bot graceful termination."""
    logger.info("Shutting down application...")
    await close_db()
    await bot.session.close()
    logger.info("Application shut down cleanly.")
