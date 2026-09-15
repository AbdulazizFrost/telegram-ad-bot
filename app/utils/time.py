from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
from app.config import settings

TASHKENT_TZ = ZoneInfo(settings.BOT_TIMEZONE)


def now_utc() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_tashkent(dt: datetime) -> datetime:
    """Convert any UTC datetime (naive or aware) to Asia/Tashkent datetime."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TASHKENT_TZ)


def format_tashkent(dt: Optional[datetime], fmt: str = "%d.%m.%Y %H:%M") -> str:
    """Format UTC datetime into Tashkent local time string."""
    if dt is None:
        return "Noma'lum"
    return to_tashkent(dt).strftime(fmt)


def is_past_24_hours(last_ad_at: Optional[datetime], current_time: Optional[datetime] = None) -> bool:
    """
    Check if at least rolling 24 hours have passed since last_ad_at.
    Returns True if last_ad_at is None or now >= last_ad_at + 24 hours.
    """
    if last_ad_at is None:
        return True
    
    if current_time is None:
        current_time = now_utc()
        
    if last_ad_at.tzinfo is None:
        last_ad_at = last_ad_at.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
        
    return current_time >= (last_ad_at + timedelta(hours=24))


def next_available_free_ad_time(last_ad_at: datetime) -> datetime:
    """Return the exact UTC datetime when the next free ad will be available."""
    if last_ad_at.tzinfo is None:
        last_ad_at = last_ad_at.replace(tzinfo=timezone.utc)
    return last_ad_at + timedelta(hours=24)


def remaining_time_str(last_ad_at: datetime) -> str:
    """
    Return human-readable remaining time string (e.g., '5 soat 30 daqiqa')
    until the next free ad is available.
    """
    next_time = next_available_free_ad_time(last_ad_at)
    now = now_utc()
    diff = next_time - now
    if diff.total_seconds() <= 0:
        return "0 daqiqa"
    
    total_minutes = int(diff.total_seconds() // 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    if hours > 0:
        return f"{hours} soat {minutes} daqiqa"
    return f"{minutes} daqiqa"
