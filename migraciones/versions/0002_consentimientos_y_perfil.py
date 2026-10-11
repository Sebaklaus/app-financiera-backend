"""Consentimientos (historial) y perfil de riesgo.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consentimientos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("otorgado", sa.Boolean(), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_consentimientos_usuario_id"), "consentimientos", ["usuario_id"], unique=False
    )
    op.create_table(
        "perfiles_riesgo",
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("perfil", sa.String(length=15), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("usuario_id"),
    )


def downgrade() -> None:
    op.drop_table("perfiles_riesgo")
    op.drop_index(op.f("ix_consentimientos_usuario_id"), table_name="consentimientos")
    op.drop_table("consentimientos")
