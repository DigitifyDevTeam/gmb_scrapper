"""Migrate legacy http_failure website_reason to under_construction.

Revision ID: 003
Revises: 002
Create Date: 2026-06-17
"""

from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE prospects SET website_reason = 'under_construction' "
        "WHERE website_reason = 'http_failure'"
    )


def downgrade() -> None:
    pass
