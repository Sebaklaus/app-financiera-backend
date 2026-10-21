"""Enlaces bancarios (link_token de Fintoc, cifrado).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "enlaces_bancarios",
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("token_cifrado", sa.String(length=600), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("usuario_id"),
    )


def downgrade() -> None:
    op.drop_table("enlaces_bancarios")
