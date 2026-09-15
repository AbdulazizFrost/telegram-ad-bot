from datetime import timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.subscription import Subscription
from app.models.taxi_limit import TaxiAdLimit
from app.utils.time import now_utc
from app.utils.text import normalize_username

PLAN_DURATIONS = {
    "1_day": timedelta(days=1),
    "7_days": timedelta(days=7),
    "30_days": timedelta(days=30),
}


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: Optional[int],
    username: Optional[str] = None,
    first_name: Optional[str] = None
) -> User:
    """
    Get or create user with lazy binding of telegram_id to pre-registered usernames.
    - If user exists by telegram_id -> return user (and update username if changed).
    - If user exists by username without telegram_id (e.g. pre-added taxi) -> bind telegram_id.
    - Otherwise -> create new user.
    """
    clean_username = normalize_username(username)
    user: Optional[User] = None

    # 1. Search by telegram_id first (primary identifier)
    if telegram_id:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update username and first_name if changed
            updated = False
            if clean_username and user.username != clean_username:
                user.username = clean_username
                updated = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if updated:
                await session.commit()
                await session.refresh(user)
            return user

    # 2. If not found by telegram_id, search by username (e.g. admin pre-added by /add_taxi @username)
    if clean_username:
        result = await session.execute(
            select(User).where(User.username == clean_username)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Bind telegram_id to existing pre-registered user
            if telegram_id and user.telegram_id is None:
                user.telegram_id = telegram_id
            if first_name and not user.first_name:
                user.first_name = first_name
            await session.commit()
            await session.refresh(user)
            return user

    # 3. Create new user
    new_user = User(
        telegram_id=telegram_id,
        username=clean_username,
        first_name=first_name,
        role="user"
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


async def get_user_by_identifier(session: AsyncSession, identifier: str) -> Optional[User]:
    """
    Find user by Telegram ID or @username.
    """
    identifier = identifier.strip()
    # Check if integer ID
    if identifier.lstrip('-').isdigit():
        tg_id = int(identifier)
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        return result.scalar_one_or_none()
    
    # Check by username
    clean_name = normalize_username(identifier)
    if clean_name:
        result = await session.execute(select(User).where(User.username == clean_name))
        return result.scalar_one_or_none()
        
    return None


async def has_active_subscription(
    session: AsyncSession,
    user_id: int
) -> Tuple[bool, Optional[Subscription]]:
    """
    Check if user has an active subscription.
    Automatically marks expired subscriptions as inactive.
    """
    current_time = now_utc()
    result = await session.execute(
        select(Subscription)
        .where(and_(Subscription.user_id == user_id, Subscription.active == True))
        .order_by(Subscription.expires_at.desc())
    )
    subscriptions = result.scalars().all()
    
    active_sub: Optional[Subscription] = None
    for sub in subscriptions:
        sub_expires = sub.expires_at
        if sub_expires.tzinfo is None:
            sub_expires = sub_expires.replace(tzinfo=timezone.utc)
            
        if sub_expires > current_time:
            active_sub = sub
            break
        else:
            # Expired subscription
            sub.active = False
            
    await session.commit()
    return (active_sub is not None), active_sub


async def grant_subscription(
    session: AsyncSession,
    user_id: int,
    plan: str,
    price: int = 0
) -> Subscription:
    """
    Grant or extend a subscription for a user.
    If an active subscription exists, extends from its expiration date.
    Note: Does NOT change the user's role!
    """
    duration = PLAN_DURATIONS.get(plan, timedelta(days=1))
    current_time = now_utc()
    
    # Check existing active subscription to extend
    is_active, existing_sub = await has_active_subscription(session, user_id)
    
    if is_active and existing_sub:
        base_time = existing_sub.expires_at
        if base_time.tzinfo is None:
            base_time = base_time.replace(tzinfo=timezone.utc)
        new_expires_at = base_time + duration
        existing_sub.expires_at = new_expires_at
        existing_sub.plan = plan
        await session.commit()
        await session.refresh(existing_sub)
        return existing_sub
    else:
        new_expires_at = current_time + duration
        new_sub = Subscription(
            user_id=user_id,
            plan=plan,
            price=price,
            started_at=current_time,
            expires_at=new_expires_at,
            active=True
        )
        session.add(new_sub)
        await session.commit()
        await session.refresh(new_sub)
        return new_sub


async def revoke_subscription(session: AsyncSession, user_id: int) -> bool:
    """Revoke all active subscriptions for user."""
    result = await session.execute(
        select(Subscription).where(
            and_(Subscription.user_id == user_id, Subscription.active == True)
        )
    )
    subs = result.scalars().all()
    if not subs:
        return False
    for sub in subs:
        sub.active = False
    await session.commit()
    return True
