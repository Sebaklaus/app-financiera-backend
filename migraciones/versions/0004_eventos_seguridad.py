"""Bitácora de eventos de seguridad.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "eventos_seguridad",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=True),
        sa.Column("ip_huella", sa.String(length=64), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_eventos_seguridad_creado_en"), "eventos_seguridad", ["creado_en"])
    op.create_index(op.f("ix_eventos_seguridad_tipo"), "eventos_seguridad", ["tipo"])
    op.create_index(op.f("ix_eventos_seguridad_usuario_id"), "eventos_seguridad", ["usuario_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_eventos_seguridad_usuario_id"), table_name="eventos_seguridad")
    op.drop_index(op.f("ix_eventos_seguridad_tipo"), table_name="eventos_seguridad")
    op.drop_index(op.f("ix_eventos_seguridad_creado_en"), table_name="eventos_seguridad")
    op.drop_table("eventos_seguridad")
