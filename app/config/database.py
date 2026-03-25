"""
settings/database.py — Database connection setup.

Creates the SQLAlchemy engine, session factory, and declarative base.
All models inherit from Base. Sessions are injected via get_db() FastAPI dependency.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config.settings.base import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # recycle stale connections automatically
    pool_size=10,
    max_overflow=20,
    echo=(settings.app_env == "development"),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base — all ORM models inherit from this."""
    pass


def get_db():
    """
    FastAPI dependency: yields a DB session and always closes it after the request,
    even if an exception is raised — prevents connection leaks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
