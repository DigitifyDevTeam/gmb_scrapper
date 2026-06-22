"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "searches",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=150), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "completed",
                "failed",
                name="search_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_searches_status", "searches", ["status"])

    op.create_table(
        "prospects",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("search_id", sa.BigInteger(), nullable=False),
        sa.Column("business_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=150), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("rating", sa.Numeric(precision=2, scale=1), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=True),
        sa.Column("maps_url", sa.String(length=1000), nullable=True),
        sa.Column("has_website", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "website_reason",
            sa.Enum(
                "no_url",
                "dns_failure",
                "http_failure",
                "social_only",
                "under_construction",
                "valid",
                name="website_reason",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["search_id"], ["searches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prospects_search_id", "prospects", ["search_id"])
    op.create_index("ix_prospects_category", "prospects", ["category"])
    op.create_index("ix_prospects_has_website", "prospects", ["has_website"])
    op.create_index(
        "ix_prospects_search_name_address",
        "prospects",
        ["search_id", "business_name", "address"],
        mysql_length={"address": 191},
    )


def downgrade() -> None:
    op.drop_index("ix_prospects_search_name_address", table_name="prospects")
    op.drop_index("ix_prospects_has_website", table_name="prospects")
    op.drop_index("ix_prospects_category", table_name="prospects")
    op.drop_index("ix_prospects_search_id", table_name="prospects")
    op.drop_table("prospects")
    op.drop_index("ix_searches_status", table_name="searches")
    op.drop_table("searches")
