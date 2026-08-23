from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator
from uuid import uuid4

from geoalchemy2 import Geography
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .config import settings


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EventRow(Base):
    __tablename__ = "normalized_events"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    source_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    source_system: Mapped[str] = mapped_column(String(128), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    raw_sha256: Mapped[str | None] = mapped_column(String(64))
    correlation_processed_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    correlation_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    geom: Mapped[object | None] = mapped_column(Geography("POINT", srid=4326, spatial_index=True))
    roadway: Mapped[str | None] = mapped_column(String(255), index=True)
    direction: Mapped[str | None] = mapped_column(String(16), index=True)
    location_text: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    lanes_affected: Mapped[str | None] = mapped_column(String(255))
    commercial_vehicle_hint: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    injury_hint: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fatality_hint: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    closure_hint: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stalled_vehicle_hint: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    debris_hint: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    wheel_off_hint: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attributes_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    first_ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    hypothesis_links: Mapped[list["HypothesisEventRow"]] = relationship(back_populates="event")

    __table_args__ = (
        UniqueConstraint("source_system", "source_record_id", name="uq_event_source_record"),
        Index("ix_event_time_roadway", "observed_at", "roadway"),
    )


class HypothesisRow(Base):
    __tablename__ = "incident_hypotheses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    current_revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    centroid: Mapped[object | None] = mapped_column(Geography("POINT", srid=4326, spatial_index=True))
    roadway: Mapped[str | None] = mapped_column(String(255), index=True)
    direction: Mapped[str | None] = mapped_column(String(16), index=True)

    revisions: Mapped[list["HypothesisRevisionRow"]] = relationship(back_populates="hypothesis")
    event_links: Mapped[list["HypothesisEventRow"]] = relationship(back_populates="hypothesis")


class HypothesisRevisionRow(Base):
    __tablename__ = "hypothesis_revisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid4()))
    hypothesis_id: Mapped[str] = mapped_column(ForeignKey("incident_hypotheses.id", ondelete="CASCADE"), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    machine_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    classification: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    rationale_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    contradictions_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    member_event_ids_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    hypothesis: Mapped[HypothesisRow] = relationship(back_populates="revisions")

    __table_args__ = (UniqueConstraint("hypothesis_id", "revision", name="uq_hypothesis_revision"),)


class HypothesisEventRow(Base):
    __tablename__ = "hypothesis_events"

    hypothesis_id: Mapped[str] = mapped_column(ForeignKey("incident_hypotheses.id", ondelete="CASCADE"), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("normalized_events.id", ondelete="CASCADE"), primary_key=True)
    first_linked_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    last_evaluated_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    link_score: Mapped[float | None] = mapped_column(Float)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    hypothesis: Mapped[HypothesisRow] = relationship(back_populates="event_links")
    event: Mapped[EventRow] = relationship(back_populates="hypothesis_links")


class DecisionLedgerRow(Base):
    __tablename__ = "decision_ledger"

    sequence_no: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, default=lambda: str(uuid4()))
    entry_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    produced_by: Mapped[str] = mapped_column(String(255), nullable=False)
    source_system: Mapped[str | None] = mapped_column(String(255))
    model_version: Mapped[str | None] = mapped_column(String(128))
    input_entry_ids_json: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    supersedes_entry_id: Mapped[str | None] = mapped_column(String(64))
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (Index("ix_ledger_subject_sequence", "subject_id", "sequence_no"),)


engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def session_scope() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
