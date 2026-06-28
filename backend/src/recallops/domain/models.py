from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from recallops.db import Base
from recallops.domain.enums import IncidentStatus


class InvalidTransition(ValueError):
    """Raised when a domain object cannot enter the requested state."""


@dataclass
class IncidentRecord:
    id: str
    status: IncidentStatus
    resolved_at: datetime | None = None

    @classmethod
    def active_demo(cls) -> IncidentRecord:
        return cls(id="INC-2048", status=IncidentStatus.ACTIVE)

    def resolve(
        self,
        *,
        root_cause: str,
        mitigation: str,
        verification: str,
        reference_count: int,
    ) -> None:
        if not root_cause.strip():
            raise InvalidTransition("root cause is required")
        if not mitigation.strip():
            raise InvalidTransition("mitigation is required")
        if not verification.strip():
            raise InvalidTransition("verification is required")
        if reference_count < 1:
            raise InvalidTransition("at least one evidence reference is required")
        if self.status not in {IncidentStatus.ACTIVE, IncidentStatus.MITIGATED}:
            raise InvalidTransition(f"incident cannot resolve from {self.status}")
        self.status = IncidentStatus.RESOLVED
        self.resolved_at = datetime.now(UTC)


def _uuid() -> str:
    return str(uuid4())


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(8))
    service: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="active")
    session_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
    )

    observations: Mapped[list[Observation]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )
    memory_candidates: Mapped[list[MemoryCandidate]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )
    recall_traces: Mapped[list[RecallTrace]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )
    feedback_entries: Mapped[list[Feedback]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )
    resolution: Mapped[Resolution | None] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        uselist=False,
    )


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    __table_args__ = (
        UniqueConstraint(
            "dataset",
            "content_hash",
            name="uq_evidence_dataset_content_hash",
        ),
    )

    data_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(32))
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    content_hash: Mapped[str] = mapped_column(String(80))
    source_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
    )
    forgotten_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    candidates: Mapped[list[MemoryCandidate]] = relationship(
        back_populates="evidence",
    )
    recall_references: Mapped[list[RecallReference]] = relationship(
        back_populates="evidence",
    )


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
    )
    source: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    memory_status: Mapped[str] = mapped_column(String(20), default="pending")
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
    )

    incident: Mapped[Incident] = relationship(back_populates="observations")


class MemoryCandidate(Base):
    __tablename__ = "memory_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        index=True,
    )
    evidence_data_id: Mapped[str | None] = mapped_column(
        ForeignKey("evidence_items.data_id", ondelete="SET NULL"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), default="proposed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
    )

    incident: Mapped[Incident] = relationship(back_populates="memory_candidates")
    evidence: Mapped[EvidenceItem | None] = relationship(back_populates="candidates")


class RecallTrace(Base):
    __tablename__ = "recall_traces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        index=True,
    )
    query: Mapped[str] = mapped_column(Text)
    query_type: Mapped[str] = mapped_column(String(50), default="auto")
    source: Mapped[str] = mapped_column(String(30))
    search_type: Mapped[str] = mapped_column(String(100))
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_state: Mapped[str] = mapped_column(
        String(20),
        default="unverified",
    )
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    raw_fixture_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
    )

    incident: Mapped[Incident] = relationship(back_populates="recall_traces")
    references: Mapped[list[RecallReference]] = relationship(
        back_populates="trace",
        cascade="all, delete-orphan",
    )
    feedback_entries: Mapped[list[Feedback]] = relationship(
        back_populates="trace",
        cascade="all, delete-orphan",
    )


class RecallReference(Base):
    __tablename__ = "recall_references"
    __table_args__ = (
        UniqueConstraint(
            "trace_id",
            "chunk_id",
            name="uq_recall_reference_trace_chunk",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    trace_id: Mapped[str] = mapped_column(
        ForeignKey("recall_traces.id", ondelete="CASCADE"),
        index=True,
    )
    data_id: Mapped[str] = mapped_column(
        ForeignKey("evidence_items.data_id"),
        index=True,
    )
    chunk_id: Mapped[str] = mapped_column(String(100))
    document_name: Mapped[str] = mapped_column(String(255))
    snippet: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
    )

    trace: Mapped[RecallTrace] = relationship(back_populates="references")
    evidence: Mapped[EvidenceItem] = relationship(
        back_populates="recall_references",
    )


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        index=True,
    )
    trace_id: Mapped[str] = mapped_column(
        ForeignKey("recall_traces.id", ondelete="CASCADE"),
        index=True,
    )
    score: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
    )

    incident: Mapped[Incident] = relationship(back_populates="feedback_entries")
    trace: Mapped[RecallTrace] = relationship(back_populates="feedback_entries")


class Resolution(Base):
    __tablename__ = "resolutions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    root_cause: Mapped[str] = mapped_column(Text)
    mitigation: Mapped[str] = mapped_column(Text)
    verification: Mapped[str] = mapped_column(Text)
    confirmed_by_human: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    promotion_state: Mapped[str] = mapped_column(
        String(30),
        default="not_requested",
    )
    improve_operation_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
        onupdate=_utc_now,
    )

    incident: Mapped[Incident] = relationship(back_populates="resolution")


class MemoryOperation(Base):
    __tablename__ = "memory_operations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    incident_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    operation: Mapped[str] = mapped_column(String(30), index=True)
    dataset: Mapped[str] = mapped_column(String(100))
    target_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estimated_tokens: Mapped[int] = mapped_column(Integer, default=0)


class CreditLedger(Base):
    __tablename__ = "credit_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    operation: Mapped[str] = mapped_column(String(30), index=True)
    estimated_tokens: Mapped[int] = mapped_column(Integer)
    essential: Mapped[bool] = mapped_column(Boolean, default=False)
    remaining_after: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utc_now,
    )
