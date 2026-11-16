"""archivos guardados en la base

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "archivos_guardados",
        sa.Column("prefijo", sa.String(length=64), nullable=False),
        sa.Column("nombre", sa.String(length=32), nullable=False),
        sa.Column("datos", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("prefijo", "nombre", name=op.f("pk_archivos_guardados")),
    )


def downgrade() -> None:
    op.drop_table("archivos_guardados")
