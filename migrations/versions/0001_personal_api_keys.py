"""Ajoute is_personal à devkeys_api_keys

Revision ID: 0001_personal_api_keys
Revises: None
Create Date: 2026-08-21

Introduit les clés "personnelles" (xcli login — flux device-code) :
authentifient comme un user_id nu, sans projet, acceptées pour tout
plugin/service public (voir routes/install.py des plugins marketplace et
xservices). Idempotente comme les migrations marketplace 0001/0002/0003 —
create_all() a déjà créé la colonne sur une base neuve.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_personal_api_keys"
down_revision = None
branch_labels = None
depends_on = None

_TABLE = "devkeys_api_keys"


def _existing_columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {c["name"] for c in inspector.get_columns(_TABLE)}


def upgrade() -> None:
    if "is_personal" not in _existing_columns():
        op.add_column(
            _TABLE,
            sa.Column("is_personal", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    if "is_personal" in _existing_columns():
        op.drop_column(_TABLE, "is_personal")
