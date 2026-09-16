import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.database import Base
from app.models.user import User
from app.models.subscription import Subscription
from app.models.taxi_limit import TaxiAdLimit
from app.models.moderation_log import ModerationLog
from app.services.subscription_service import (
    get_or_create_user,
    has_active_subscription,
    grant_subscription,
)
from app.services.moderation_service import process_group_message, cleanup_old_moderation_logs
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from app.config import settings


from contextlib import asynccontextmanager

@asynccontextmanager
async def get_test_session():
    """Create an isolated in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
    
    await engine.dispose()


def create_mock_message(
    chat_id: int = -100123456789,
    user_id: int = 111111,
    username: str = "testuser",
    first_name: str = "Test",
    last_name: str = None,
    text: str = "Oddiy xabar",
    chat_type: ChatType = ChatType.SUPERGROUP
):
    """Helper to generate mock aiogram Message."""
    msg = MagicMock()
    msg.message_id = 123
    msg.chat.id = chat_id
    msg.chat.type = chat_type
    
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.first_name = first_name
    user.last_name = last_name
    user.is_bot = False
    
    msg.from_user = user
    msg.text = text
    msg.caption = None
    msg.entities = []
    msg.caption_entities = []
    msg.answer = AsyncMock()
    return msg


def create_mock_bot(is_admin: bool = False):
    """Helper to generate mock aiogram Bot."""
    bot = AsyncMock()
    bot_user = MagicMock()
    bot_user.username = "ad_moderator_bot"
    bot_user.id = 999999
    bot.get_me.return_value = bot_user
    
    member = MagicMock()
    member.status = ChatMemberStatus.ADMINISTRATOR if is_admin else ChatMemberStatus.MEMBER
    bot.get_chat_member.return_value = member
    bot.delete_message = AsyncMock()
    return bot


# ==========================================
# TEST CASES 4, 5, 6: TAXI 24-HOUR LIMIT
# ==========================================

@pytest.mark.asyncio
async def test_taxi_24_hour_rolling_limit():
    """
    Test 4: Taxi first ad -> allowed
    Test 5: Taxi second ad before 24h -> deleted
    Test 6: Taxi ad after 24h -> allowed
    """
    async with get_test_session() as test_session:
        # 1. Create a taxi user
        taxi_user = User(telegram_id=222222, username="taxi_driver", role="taxi")
        test_session.add(taxi_user)
        await test_session.commit()

        bot = create_mock_bot(is_admin=False)
        taxi_ad_text = "Toshkent Samarqand mashina bor 2 ta joy bor yuramiz"

        # Step 1: First taxi ad -> Should be allowed!
        msg1 = create_mock_message(user_id=222222, username="taxi_driver", text=taxi_ad_text)
        deleted1 = await process_group_message(bot, msg1, test_session)
        assert deleted1 is False, "Taxi first ad was wrongly deleted"
        bot.delete_message.assert_not_called()

        # Verify last_free_ad_at timestamp was saved
        result = await test_session.execute(select(TaxiAdLimit).where(TaxiAdLimit.user_id == taxi_user.id))
        limit_entry = result.scalar_one_or_none()
        assert limit_entry is not None
        assert limit_entry.last_free_ad_at is not None

        # Step 2: Second taxi ad within 2 hours -> Should be DELETED!
        msg2 = create_mock_message(user_id=222222, username="taxi_driver", text=taxi_ad_text)
        deleted2 = await process_group_message(bot, msg2, test_session)
        assert deleted2 is True, "Taxi second ad within 24h was NOT deleted"
        bot.delete_message.assert_called_once_with(chat_id=msg2.chat.id, message_id=msg2.message_id)

        # Step 3: Simulate 25 hours passing
        limit_entry.last_free_ad_at = datetime.now(timezone.utc) - timedelta(hours=25)
        await test_session.commit()

        bot.delete_message.reset_mock()
        msg3 = create_mock_message(user_id=222222, username="taxi_driver", text=taxi_ad_text)
        deleted3 = await process_group_message(bot, msg3, test_session)
        assert deleted3 is False, "Taxi ad after 24h was wrongly deleted"
        bot.delete_message.assert_not_called()


# ==========================================
# TEST CASES 7, 8: TAXI SUBSCRIPTION
# ==========================================

@pytest.mark.asyncio
async def test_taxi_with_active_and_expired_subscription():
    """
    Test 7: Taxi with active subscription -> ad allowed without 24h limit
    Test 8: Subscription expired -> reverts to 24h limit rule
    """
    async with get_test_session() as test_session:
        # Create taxi who already used their free ad 1 hour ago
        taxi = User(telegram_id=333333, username="sub_taxi", role="taxi")
        test_session.add(taxi)
        await test_session.commit()

        limit = TaxiAdLimit(user_id=taxi.id, last_free_ad_at=datetime.now(timezone.utc) - timedelta(hours=1))
        test_session.add(limit)
        await test_session.commit()

        # Grant active 7-day subscription
        await grant_subscription(test_session, taxi.id, "7_days", price=35000)

        bot = create_mock_bot(is_admin=False)
        taxi_ad = "Toshkent Samarqand mashina bor 2 ta joy bor yuramiz"

        # With active subscription: ad must be allowed even though free ad was 1h ago!
        msg1 = create_mock_message(user_id=333333, username="sub_taxi", text=taxi_ad)
        deleted1 = await process_group_message(bot, msg1, test_session)
        assert deleted1 is False, "Taxi with active subscription was blocked"

        # Now expire the subscription
        res = await test_session.execute(select(Subscription).where(Subscription.user_id == taxi.id))
        sub = res.scalar_one()
        sub.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await test_session.commit()

        # Re-send ad: since sub expired and last free ad was only 1h ago -> MUST BE DELETED
        msg2 = create_mock_message(user_id=333333, username="sub_taxi", text=taxi_ad)
        deleted2 = await process_group_message(bot, msg2, test_session)
        assert deleted2 is True, "Taxi with expired subscription was not subjected to 24h limit"


# ==========================================
# TEST CASES 9, 10: BUSINESS / REGULAR USER
# ==========================================

@pytest.mark.asyncio
async def test_business_ad_rules():
    """
    Test 9: Business without subscription -> ad deleted (0 free ads)
    Test 10: Business with subscription -> ad allowed
    """
    async with get_test_session() as test_session:
        bot = create_mock_bot(is_admin=False)
        commercial_ad = "Sotiladi! Yangi iPhone 15 Pro Max, karobka dokument, narxi arzon."

        # Step 1: User without subscription -> DELETED
        msg1 = create_mock_message(user_id=444444, username="shop_owner", text=commercial_ad)
        deleted1 = await process_group_message(bot, msg1, test_session)
        assert deleted1 is True, "Commercial ad without subscription was NOT deleted"

        # Step 2: Grant subscription to user
        user = await get_or_create_user(test_session, telegram_id=444444, username="shop_owner")
        await grant_subscription(test_session, user.id, "30_days", price=100000)

        # Step 3: Same ad with active subscription -> ALLOWED
        msg2 = create_mock_message(user_id=444444, username="shop_owner", text=commercial_ad)
        deleted2 = await process_group_message(bot, msg2, test_session)
        assert deleted2 is False, "Commercial ad with active subscription was wrongly deleted"


# ==========================================
# TEST CASE 11: GROUP ADMINISTRATOR PROTECTION
# ==========================================

@pytest.mark.asyncio
async def test_group_administrator_not_moderated():
    """
    Test 11: Group administrator / owner message is never moderated.
    """
    async with get_test_session() as test_session:
        # Bot where user is administrator
        bot = create_mock_bot(is_admin=True)
        msg = create_mock_message(
            user_id=555555,
            username="group_admin",
            text="Sotiladi! Yangi iPhone 15 Pro Max narxi arzon."
        )
        deleted = await process_group_message(bot, msg, test_session)
        assert deleted is False, "Group administrator message was wrongly moderated"
        bot.delete_message.assert_not_called()


# ==========================================
# TEST CASES 12, 13: IDENTIFICATION & BINDING
# ==========================================

@pytest.mark.asyncio
async def test_taxi_username_pre_registration_and_binding():
    """
    Test 12: Admin adds taxi by username (@taxi_ali) before user ever sent a message.
             When user sends first message, bot binds their telegram_id to this record.
    Test 13: When user changes username, telegram_id continues identifying them.
    """
    async with get_test_session() as test_session:
        # Admin pre-adds taxi by username
        pre_user = User(username="taxi_ali", role="taxi", telegram_id=None)
        test_session.add(pre_user)
        await test_session.commit()
        pre_id = pre_user.id

        # User sends first message with Telegram ID 777777 and username 'Taxi_Ali'
        user = await get_or_create_user(
            session=test_session,
            telegram_id=777777,
            username="Taxi_Ali",
            first_name="Ali"
        )

        # Must be the exact same DB user record with telegram_id bound!
        assert user.id == pre_id, "Lazy binding failed: created duplicate user instead of binding"
        assert user.telegram_id == 777777
        assert user.role == "taxi"

        # User changes username to 'ali_transport'
        user_updated = await get_or_create_user(
            session=test_session,
            telegram_id=777777,
            username="ali_transport",
            first_name="Ali"
        )
        assert user_updated.id == pre_id
        assert user_updated.username == "ali_transport"
        assert user_updated.role == "taxi", "Role was lost after username change"


# ==========================================
# TEST CASE 14: DATA PERSISTENCE ACROSS RESTART
# ==========================================

@pytest.mark.asyncio
async def test_data_persistence_across_restart(tmp_path):
    """
    Test 14: Verifies data (users, subscriptions, taxi limits) persists
             in SQLite file across multiple database engine/session instantiations.
    """
    db_file = tmp_path / "persistent_test.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    # First session: insert data
    engine1 = create_async_engine(db_url)
    async with engine1.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sm1 = async_sessionmaker(engine1, expire_on_commit=False, class_=AsyncSession)
    async with sm1() as s1:
        u = User(telegram_id=888888, username="persist_user", role="taxi")
        s1.add(u)
        await s1.commit()
        await grant_subscription(s1, u.id, "30_days", price=100000)
    await engine1.dispose()

    # Second session: simulate bot restart with a new engine
    engine2 = create_async_engine(db_url)
    sm2 = async_sessionmaker(engine2, expire_on_commit=False, class_=AsyncSession)
    async with sm2() as s2:
        res = await s2.execute(select(User).where(User.telegram_id == 888888))
        user_loaded = res.scalar_one_or_none()
        assert user_loaded is not None
        assert user_loaded.username == "persist_user"
        assert user_loaded.role == "taxi"

        # Check subscription persisted
        has_sub, sub = await has_active_subscription(s2, user_loaded.id)
        assert has_sub is True
        assert sub.plan == "30_days"

    await engine2.dispose()


# ==========================================
# TEST CASES: DETAILED MODERATION LOGGING
# ==========================================

@pytest.mark.asyncio
async def test_detailed_moderation_log_recorded(monkeypatch):
    """
    Verifies that upon successful deletion of an ad, a detailed ModerationLog
    record is created with all required fields when SAVE_MODERATION_LOGS is True.
    """
    monkeypatch.setattr(settings, "SAVE_MODERATION_LOGS", True)
    async with get_test_session() as test_session:
        bot = create_mock_bot(is_admin=False)
        ad_text = "Sotiladi! Yangi iPhone 15 Pro Max narxi arzon."
        msg = create_mock_message(
            chat_id=-100999888777,
            user_id=654321,
            username="seller_uz",
            first_name="Seller",
            last_name="Pro",
            text=ad_text,
        )

        deleted = await process_group_message(bot, msg, test_session)
        assert deleted is True
        bot.delete_message.assert_called_once_with(chat_id=-100999888777, message_id=123)

        # Query ModerationLog
        result = await test_session.execute(
            select(ModerationLog).where(ModerationLog.user_id == 654321)
        )
        logs = result.scalars().all()
        assert len(logs) == 1
        log = logs[0]

        assert log.telegram_message_id == 123
        assert log.chat_id == -100999888777
        assert log.user_id == 654321
        assert log.username == "seller_uz"
        assert log.first_name == "Seller"
        assert log.last_name == "Pro"
        assert log.message_text == ad_text
        assert log.violation_type == "BUSINESS_AD_WITHOUT_SUBSCRIPTION"
        assert log.user_role == "user"
        assert log.subscription_status == "none"
        assert log.was_taxi is False
        assert log.detector_score >= 50.0
        assert log.deleted_at is not None
        assert "sotiladi" in log.reason.lower()


@pytest.mark.asyncio
async def test_moderation_log_not_recorded_when_disabled():
    """
    Verifies that when SAVE_MODERATION_LOGS is False (default),
    no record is inserted into moderation_logs table upon deletion.
    """
    async with get_test_session() as test_session:
        bot = create_mock_bot(is_admin=False)
        ad_text = "Sotiladi! Yangi iPhone 15 Pro Max narxi arzon."
        msg = create_mock_message(
            chat_id=-100999888777,
            user_id=654322,
            username="seller_uz2",
            first_name="Seller2",
            last_name="Pro2",
            text=ad_text,
        )

        deleted = await process_group_message(bot, msg, test_session)
        assert deleted is True
        bot.delete_message.assert_called_once_with(chat_id=-100999888777, message_id=123)

        result = await test_session.execute(
            select(ModerationLog).where(ModerationLog.user_id == 654322)
        )
        logs = result.scalars().all()
        assert len(logs) == 0


@pytest.mark.asyncio
async def test_failed_telegram_deletion_does_not_log():
    """
    Verifies that if Telegram deletion fails (e.g. lack of permissions or message already deleted),
    NO record is inserted into moderation_logs table.
    """
    async with get_test_session() as test_session:
        bot = create_mock_bot(is_admin=False)
        bot.delete_message.side_effect = TelegramBadRequest(
            method=MagicMock(), message="Bad Request: message to delete not found"
        )

        ad_text = "Sotiladi! Yangi iPhone 15 Pro Max narxi arzon."
        msg = create_mock_message(
            chat_id=-100999888777,
            user_id=777888,
            username="failed_seller",
            text=ad_text,
        )

        deleted = await process_group_message(bot, msg, test_session)
        assert deleted is False

        # Verify no log entry was written
        result = await test_session.execute(
            select(ModerationLog).where(ModerationLog.user_id == 777888)
        )
        logs = result.scalars().all()
        assert len(logs) == 0


@pytest.mark.asyncio
async def test_cleanup_old_moderation_logs():
    """
    Verifies that cleanup_old_moderation_logs deletes records older than retention threshold,
    while keeping recent records intact.
    """
    async with get_test_session() as test_session:
        now = datetime.now(timezone.utc)
        old_date = now - timedelta(days=95)
        recent_date = now - timedelta(days=10)

        old_log = ModerationLog(
            telegram_message_id=1,
            chat_id=-1001,
            user_id=111,
            username="old_user",
            message_text="Eski reklama",
            deleted_at=old_date,
            reason="Old ad",
            violation_type="TEST",
            user_role="user",
            subscription_status="none",
            was_taxi=False,
            detector_score=60.0
        )
        recent_log = ModerationLog(
            telegram_message_id=2,
            chat_id=-1001,
            user_id=222,
            username="recent_user",
            message_text="Yangi reklama",
            deleted_at=recent_date,
            reason="Recent ad",
            violation_type="TEST",
            user_role="user",
            subscription_status="none",
            was_taxi=False,
            detector_score=60.0
        )
        test_session.add_all([old_log, recent_log])
        await test_session.commit()

        # Run cleanup with 90-day retention
        deleted_count = await cleanup_old_moderation_logs(test_session, retention_days=90)
        assert deleted_count == 1

        # Check remaining records
        result = await test_session.execute(select(ModerationLog))
        remaining = result.scalars().all()
        assert len(remaining) == 1
        assert remaining[0].user_id == 222
        assert remaining[0].message_text == "Yangi reklama"
