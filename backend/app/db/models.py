from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RunRecord(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    cv_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class JobRecord(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    job_id: Mapped[str] = mapped_column(String(128), index=True)
    job_url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(512))
    company: Mapped[str] = mapped_column(String(512))
    match_score: Mapped[int] = mapped_column(Integer, default=0)
    payload_json: Mapped[str] = mapped_column(Text)
