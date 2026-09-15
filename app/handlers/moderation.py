import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.enums import ChatType
from app.database import async_session_maker
from app.services.moderation_service import process_group_message

logger = logging.getLogger(__name__)

router = Router(name="moderation")


@router.message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def handle_group_message(message: Message, bot: Bot):
    """
    Catch all group messages and run moderation pipeline.
    """
    try:
        async with async_session_maker() as session:
            await process_group_message(bot=bot, message=message, session=session)
    except Exception as e:
        logger.error(f"Unexpected error in group moderation handler: {e}", exc_info=True)


@router.edited_message(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def handle_group_edited_message(message: Message, bot: Bot):
    """
    Catch edited messages in group and run moderation pipeline.
    Prevents evasion by posting clean text and then editing it into an ad.
    """
    try:
        async with async_session_maker() as session:
            await process_group_message(bot=bot, message=message, session=session)
    except Exception as e:
        logger.error(f"Unexpected error in edited message handler: {e}", exc_info=True)

