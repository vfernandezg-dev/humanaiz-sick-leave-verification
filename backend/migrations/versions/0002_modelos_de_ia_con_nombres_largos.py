"""modelos de ia con nombres largos

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:

    op.alter_column(
        "analisis_descanso",
        "modelo",
        existing_type=sa.VARCHAR(length=80),
        type_=sa.String(length=120),
        existing_nullable=False,
    )
    op.alter_column(
        "analisis_descanso",
        "modelo_efectivo",
        existing_type=sa.VARCHAR(length=80),
        type_=sa.String(length=120),
        existing_nullable=True,
    )


def downgrade() -> None:

    op.alter_column(
        "analisis_descanso",
        "modelo_efectivo",
        existing_type=sa.String(length=120),
        type_=sa.VARCHAR(length=80),
        existing_nullable=True,
    )
    op.alter_column(
        "analisis_descanso",
        "modelo",
        existing_type=sa.String(length=120),
        type_=sa.VARCHAR(length=80),
        existing_nullable=False,
    )
