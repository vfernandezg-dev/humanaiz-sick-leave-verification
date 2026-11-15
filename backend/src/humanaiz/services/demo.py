"""Modo demo: usuarios de prueba públicos, aislados por visitante.

Reglas que este módulo hace cumplir:
- Las credenciales salen de la configuración, nunca del código.
- El modo demo y los usuarios reales son excluyentes: la cuenta pública de RRHH
  no debe poder listar personas reales.
- Con DEMO_MODE=false no puede quedar activa ninguna cuenta de prueba.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from humanaiz.config import ConfigError, Settings
from humanaiz.models import Colaborador, User, UserSession
from humanaiz.scanning.preprocess import Limits
from humanaiz.security.passwords import hash_password
from humanaiz.services import demo_muestras
from humanaiz.storage.base import Storage

# Personas ficticias para poblar el padrón de la demo.
_PADRON_MUESTRA: tuple[dict[str, object], ...] = (
    {
        "dni": "70000011",
        "apellidos": "Quispe Mamani",
        "nombres": "Rosa Elena",
        "fecha_nacimiento": date(1990, 3, 14),
        "categoria": "B",
        "sexo": "F",
        "celular": "900000011",
        "area_operacion": "Atención al cliente",
        "tipo_contrato": "Indeterminado",
        "sede": "Lima Centro",
    },
    {
        "dni": "70000012",
        "apellidos": "Huamán Rojas",
        "nombres": "Luis Alberto",
        "fecha_nacimiento": date(1985, 11, 2),
        "categoria": "A",
        "sexo": "M",
        "celular": "900000012",
        "area_operacion": "Logística",
        "tipo_contrato": "Indeterminado",
        "sede": "Callao",
    },
    {
        "dni": "70000013",
        "apellidos": "Flores Castillo",
        "nombres": "María Fernanda",
        "fecha_nacimiento": date(1996, 7, 21),
        "categoria": "C",
        "sexo": "F",
        "celular": None,
        "area_operacion": "Ventas",
        "tipo_contrato": "Plazo fijo",
        "sede": "Arequipa",
    },
    {
        "dni": "70000014",
        "apellidos": "Torres Vega",
        "nombres": "Jorge Luis",
        "fecha_nacimiento": date(1979, 1, 30),
        "categoria": "D",
        "sexo": "M",
        "celular": "900000014",
        "area_operacion": "Mantenimiento",
        "tipo_contrato": "Plazo fijo",
        "sede": "Lima Norte",
    },
    {
        "dni": "70000015",
        "apellidos": "Chávez Paredes",
        "nombres": "Ana Lucía",
        "fecha_nacimiento": date(1992, 9, 8),
        "categoria": "B",
        "sexo": "F",
        "celular": "900000015",
        "area_operacion": "Finanzas",
        "tipo_contrato": "Indeterminado",
        "sede": "Lima Centro",
        "activo": False,
    },
)

_DEMO_COLABORADOR = {
    "apellidos": "Ramírez Soto",
    "nombres": "Carlos Daniel",
    "fecha_nacimiento": date(1991, 5, 17),
    "categoria": "C",
    "sexo": "M",
    "celular": "900000001",
    "area_operacion": "Operaciones",
    "tipo_contrato": "Indeterminado",
    "sede": "Lima Centro",
}
_DEMO_RRHH = {
    "apellidos": "Mendoza Ríos",
    "nombres": "Patricia Isabel",
    "fecha_nacimiento": date(1987, 12, 4),
    "categoria": "A",
    "sexo": "F",
    "celular": "900000002",
    "area_operacion": "Recursos Humanos",
    "tipo_contrato": "Indeterminado",
    "sede": "Lima Centro",
}


@dataclass(frozen=True, slots=True)
class ResultadoSiembra:
    usuarios: int
    colaboradores: int
    muestras: int = 0


async def assert_mode_consistency(session: AsyncSession, settings: Settings) -> None:
    """Se ejecuta al arrancar la API: impide mezclar demo y usuarios reales."""
    reales = await session.scalar(
        select(func.count()).select_from(User).where(User.is_demo.is_(False))
    )
    demo_activos = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.is_demo.is_(True), User.is_active.is_(True))
    )
    if settings.demo_mode and reales:
        raise ConfigError(
            f"DEMO_MODE=true pero existen {reales} usuarios reales. Las cuentas de prueba son "
            "públicas y la de RRHH podría ver a personas reales: usa una base de datos "
            "distinta para la demo."
        )
    if not settings.demo_mode and demo_activos:
        raise ConfigError(
            f"Hay {demo_activos} cuentas de prueba activas con DEMO_MODE=false. Ejecuta "
            "`humanaiz seed-demo --if-enabled` para desactivarlas antes de arrancar."
        )


async def _upsert_colaborador(
    session: AsyncSession, dni: str, datos: dict[str, object], user: User | None
) -> Colaborador:
    colaborador = await session.scalar(select(Colaborador).where(Colaborador.dni == dni))
    if colaborador is None:
        colaborador = Colaborador(dni=dni)
        session.add(colaborador)
    for campo, valor in datos.items():
        if campo != "dni":
            setattr(colaborador, campo, valor)
    if "activo" not in datos:
        colaborador.activo = True
    if user is not None:
        colaborador.user = user
    return colaborador


async def _upsert_demo_user(
    session: AsyncSession, *, dni: str, password: str, role: str, datos: dict[str, object]
) -> User:
    user = await session.scalar(select(User).where(User.dni == dni))
    if user is None:
        user = User(dni=dni, role=role, is_demo=True)
        session.add(user)
    elif not user.is_demo:
        raise ConfigError(f"El DNI de demo {dni} ya pertenece a un usuario real.")
    user.role = role
    user.nombres = str(datos["nombres"])
    user.apellidos = str(datos["apellidos"])
    user.password_hash = hash_password(password)
    user.is_active = True
    return user


async def seed(
    session: AsyncSession, settings: Settings, storage: Storage | None = None
) -> ResultadoSiembra:
    """Crea o actualiza las cuentas de prueba y el padrón de muestra. Idempotente.

    Con `storage` siembra además los descansos de muestra con su análisis.
    """
    if not settings.demo_mode:
        raise ConfigError("DEMO_MODE no está activo.")
    await assert_mode_consistency(session, settings)
    if settings.demo_colaborador_dni == settings.demo_rrhh_dni:
        raise ConfigError("DEMO_COLABORADOR_DNI y DEMO_RRHH_DNI deben ser distintos.")

    colaborador_user = await _upsert_demo_user(
        session,
        dni=settings.demo_colaborador_dni,
        password=settings.demo_colaborador_password.get_secret_value(),
        role="colaborador",
        datos=_DEMO_COLABORADOR,
    )
    rrhh_user = await _upsert_demo_user(
        session,
        dni=settings.demo_rrhh_dni,
        password=settings.demo_rrhh_password.get_secret_value(),
        role="analista_rrhh",
        datos=_DEMO_RRHH,
    )
    await session.flush()
    padron: dict[str, Colaborador] = {
        settings.demo_colaborador_dni: await _upsert_colaborador(
            session, settings.demo_colaborador_dni, _DEMO_COLABORADOR, colaborador_user
        ),
        settings.demo_rrhh_dni: await _upsert_colaborador(
            session, settings.demo_rrhh_dni, _DEMO_RRHH, rrhh_user
        ),
    }
    for persona in _PADRON_MUESTRA:
        dni = str(persona["dni"])
        if dni not in padron:
            padron[dni] = await _upsert_colaborador(session, dni, persona, None)
    await session.flush()

    muestras = 0
    if storage is not None:
        muestras = await demo_muestras.sembrar(
            session,
            storage,
            hoy=datetime.now(ZoneInfo(settings.tz_negocio)).date(),
            limits=Limits(
                max_pixels=settings.max_image_pixels,
                max_pdf_pages=settings.max_pdf_pages,
                page_max_side_px=settings.page_max_side_px,
                timeout_seconds=settings.normalize_timeout_seconds,
            ),
            colaboradores=padron,
            colaborador_user=colaborador_user,
            rrhh_user=rrhh_user,
        )

    await session.commit()
    return ResultadoSiembra(usuarios=2, colaboradores=len(padron), muestras=muestras)


async def disable(session: AsyncSession) -> int:
    """Desactiva las cuentas de prueba y cierra sus sesiones. Devuelve cuántas había."""
    ids = (
        await session.scalars(
            select(User.id).where(User.is_demo.is_(True), User.is_active.is_(True))
        )
    ).all()
    if not ids:
        return 0
    await session.execute(update(User).where(User.id.in_(ids)).values(is_active=False))
    await session.execute(
        update(UserSession)
        .where(UserSession.user_id.in_(ids), UserSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()
    return len(ids)
