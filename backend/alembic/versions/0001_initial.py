"""Create the initial RecallOps schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("severity", sa.String(length=8), nullable=False),
        sa.Column("service", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("session_id", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_incidents_session_id", "incidents", ["session_id"])

    op.create_table(
        "evidence_items",
        sa.Column("data_id", sa.String(length=36), nullable=False),
        sa.Column("dataset", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("content_hash", sa.String(length=80), nullable=False),
        sa.Column("source_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_stale", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("forgotten_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("data_id"),
        sa.UniqueConstraint(
            "dataset",
            "content_hash",
            name="uq_evidence_dataset_content_hash",
        ),
    )
    op.create_index("ix_evidence_items_dataset", "evidence_items", ["dataset"])

    op.create_table(
        "observations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("incident_id", sa.String(length=16), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("memory_status", sa.String(length=20), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_observations_incident_id", "observations", ["incident_id"])

    op.create_table(
        "memory_candidates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("incident_id", sa.String(length=16), nullable=False),
        sa.Column("evidence_data_id", sa.String(length=36), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_data_id"],
            ["evidence_items.data_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_memory_candidates_incident_id",
        "memory_candidates",
        ["incident_id"],
    )

    op.create_table(
        "recall_traces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("incident_id", sa.String(length=16), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("query_type", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("search_type", sa.String(length=100), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("verification_state", sa.String(length=20), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("raw_fixture_ref", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recall_traces_incident_id", "recall_traces", ["incident_id"])

    op.create_table(
        "recall_references",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=False),
        sa.Column("data_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=100), nullable=False),
        sa.Column("document_name", sa.String(length=255), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["data_id"],
            ["evidence_items.data_id"],
        ),
        sa.ForeignKeyConstraint(
            ["trace_id"],
            ["recall_traces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trace_id",
            "chunk_id",
            name="uq_recall_reference_trace_chunk",
        ),
    )
    op.create_index("ix_recall_references_data_id", "recall_references", ["data_id"])
    op.create_index("ix_recall_references_trace_id", "recall_references", ["trace_id"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("incident_id", sa.String(length=16), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["trace_id"],
            ["recall_traces.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_incident_id", "feedback", ["incident_id"])
    op.create_index("ix_feedback_trace_id", "feedback", ["trace_id"])

    op.create_table(
        "resolutions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("incident_id", sa.String(length=16), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=False),
        sa.Column("mitigation", sa.Text(), nullable=False),
        sa.Column("verification", sa.Text(), nullable=False),
        sa.Column("confirmed_by_human", sa.Boolean(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promotion_state", sa.String(length=30), nullable=False),
        sa.Column("improve_operation_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_id"),
    )
    op.create_index("ix_resolutions_incident_id", "resolutions", ["incident_id"])

    op.create_table(
        "memory_operations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("incident_id", sa.String(length=16), nullable=True),
        sa.Column("trace_id", sa.String(length=36), nullable=True),
        sa.Column("operation", sa.String(length=30), nullable=False),
        sa.Column("dataset", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_category", sa.String(length=100), nullable=True),
        sa.Column("estimated_tokens", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_memory_operations_operation",
        "memory_operations",
        ["operation"],
    )
    op.create_index(
        "ix_memory_operations_request_id",
        "memory_operations",
        ["request_id"],
    )

    op.create_table(
        "credit_ledger",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("operation", sa.String(length=30), nullable=False),
        sa.Column("estimated_tokens", sa.Integer(), nullable=False),
        sa.Column("essential", sa.Boolean(), nullable=False),
        sa.Column("remaining_after", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_ledger_operation", "credit_ledger", ["operation"])


def downgrade() -> None:
    op.drop_index("ix_credit_ledger_operation", table_name="credit_ledger")
    op.drop_table("credit_ledger")
    op.drop_index("ix_memory_operations_request_id", table_name="memory_operations")
    op.drop_index("ix_memory_operations_operation", table_name="memory_operations")
    op.drop_table("memory_operations")
    op.drop_index("ix_resolutions_incident_id", table_name="resolutions")
    op.drop_table("resolutions")
    op.drop_index("ix_feedback_trace_id", table_name="feedback")
    op.drop_index("ix_feedback_incident_id", table_name="feedback")
    op.drop_table("feedback")
    op.drop_index("ix_recall_references_trace_id", table_name="recall_references")
    op.drop_index("ix_recall_references_data_id", table_name="recall_references")
    op.drop_table("recall_references")
    op.drop_index("ix_recall_traces_incident_id", table_name="recall_traces")
    op.drop_table("recall_traces")
    op.drop_index(
        "ix_memory_candidates_incident_id",
        table_name="memory_candidates",
    )
    op.drop_table("memory_candidates")
    op.drop_index("ix_observations_incident_id", table_name="observations")
    op.drop_table("observations")
    op.drop_index("ix_evidence_items_dataset", table_name="evidence_items")
    op.drop_table("evidence_items")
    op.drop_index("ix_incidents_session_id", table_name="incidents")
    op.drop_table("incidents")
