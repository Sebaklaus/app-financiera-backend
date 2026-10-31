"""Metas de ahorro y sus aportes (CU-08).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meta_ahorro",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=80), nullable=False),
        sa.Column("monto_objetivo", sa.BigInteger(), nullable=False),
        sa.Column("fecha_limite", sa.Date(), nullable=True),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("monto_objetivo > 0", name="meta_ahorro_monto_positivo"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_meta_ahorro_usuario_id"), "meta_ahorro", ["usuario_id"])
    op.create_table(
        "aporte_meta",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("meta_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("monto", sa.BigInteger(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("monto > 0", name="aporte_meta_monto_positivo"),
        sa.ForeignKeyConstraint(["meta_id"], ["meta_ahorro.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_aporte_meta_meta_id"), "aporte_meta", ["meta_id"])
    op.create_index(op.f("ix_aporte_meta_usuario_id"), "aporte_meta", ["usuario_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_aporte_meta_usuario_id"), table_name="aporte_meta")
    op.drop_index(op.f("ix_aporte_meta_meta_id"), table_name="aporte_meta")
    op.drop_table("aporte_meta")
    op.drop_index(op.f("ix_meta_ahorro_usuario_id"), table_name="meta_ahorro")
    op.drop_table("meta_ahorro")
