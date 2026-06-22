"""Add bulk_jobs table for persistent bulk scrape state.

Revision ID: 005
Revises: 004
Create Date: 2026-06-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bulk_jobs",
        sa.Column("job_id", sa.String(length=20), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("target_count", sa.Integer(), nullable=False),
        sa.Column("total_queries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_queries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prospects_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prospects_saved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "prospects_skipped_duplicates",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("current_city", sa.String(length=150), nullable=True),
        sa.Column("current_category", sa.String(length=150), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "paused",
                "stopped",
                "completed",
                "failed",
                name="search_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("pause_requested", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("stop_requested", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("cities", sa.JSON(), nullable=True),
        sa.Column("categories", sa.JSON(), nullable=True),
        sa.Column("max_queries", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("job_id"),
    )


def downgrade() -> None:
    op.drop_table("bulk_jobs")
