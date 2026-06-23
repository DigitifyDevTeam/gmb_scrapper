"""Add bulk job counters for total and with-website saves.

Revision ID: 008
Revises: 007
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(connection, table: str) -> set[str]:
    inspector = sa.inspect(connection)
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    connection = op.get_bind()
    columns = _column_names(connection, "bulk_jobs")

    if "prospects_saved_with_website" not in columns:
        op.add_column(
            "bulk_jobs",
            sa.Column(
                "prospects_saved_with_website",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if "prospects_saved_total" not in columns:
        op.add_column(
            "bulk_jobs",
            sa.Column(
                "prospects_saved_total",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade() -> None:
    connection = op.get_bind()
    columns = _column_names(connection, "bulk_jobs")

    if "prospects_saved_total" in columns:
        op.drop_column("bulk_jobs", "prospects_saved_total")
    if "prospects_saved_with_website" in columns:
        op.drop_column("bulk_jobs", "prospects_saved_with_website")
