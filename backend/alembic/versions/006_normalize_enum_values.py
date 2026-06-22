"""Normalize enum columns to use member values instead of names.

Revision ID: 006
Revises: 005
Create Date: 2026-06-22
"""

from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_WEBSITE_REASON_RENAMES = (
    ("NO_URL", "no_url"),
    ("DNS_FAILURE", "dns_failure"),
    ("HTTP_FAILURE", "http_failure"),
    ("SOCIAL_ONLY", "social_only"),
    ("UNDER_CONSTRUCTION", "under_construction"),
    ("VALID", "valid"),
)

_SEARCH_STATUS_RENAMES = (
    ("PENDING", "pending"),
    ("RUNNING", "running"),
    ("PAUSED", "paused"),
    ("STOPPED", "stopped"),
    ("COMPLETED", "completed"),
    ("FAILED", "failed"),
)


def _rename_column(table: str, column: str, renames: tuple[tuple[str, str], ...]) -> None:
    for old_value, new_value in renames:
        op.execute(
            f"UPDATE {table} SET {column} = '{new_value}' "
            f"WHERE {column} = '{old_value}'"
        )


def upgrade() -> None:
    _rename_column("prospects", "website_reason", _WEBSITE_REASON_RENAMES)
    _rename_column("searches", "status", _SEARCH_STATUS_RENAMES)
    _rename_column("bulk_jobs", "status", _SEARCH_STATUS_RENAMES)


def downgrade() -> None:
    for new_value, old_value in reversed(_WEBSITE_REASON_RENAMES):
        op.execute(
            f"UPDATE prospects SET website_reason = '{old_value}' "
            f"WHERE website_reason = '{new_value}'"
        )
    for new_value, old_value in reversed(_SEARCH_STATUS_RENAMES):
        op.execute(
            f"UPDATE searches SET status = '{old_value}' "
            f"WHERE status = '{new_value}'"
        )
        op.execute(
            f"UPDATE bulk_jobs SET status = '{old_value}' "
            f"WHERE status = '{new_value}'"
        )
