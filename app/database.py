import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


# Create async SQLAlchemy engine
# Supports both SQLite (sqlite+aiosqlite) and PostgreSQL (postgresql+asyncpg)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async session generator context."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create tables, run schema migrations, and populate default settings."""
    # Import all models to ensure they are registered with Base.metadata
    import app.models  # noqa: F401
    from app.models.setting import Setting

    logger.info("Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Auto-migration for existing SQLite moderation_logs table if columns are missing
        if "sqlite" in settings.DATABASE_URL:
            def migrate_sqlite(sync_conn):
                cursor = sync_conn.connection.cursor()
                cursor.execute("PRAGMA table_info(moderation_logs)")
                existing_cols = {row[1] for row in cursor.fetchall()}
                if existing_cols:
                    col_defs = {
                        "telegram_message_id": "BIGINT DEFAULT 0",
                        "first_name": "VARCHAR(255)",
                        "last_name": "VARCHAR(255)",
                        "message_text": "TEXT",
                        "deleted_at": "TIMESTAMP",
                        "violation_type": "VARCHAR(64) DEFAULT 'OTHER_AD_VIOLATION'",
                        "user_role": "VARCHAR(32) DEFAULT 'user'",
                        "subscription_status": "VARCHAR(32) DEFAULT 'none'",
                        "was_taxi": "BOOLEAN DEFAULT 0",
                        "detector_score": "FLOAT DEFAULT 0.0",
                    }
                    for col, defn in col_defs.items():
                        if col not in existing_cols:
                            try:
                                cursor.execute(f"ALTER TABLE moderation_logs ADD COLUMN {col} {defn}")
                            except Exception as e:
                                logger.debug(f"Could not add column {col}: {e}")
            await conn.run_sync(migrate_sqlite)

    # Populate default settings if missing
    async with async_session_maker() as session:
        default_settings = {
            "price_1_day": "15000",
            "price_7_days": "35000",
            "price_30_days": "100000",
            "payment_card": settings.PAYMENT_CARD,
            "payment_card_holder": settings.PAYMENT_CARD_HOLDER,
            "notice_delete_seconds": str(settings.NOTICE_DELETE_SECONDS),
            "moderation_log_retention_days": str(settings.MODERATION_LOG_RETENTION_DAYS),
            "ad_detection_threshold": str(settings.AD_DETECTION_THRESHOLD),
        }
        for key, val in default_settings.items():
            existing = await session.get(Setting, key)
            if not existing:
                session.add(Setting(key=key, value=val))
        await session.commit()
    logger.info("Database initialized successfully.")


async def close_db():
    """Dispose of engine connection pool."""
    await engine.dispose()
    logger.info("Database connection closed.")
