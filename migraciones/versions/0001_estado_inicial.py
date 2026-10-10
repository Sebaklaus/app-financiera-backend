"""Estado inicial: usuarios, movimientos, confirmaciones, tokens de refresco e intentos de login.

Revision ID: 0001
Revises:
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hash_contrasena", sa.String(length=100), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "movimientos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("monto", sa.BigInteger(), nullable=False),
        sa.Column("categoria", sa.String(length=20), nullable=True),
        sa.Column("descripcion", sa.String(length=200), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("monto > 0", name="movimientos_monto_positivo"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_movimientos_usuario_id"), "movimientos", ["usuario_id"])
    op.create_table(
        "confirmaciones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("ingreso_id", sa.Uuid(), nullable=False),
        sa.Column("categoria", sa.String(length=20), nullable=False),
        sa.Column("monto", sa.BigInteger(), nullable=False),
        sa.Column("estado", sa.String(length=12), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decidido_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("monto > 0", name="confirmaciones_monto_positivo"),
        sa.ForeignKeyConstraint(["ingreso_id"], ["movimientos.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_confirmaciones_usuario_id"), "confirmaciones", ["usuario_id"])
    op.create_index(op.f("ix_confirmaciones_ingreso_id"), "confirmaciones", ["ingreso_id"])
    op.create_table(
        "tokens_refresco",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("huella", sa.String(length=64), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocado_en", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tokens_refresco_usuario_id"), "tokens_refresco", ["usuario_id"])
    op.create_index(op.f("ix_tokens_refresco_huella"), "tokens_refresco", ["huella"], unique=True)
    op.create_table(
        "intentos_login",
        sa.Column("clave", sa.String(length=64), nullable=False),
        sa.Column("fallos", sa.Integer(), nullable=False),
        sa.Column("primer_fallo", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("clave"),
    )


def downgrade() -> None:
    op.drop_table("intentos_login")
    op.drop_index(op.f("ix_tokens_refresco_huella"), table_name="tokens_refresco")
    op.drop_index(op.f("ix_tokens_refresco_usuario_id"), table_name="tokens_refresco")
    op.drop_table("tokens_refresco")
    op.drop_index(op.f("ix_confirmaciones_ingreso_id"), table_name="confirmaciones")
    op.drop_index(op.f("ix_confirmaciones_usuario_id"), table_name="confirmaciones")
    op.drop_table("confirmaciones")
    op.drop_index(op.f("ix_movimientos_usuario_id"), table_name="movimientos")
    op.drop_table("movimientos")
    op.drop_table("usuarios")
