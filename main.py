import os
import sys
import logging
import asyncio
from aiohttp import web

from app.config import settings
from app.bot import create_bot, create_dispatcher, on_startup, on_shutdown


def setup_logging():
    """Setup dual logging to console and logs/bot.log."""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/bot.log", encoding="utf-8")
        ]
    )


async def run_polling():
    """Run bot in Long Polling mode (ideal for local testing and standard VPS)."""
    bot = create_bot()
    dp = create_dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logging.info("Starting bot in Polling mode...")
    # Delete webhook if previously set to ensure polling receives updates
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def health_check_handler(request: web.Request) -> web.Response:
    """Health check endpoint for Render ping."""
    return web.json_response({"status": "ok", "service": "telegram-ad-moderation-bot"})


async def root_handler(request: web.Request) -> web.Response:
    """Root landing endpoint."""
    return web.Response(text="Telegram Anti-Ad Moderation Bot is operational.")


def run_webhook():
    """Run bot in Webhook mode (ideal for Render Free Web Service)."""
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    bot = create_bot()
    dp = create_dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    # Health check routes
    app.router.add_get("/", root_handler)
    app.router.add_get("/health", health_check_handler)

    # Register webhook handler
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )
    webhook_handler.register(app, path=settings.WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    async def on_app_startup(app: web.Application):
        webhook_full_url = f"{settings.WEBHOOK_URL.rstrip('/')}{settings.WEBHOOK_PATH}"
        logging.info(f"Configuring Telegram webhook to: {webhook_full_url}")
        await bot.set_webhook(
            url=webhook_full_url,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )

    app.on_startup.append(on_app_startup)

    port = int(os.environ.get("PORT", settings.PORT))
    logging.info(f"Starting webhook server on 0.0.0.0:{port}...")
    web.run_app(app, host="0.0.0.0", port=port)


def main():
    setup_logging()
    
    if not settings.BOT_TOKEN:
        logging.critical("BOT_TOKEN is not set! Please configure .env file.")
        print("\n[ERROR] BOT_TOKEN topilmadi! Iltimos, .env faylida BOT_TOKEN ni belgilang.\n")
        sys.exit(1)

    # If WEBHOOK_URL is configured, use webhook mode (e.g. on Render)
    if settings.WEBHOOK_URL and settings.WEBHOOK_URL.strip():
        run_webhook()
    else:
        # Otherwise run in polling mode
        asyncio.run(run_polling())


if __name__ == "__main__":
    main()
