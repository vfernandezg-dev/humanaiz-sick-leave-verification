"""Modelo de datos. Las enumeraciones son varchar + CHECK (más fáciles de migrar)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    SmallInteger,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

ROLES = ("colaborador", "analista_rrhh")
ESTADOS_DESCANSO = ("Pendiente", "Aprobado", "Rechazado")
ESTADOS_DOCUMENTO = ("Aprobado", "Observado", "Rechazado")
ESTADOS_ANALISIS = ("en_proceso", "completado", "fallido")
CATEGORIAS = ("A", "B", "C", "D")
SEXOS = ("M", "F")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_N_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class _Timestamps:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(_Timestamps, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("dni ~ '^[0-9]{8}$'", name="dni_formato"),
        CheckConstraint(_in("role", ROLES), name="role_valido"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    dni: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    nombres: Mapped[str] = mapped_column(Text, nullable=False)
    apellidos: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    colaborador: Mapped[Colaborador | None] = relationship(back_populates="user", uselist=False)


class UserSession(Base):
    """Sesión de servidor. El token vive solo en la cookie; aquí va su SHA-256."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), unique=True, nullable=False)
    visitor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(200), nullable=True)

    user: Mapped[User] = relationship()


class Colaborador(_Timestamps, Base):
    __tablename__ = "colaboradores"
    __table_args__ = (
        CheckConstraint("dni ~ '^[0-9]{8}$'", name="dni_formato"),
        CheckConstraint(_in("categoria", CATEGORIAS), name="categoria_valida"),
        CheckConstraint(_in("sexo", SEXOS), name="sexo_valido"),
        Index("ix_colaboradores_apellidos_nombres", "apellidos", "nombres"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    dni: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    apellidos: Mapped[str] = mapped_column(Text, nullable=False)
    nombres: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_nacimiento: Mapped[date] = mapped_column(Date, nullable=False)
    categoria: Mapped[str] = mapped_column(String(1), nullable=False)
    sexo: Mapped[str] = mapped_column(String(1), nullable=False)
    celular: Mapped[str | None] = mapped_column(String(15), nullable=True)
    area_operacion: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_contrato: Mapped[str] = mapped_column(Text, nullable=False)
    sede: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    user: Mapped[User | None] = relationship(back_populates="colaborador")


class DescansoMedico(_Timestamps, Base):
    __tablename__ = "descansos_medicos"
    __table_args__ = (
        CheckConstraint(_in("estado", ESTADOS_DESCANSO), name="estado_valido"),
        CheckConstraint("char_length(sede) BETWEEN 1 AND 100", name="sede_longitud"),
        CheckConstraint(
            "comentario_rrhh IS NULL OR char_length(comentario_rrhh) <= 1000",
            name="comentario_longitud",
        ),
        CheckConstraint(
            "fecha_inicio IS NULL OR fecha_fin IS NULL OR fecha_fin >= fecha_inicio",
            name="fechas_coherentes",
        ),
        CheckConstraint(
            "estado <> 'Aprobado' OR (fecha_inicio IS NOT NULL AND fecha_fin IS NOT NULL)",
            name="aprobado_con_fechas",
        ),
        CheckConstraint(
            "(estado = 'Pendiente') = (decidido_at IS NULL)", name="decision_consistente"
        ),
        CheckConstraint("paginas BETWEEN 1 AND 20", name="paginas_rango"),
        Index("ix_descansos_colaborador_creado", "colaborador_id", text("created_at DESC")),
        Index("ix_descansos_estado_creado", "estado", text("created_at DESC")),
        Index("ix_descansos_autor_creado", "created_by", text("created_at DESC")),
        Index("ix_descansos_sha256", "archivo_sha256"),
        Index(
            "ix_descansos_visitante_creado",
            "created_at",
            postgresql_where=text("visitor_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    colaborador_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("colaboradores.id", ondelete="RESTRICT"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    estado: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'Pendiente'")
    )
    sede: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    comentario_rrhh: Mapped[str | None] = mapped_column(Text, nullable=True)
    decidido_por: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    decidido_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archivo_key: Mapped[str] = mapped_column(Text, nullable=False)
    archivo_mime: Mapped[str] = mapped_column(String(30), nullable=False)
    archivo_size: Mapped[int] = mapped_column(Integer, nullable=False)
    archivo_sha256: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    paginas: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    visitor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    es_muestra: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    colaborador: Mapped[Colaborador] = relationship(lazy="joined", innerjoin=True)


class AnalisisDescanso(Base):
    __tablename__ = "analisis_descanso"
    __table_args__ = (
        CheckConstraint(_in("estado", ESTADOS_ANALISIS), name="estado_valido"),
        CheckConstraint(
            "estado_documento IS NULL OR " + _in("estado_documento", ESTADOS_DOCUMENTO),
            name="estado_documento_valido",
        ),
        CheckConstraint(
            "estado <> 'completado' OR (resultado IS NOT NULL AND estado_documento IS NOT NULL)",
            name="completado_con_resultado",
        ),
        Index("ix_analisis_descanso_inicio", "descanso_id", text("started_at DESC")),
        # Garantiza, también entre réplicas, un solo análisis en curso por descanso.
        Index(
            "uq_analisis_en_proceso",
            "descanso_id",
            unique=True,
            postgresql_where=text("estado = 'en_proceso'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    descanso_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("descansos_medicos.id", ondelete="CASCADE"), nullable=False
    )
    solicitado_por: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    proveedor: Mapped[str] = mapped_column(String(20), nullable=False)
    modelo: Mapped[str] = mapped_column(String(120), nullable=False)
    modelo_efectivo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    estado: Mapped[str] = mapped_column(String(12), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    extraccion: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    resultado: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    estado_documento: Mapped[str | None] = mapped_column(String(10), nullable=True)
    version_prompt: Mapped[str] = mapped_column(String(20), nullable=False)
    version_reglas: Mapped[str] = mapped_column(String(20), nullable=False)
    tokens_entrada: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_salida: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duracion_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    proveedor_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    solicitante: Mapped[User] = relationship(lazy="joined", innerjoin=True)


class AuditLog(Base):
    """Bitácora de solo escritura. `actor_id` sin FK: sobrevive al borrado del usuario."""

    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_entidad", "entidad", "entidad_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    accion: Mapped[str] = mapped_column(String(40), nullable=False)
    entidad: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entidad_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    ip: Mapped[str | None] = mapped_column(INET, nullable=True)
    detalle: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


class ArchivoGuardado(Base):
    """Imágenes guardadas en la propia base (STORAGE_BACKEND=database).

    Para plataformas sin disco persistente (Vercel). Con almacenamiento local la
    tabla queda vacía. Sin FK a los descansos, igual que los archivos en disco:
    la purga barre los que quedan huérfanos.
    """

    __tablename__ = "archivos_guardados"

    prefijo: Mapped[str] = mapped_column(String(64), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(32), primary_key=True)
    datos: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
