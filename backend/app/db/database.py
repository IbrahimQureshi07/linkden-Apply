from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _sqlite_url_to_path(url: str) -> Path | None:
    if url.startswith("sqlite:///"):
        return Path(url.replace("sqlite:///", ""))
    return None


def get_engine():
    settings = get_settings()
    db_path = _sqlite_url_to_path(settings.database_url)
    if db_path and not db_path.is_absolute():
        db_path = settings.backend_root / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_path.as_posix()}"
    else:
        url = settings.database_url
    return create_engine(url, connect_args={"check_same_thread": False})


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    from app.db import models as _models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
