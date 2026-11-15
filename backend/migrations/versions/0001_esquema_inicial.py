"""esquema inicial

Revision ID: 0001
Revises: -
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column(
            "at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("accion", sa.String(length=40), nullable=False),
        sa.Column("entidad", sa.String(length=40), nullable=True),
        sa.Column("entidad_id", sa.Uuid(), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("detalle", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(op.f("ix_audit_log_at"), "audit_log", ["at"], unique=False)
    op.create_index("ix_audit_log_entidad", "audit_log", ["entidad", "entidad_id"], unique=False)
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dni", sa.String(length=8), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("nombres", sa.Text(), nullable=False),
        sa.Column("apellidos", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("dni ~ '^[0-9]{8}$'", name=op.f("ck_users_dni_formato")),
        sa.CheckConstraint(
            "role IN ('colaborador', 'analista_rrhh')", name=op.f("ck_users_role_valido")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("dni", name=op.f("uq_users_dni")),
    )
    op.create_table(
        "colaboradores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("dni", sa.String(length=8), nullable=False),
        sa.Column("apellidos", sa.Text(), nullable=False),
        sa.Column("nombres", sa.Text(), nullable=False),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=False),
        sa.Column("categoria", sa.String(length=1), nullable=False),
        sa.Column("sexo", sa.String(length=1), nullable=False),
        sa.Column("celular", sa.String(length=15), nullable=True),
        sa.Column("area_operacion", sa.Text(), nullable=False),
        sa.Column("tipo_contrato", sa.Text(), nullable=False),
        sa.Column("sede", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "categoria IN ('A', 'B', 'C', 'D')", name=op.f("ck_colaboradores_categoria_valida")
        ),
        sa.CheckConstraint("dni ~ '^[0-9]{8}$'", name=op.f("ck_colaboradores_dni_formato")),
        sa.CheckConstraint("sexo IN ('M', 'F')", name=op.f("ck_colaboradores_sexo_valido")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_colaboradores_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_colaboradores")),
        sa.UniqueConstraint("dni", name=op.f("uq_colaboradores_dni")),
        sa.UniqueConstraint("user_id", name=op.f("uq_colaboradores_user_id")),
    )
    op.create_index(
        "ix_colaboradores_apellidos_nombres",
        "colaboradores",
        ["apellidos", "nombres"],
        unique=False,
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(length=32), nullable=False),
        sa.Column("visitor_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )
    op.create_index(op.f("ix_sessions_expires_at"), "sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)
    op.create_table(
        "descansos_medicos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("colaborador_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "estado", sa.String(length=10), server_default=sa.text("'Pendiente'"), nullable=False
        ),
        sa.Column("sede", sa.Text(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=True),
        sa.Column("fecha_fin", sa.Date(), nullable=True),
        sa.Column("comentario_rrhh", sa.Text(), nullable=True),
        sa.Column("decidido_por", sa.Uuid(), nullable=True),
        sa.Column("decidido_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archivo_key", sa.Text(), nullable=False),
        sa.Column("archivo_mime", sa.String(length=30), nullable=False),
        sa.Column("archivo_size", sa.Integer(), nullable=False),
        sa.Column("archivo_sha256", sa.LargeBinary(length=32), nullable=False),
        sa.Column("paginas", sa.SmallInteger(), nullable=False),
        sa.Column("visitor_id", sa.Uuid(), nullable=True),
        sa.Column("es_muestra", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(estado = 'Pendiente') = (decidido_at IS NULL)",
            name=op.f("ck_descansos_medicos_decision_consistente"),
        ),
        sa.CheckConstraint(
            "estado <> 'Aprobado' OR (fecha_inicio IS NOT NULL AND fecha_fin IS NOT NULL)",
            name=op.f("ck_descansos_medicos_aprobado_con_fechas"),
        ),
        sa.CheckConstraint(
            "estado IN ('Pendiente', 'Aprobado', 'Rechazado')",
            name=op.f("ck_descansos_medicos_estado_valido"),
        ),
        sa.CheckConstraint(
            "char_length(sede) BETWEEN 1 AND 100", name=op.f("ck_descansos_medicos_sede_longitud")
        ),
        sa.CheckConstraint(
            "comentario_rrhh IS NULL OR char_length(comentario_rrhh) <= 1000",
            name=op.f("ck_descansos_medicos_comentario_longitud"),
        ),
        sa.CheckConstraint(
            "fecha_inicio IS NULL OR fecha_fin IS NULL OR fecha_fin >= fecha_inicio",
            name=op.f("ck_descansos_medicos_fechas_coherentes"),
        ),
        sa.CheckConstraint(
            "paginas BETWEEN 1 AND 20", name=op.f("ck_descansos_medicos_paginas_rango")
        ),
        sa.ForeignKeyConstraint(
            ["colaborador_id"],
            ["colaboradores.id"],
            name=op.f("fk_descansos_medicos_colaborador_id_colaboradores"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_descansos_medicos_created_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["decidido_por"],
            ["users.id"],
            name=op.f("fk_descansos_medicos_decidido_por_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_descansos_medicos")),
    )
    op.create_index(
        "ix_descansos_autor_creado",
        "descansos_medicos",
        ["created_by", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_descansos_colaborador_creado",
        "descansos_medicos",
        ["colaborador_id", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_descansos_estado_creado",
        "descansos_medicos",
        ["estado", sa.literal_column("created_at DESC")],
        unique=False,
    )
    op.create_index("ix_descansos_sha256", "descansos_medicos", ["archivo_sha256"], unique=False)
    op.create_index(
        "ix_descansos_visitante_creado",
        "descansos_medicos",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("visitor_id IS NOT NULL"),
    )
    op.create_table(
        "analisis_descanso",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("descanso_id", sa.Uuid(), nullable=False),
        sa.Column("solicitado_por", sa.Uuid(), nullable=False),
        sa.Column("proveedor", sa.String(length=20), nullable=False),
        sa.Column("modelo", sa.String(length=80), nullable=False),
        sa.Column("modelo_efectivo", sa.String(length=80), nullable=True),
        sa.Column("estado", sa.String(length=12), nullable=False),
        sa.Column("error_code", sa.String(length=40), nullable=True),
        sa.Column("extraccion", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resultado", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("estado_documento", sa.String(length=10), nullable=True),
        sa.Column("version_prompt", sa.String(length=20), nullable=False),
        sa.Column("version_reglas", sa.String(length=20), nullable=False),
        sa.Column("tokens_entrada", sa.Integer(), nullable=True),
        sa.Column("tokens_salida", sa.Integer(), nullable=True),
        sa.Column("duracion_ms", sa.Integer(), nullable=True),
        sa.Column("proveedor_request_id", sa.String(length=100), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "estado <> 'completado' OR (resultado IS NOT NULL AND estado_documento IS NOT NULL)",
            name=op.f("ck_analisis_descanso_completado_con_resultado"),
        ),
        sa.CheckConstraint(
            "estado IN ('en_proceso', 'completado', 'fallido')",
            name=op.f("ck_analisis_descanso_estado_valido"),
        ),
        sa.CheckConstraint(
            "estado_documento IS NULL OR estado_documento IN ('Aprobado', 'Observado', 'Rechazado')",
            name=op.f("ck_analisis_descanso_estado_documento_valido"),
        ),
        sa.ForeignKeyConstraint(
            ["descanso_id"],
            ["descansos_medicos.id"],
            name=op.f("fk_analisis_descanso_descanso_id_descansos_medicos"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["solicitado_por"],
            ["users.id"],
            name=op.f("fk_analisis_descanso_solicitado_por_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analisis_descanso")),
    )
    op.create_index(
        "ix_analisis_descanso_inicio",
        "analisis_descanso",
        ["descanso_id", sa.literal_column("started_at DESC")],
        unique=False,
    )
    op.create_index(
        "uq_analisis_en_proceso",
        "analisis_descanso",
        ["descanso_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'en_proceso'"),
    )


def downgrade() -> None:

    op.drop_index(
        "uq_analisis_en_proceso",
        table_name="analisis_descanso",
        postgresql_where=sa.text("estado = 'en_proceso'"),
    )
    op.drop_index("ix_analisis_descanso_inicio", table_name="analisis_descanso")
    op.drop_table("analisis_descanso")
    op.drop_index(
        "ix_descansos_visitante_creado",
        table_name="descansos_medicos",
        postgresql_where=sa.text("visitor_id IS NOT NULL"),
    )
    op.drop_index("ix_descansos_sha256", table_name="descansos_medicos")
    op.drop_index("ix_descansos_estado_creado", table_name="descansos_medicos")
    op.drop_index("ix_descansos_colaborador_creado", table_name="descansos_medicos")
    op.drop_index("ix_descansos_autor_creado", table_name="descansos_medicos")
    op.drop_table("descansos_medicos")
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_expires_at"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_colaboradores_apellidos_nombres", table_name="colaboradores")
    op.drop_table("colaboradores")
    op.drop_table("users")
    op.drop_index("ix_audit_log_entidad", table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_at"), table_name="audit_log")
    op.drop_table("audit_log")
