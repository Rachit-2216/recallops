"""Expand incident identifiers for attributed public case studies.

Revision ID: 0003_expand_incident_ids
Revises: 0002_resolution_trace_ids
Create Date: 2026-07-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_expand_incident_ids"
down_revision: str | None = "0002_resolution_trace_ids"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INCIDENT_REFERENCE_TABLES = (
    "observations",
    "memory_candidates",
    "recall_traces",
    "feedback",
    "resolutions",
    "memory_operations",
)


def _resize(length_from: int, length_to: int) -> None:
    with op.batch_alter_table("incidents") as batch:
        batch.alter_column(
            "id",
            existing_type=sa.String(length=length_from),
            type_=sa.String(length=length_to),
            existing_nullable=False,
        )

    for table_name in INCIDENT_REFERENCE_TABLES:
        with op.batch_alter_table(table_name) as batch:
            batch.alter_column(
                "incident_id",
                existing_type=sa.String(length=length_from),
                type_=sa.String(length=length_to),
                existing_nullable=table_name == "memory_operations",
            )


def upgrade() -> None:
    _resize(16, 32)


def downgrade() -> None:
    _resize(32, 16)
