"""Tokens de recuperación de contraseña.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tokens_recuperacion",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("huella", sa.String(length=64), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tokens_recuperacion_huella"), "tokens_recuperacion", ["huella"], unique=True
    )
    op.create_index(
        op.f("ix_tokens_recuperacion_usuario_id"),
        "tokens_recuperacion",
        ["usuario_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tokens_recuperacion_usuario_id"), table_name="tokens_recuperacion")
    op.drop_index(op.f("ix_tokens_recuperacion_huella"), table_name="tokens_recuperacion")
    op.drop_table("tokens_recuperacion")
