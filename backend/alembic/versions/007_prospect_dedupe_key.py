"""Add global prospect dedupe_key and remove duplicate rows.

Revision ID: 007
Revises: 006
Create Date: 2026-06-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.utils.prospect_identity import build_prospect_dedupe_key

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _prospect_column_names(connection) -> set[str]:
    inspector = sa.inspect(connection)
    return {column["name"] for column in inspector.get_columns("prospects")}


def _prospect_index_names(connection) -> set[str]:
    inspector = sa.inspect(connection)
    return {index["name"] for index in inspector.get_indexes("prospects")}


def _dedupe_key_is_nullable(connection) -> bool:
    inspector = sa.inspect(connection)
    for column in inspector.get_columns("prospects"):
        if column["name"] == "dedupe_key":
            return bool(column.get("nullable", True))
    return True


def _backfill_dedupe_keys(connection) -> None:
    prospects = sa.Table(
        "prospects",
        sa.MetaData(),
        sa.Column("id", sa.BigInteger),
        sa.Column("search_id", sa.BigInteger),
        sa.Column("business_name", sa.String),
        sa.Column("address", sa.Text),
        sa.Column("phone", sa.String),
        sa.Column("maps_url", sa.Text),
        sa.Column("dedupe_key", sa.String),
        sa.Column("maps_place_id", sa.String),
    )
    searches = sa.Table(
        "searches",
        sa.MetaData(),
        sa.Column("id", sa.BigInteger),
        sa.Column("country", sa.String),
    )

    rows = connection.execute(
        sa.select(
            prospects.c.id,
            prospects.c.business_name,
            prospects.c.address,
            prospects.c.phone,
            prospects.c.maps_url,
            searches.c.country,
        )
        .select_from(prospects.outerjoin(searches, prospects.c.search_id == searches.c.id))
        .where(prospects.c.dedupe_key.is_(None))
        .order_by(prospects.c.id.asc())
    ).fetchall()

    for row in rows:
        dedupe_key, place_id = build_prospect_dedupe_key(
            business_name=row.business_name,
            address=row.address,
            phone=row.phone,
            maps_url=row.maps_url,
            country=row.country,
        )
        connection.execute(
            prospects.update()
            .where(prospects.c.id == row.id)
            .values(dedupe_key=dedupe_key, maps_place_id=place_id)
        )


def _delete_duplicate_rows(connection) -> None:
    prospects = sa.Table(
        "prospects",
        sa.MetaData(),
        sa.Column("id", sa.BigInteger),
        sa.Column("dedupe_key", sa.String),
    )
    duplicate_keys = connection.execute(
        sa.select(prospects.c.dedupe_key)
        .where(prospects.c.dedupe_key.is_not(None))
        .group_by(prospects.c.dedupe_key)
        .having(sa.func.count() > 1)
    ).fetchall()

    for (dedupe_key,) in duplicate_keys:
        ids = connection.execute(
            sa.select(prospects.c.id)
            .where(prospects.c.dedupe_key == dedupe_key)
            .order_by(prospects.c.id.asc())
        ).fetchall()
        ids_to_delete = [row.id for row in ids[1:]]
        if ids_to_delete:
            connection.execute(prospects.delete().where(prospects.c.id.in_(ids_to_delete)))


def upgrade() -> None:
    connection = op.get_bind()
    columns = _prospect_column_names(connection)

    if "maps_place_id" not in columns:
        op.add_column("prospects", sa.Column("maps_place_id", sa.String(length=255), nullable=True))
    if "dedupe_key" not in columns:
        op.add_column("prospects", sa.Column("dedupe_key", sa.String(length=512), nullable=True))

    _backfill_dedupe_keys(connection)
    _delete_duplicate_rows(connection)

    if _dedupe_key_is_nullable(connection):
        op.alter_column("prospects", "dedupe_key", existing_type=sa.String(length=512), nullable=False)

    indexes = _prospect_index_names(connection)
    if "ix_prospects_maps_place_id" not in indexes:
        op.create_index("ix_prospects_maps_place_id", "prospects", ["maps_place_id"])
    if "ux_prospects_dedupe_key" not in indexes:
        op.create_index("ux_prospects_dedupe_key", "prospects", ["dedupe_key"], unique=True)


def downgrade() -> None:
    connection = op.get_bind()
    indexes = _prospect_index_names(connection)
    columns = _prospect_column_names(connection)

    if "ux_prospects_dedupe_key" in indexes:
        op.drop_index("ux_prospects_dedupe_key", table_name="prospects")
    if "ix_prospects_maps_place_id" in indexes:
        op.drop_index("ix_prospects_maps_place_id", table_name="prospects")
    if "dedupe_key" in columns:
        op.drop_column("prospects", "dedupe_key")
    if "maps_place_id" in columns:
        op.drop_column("prospects", "maps_place_id")
