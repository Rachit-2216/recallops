"""Store evidence trace IDs selected for a resolution.

Revision ID: 0002_resolution_trace_ids
Revises: 0001_initial
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_resolution_trace_ids"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "resolutions",
        sa.Column(
            "trace_ids_json",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("resolutions", "trace_ids_json")
