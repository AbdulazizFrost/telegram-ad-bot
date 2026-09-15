from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    BOT_TOKEN: str = Field(default="", description="Telegram Bot API Token")
    ADMIN_ID: int = Field(default=0, description="Main Administrator Telegram ID")
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./data/bot.db",
        description="Async SQLAlchemy database URL"
    )
    
    # Timezone & Localization
    BOT_TIMEZONE: str = Field(default="Asia/Tashkent", description="Timezone name")
    
    # Moderation
    NOTICE_DELETE_SECONDS: int = Field(
        default=10,
        description="Seconds before temporary notification message in group is deleted"
    )
    MODERATION_LOG_RETENTION_DAYS: int = Field(
        default=90,
        description="Days to retain moderation logs before automatic cleanup"
    )
    AD_DETECTION_THRESHOLD: int = Field(
        default=50,
        description="Scoring threshold to classify message as advertisement"
    )
    OCR_ENABLED: bool = Field(
        default=True,
        description="Enable local Tesseract OCR for photos and video keyframes"
    )
    MAX_VIDEO_FRAMES_SAMPLE: int = Field(
        default=3,
        description="Max keyframes to sample from video for local OCR"
    )
    MAX_MEDIA_DOWNLOAD_MB: int = Field(
        default=25,
        description="Max media file size in megabytes to download and inspect"
    )
    ALBUM_DEBOUNCE_SECONDS: float = Field(
        default=0.4,
        description="Debounce buffer window in seconds for Telegram media groups"
    )
    
    # Default Payment Details (fallback if not in DB settings)
    PAYMENT_CARD: str = Field(default="8600 0000 0000 0000", description="Bank card number")
    PAYMENT_CARD_HOLDER: str = Field(default="ADMINISTRATOR", description="Cardholder name")
    
    # Webhook (for Render Web Service)
    WEBHOOK_URL: str = Field(default="", description="Public base URL for webhook, e.g. https://my-bot.onrender.com")
    WEBHOOK_PATH: str = Field(default="/webhook", description="Path for incoming Telegram updates")
    PORT: int = Field(default=10000, description="HTTP Port to listen on")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # AI Moderation (Tier 2 Semantic Classification)
    AI_ENABLED: bool = Field(default=False, description="Global AI moderation master toggle")
    AI_PROVIDER: str = Field(default="gemini", description="AI Provider: gemini, groq, openai_compatible, or mock")
    AI_API_KEY: str = Field(default="", description="API key for AI provider")
    AI_MODEL: str = Field(default="gemini-2.5-flash", description="AI Model identifier (configurable)")
    AI_AD_THRESHOLD: float = Field(default=0.90, description="Confidence threshold above which AI AD is deleted")
    AI_TIMEOUT: float = Field(default=8.0, description="Timeout in seconds for AI API calls")
    AI_CACHE_TTL: int = Field(default=3600, description="In-memory cache TTL in seconds for AI responses")
    AI_MAX_CONCURRENT: int = Field(default=3, description="Maximum concurrent AI API calls")
    AI_RATE_LIMIT_RPM: int = Field(default=12, description="Requests per minute rate limit for AI API calls")


import os

settings = Settings()

# Auto-detect Render external URL if WEBHOOK_URL is not explicitly configured
if not settings.WEBHOOK_URL and os.environ.get("RENDER_EXTERNAL_URL"):
    settings.WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

# Normalize PostgreSQL URL for asyncpg if standard postgres/postgresql scheme is given
if settings.DATABASE_URL.startswith("postgres://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif settings.DATABASE_URL.startswith("postgresql://") and not settings.DATABASE_URL.startswith("postgresql+asyncpg://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Ensure local data directory exists if SQLite is used
if settings.DATABASE_URL.startswith("sqlite+aiosqlite:///"):
    db_path_str = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    if db_path_str.startswith("./"):
        db_path_str = db_path_str[2:]
    db_file = Path(db_path_str)
    db_file.parent.mkdir(parents=True, exist_ok=True)

# Ensure logs directory exists
Path("logs").mkdir(parents=True, exist_ok=True)
