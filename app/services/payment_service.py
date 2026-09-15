from typing import Optional, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.models.setting import Setting
from app.services.subscription_service import grant_subscription
from app.utils.time import now_utc
from app.config import settings as app_settings


async def get_tariff_prices(session: AsyncSession) -> Dict[str, int]:
    """Retrieve current tariff prices from settings with default fallbacks."""
    default_prices = {
        "1_day": 15000,
        "7_days": 35000,
        "30_days": 100000,
    }
    prices = {}
    for plan, default_val in default_prices.items():
        setting = await session.get(Setting, f"price_{plan}")
        if setting and setting.value.isdigit():
            prices[plan] = int(setting.value)
        else:
            prices[plan] = default_val
    return prices


async def get_payment_details(session: AsyncSession) -> Dict[str, str]:
    """Retrieve bank card and cardholder information."""
    card_setting = await session.get(Setting, "payment_card")
    holder_setting = await session.get(Setting, "payment_card_holder")
    
    card = card_setting.value if card_setting else app_settings.PAYMENT_CARD
    holder = holder_setting.value if holder_setting else app_settings.PAYMENT_CARD_HOLDER
    return {"card": card, "holder": holder}


async def create_payment_request(
    session: AsyncSession,
    user_id: int,
    plan: str,
    amount: int,
    receipt_file_id: str,
    receipt_type: str = "photo"
) -> Payment:
    """Register a new pending payment request."""
    payment = Payment(
        user_id=user_id,
        plan=plan,
        amount=amount,
        status="pending",
        receipt_file_id=receipt_file_id,
        receipt_type=receipt_type,
        created_at=now_utc()
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def confirm_payment(session: AsyncSession, payment_id: int) -> Optional[Payment]:
    """
    Confirm payment and automatically activate/extend user subscription.
    """
    payment = await session.get(Payment, payment_id)
    if not payment or payment.status != "pending":
        return payment
        
    payment.status = "confirmed"
    payment.confirmed_at = now_utc()
    
    # Grant subscription
    await grant_subscription(session, payment.user_id, payment.plan, payment.amount)
    
    await session.commit()
    await session.refresh(payment)
    return payment


async def reject_payment(session: AsyncSession, payment_id: int) -> Optional[Payment]:
    """Reject payment request."""
    payment = await session.get(Payment, payment_id)
    if not payment or payment.status != "pending":
        return payment
        
    payment.status = "rejected"
    await session.commit()
    await session.refresh(payment)
    return payment
