"""Comandos de administración: `humanaiz <comando>` o `python -m humanaiz.cli`.

No existe registro público de usuarios: las cuentas reales se crean aquí, desde
el servidor. Las contraseñas se piden por teclado o se leen de stdin; nunca se
pasan como argumento (quedarían en el historial del shell).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import getpass
import json
import re
import sys
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime

from sqlalchemy import select, update

from humanaiz.config import ConfigError, Settings, get_settings
from humanaiz.db import Database
from humanaiz.models import CATEGORIAS, ROLES, SEXOS, Colaborador, User, UserSession
from humanaiz.security.passwords import hash_password, validate_new_password
from humanaiz.services import demo

Handler = Callable[[argparse.Namespace, Settings], Awaitable[int]]

_DNI = re.compile(r"^[0-9]{8}$")
_COLUMNAS_CSV = (
    "dni",
    "apellidos",
    "nombres",
    "fecha_nacimiento",
    "categoria",
    "sexo",
    "celular",
    "area_operacion",
    "tipo_contrato",
    "sede",
    "activo",
)


def _error(mensaje: str) -> int:
    print(f"Error: {mensaje}", file=sys.stderr)
    return 2


def _leer_password(desde_stdin: bool) -> str:
    if desde_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    primera = getpass.getpass("Contraseña: ")
    if primera != getpass.getpass("Repite la contraseña: "):
        raise ValueError("Las contraseñas no coinciden.")
    return primera


async def _create_user(args: argparse.Namespace, settings: Settings) -> int:
    if settings.demo_mode:
        return _error("con DEMO_MODE=true no se crean usuarios reales (ver README).")
    if not _DNI.match(args.dni):
        return _error("el DNI debe tener 8 dígitos.")
    try:
        password = _leer_password(args.password_stdin)
        validate_new_password(password)
    except ValueError as exc:
        return _error(str(exc))

    db = Database(settings.database_url, pool_size=1)
    try:
        async with db.session() as session:
            if await session.scalar(select(User.id).where(User.dni == args.dni)):
                return _error(f"ya existe un usuario con DNI {args.dni}.")
            user = User(
                dni=args.dni,
                nombres=args.nombres.strip(),
                apellidos=args.apellidos.strip(),
                role=args.role,
                password_hash=hash_password(password),
            )
            session.add(user)
            colaborador = await session.scalar(
                select(Colaborador).where(Colaborador.dni == args.dni)
            )
            if colaborador is not None:
                colaborador.user = user
            await session.commit()
    finally:
        await db.dispose()
    vinculo = "vinculado a su ficha de colaborador" if colaborador else "sin ficha de colaborador"
    print(f"Usuario {args.dni} ({args.role}) creado, {vinculo}.")
    return 0


async def _set_password(args: argparse.Namespace, settings: Settings) -> int:
    try:
        password = _leer_password(args.password_stdin)
        validate_new_password(password)
    except ValueError as exc:
        return _error(str(exc))
    db = Database(settings.database_url, pool_size=1)
    try:
        async with db.session() as session:
            user = await session.scalar(select(User).where(User.dni == args.dni))
            if user is None:
                return _error(f"no existe un usuario con DNI {args.dni}.")
            if user.is_demo:
                return _error("las cuentas de prueba toman su contraseña del .env.")
            user.password_hash = hash_password(password)
            # Cambiar la contraseña cierra todas las sesiones abiertas.
            await session.execute(
                update(UserSession)
                .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
                .values(revoked_at=datetime.now(UTC))
            )
            await session.commit()
    finally:
        await db.dispose()
    print(f"Contraseña actualizada para {args.dni}; sus sesiones se cerraron.")
    return 0


def _fila_colaborador(fila: dict[str, str], linea: int) -> dict[str, object]:
    def campo(nombre: str) -> str:
        return (fila.get(nombre) or "").strip()

    dni = campo("dni")
    if not _DNI.match(dni):
        raise ValueError(f"línea {linea}: DNI inválido '{dni}'")
    if campo("categoria") not in CATEGORIAS:
        raise ValueError(f"línea {linea}: categoría debe ser una de {', '.join(CATEGORIAS)}")
    if campo("sexo") not in SEXOS:
        raise ValueError(f"línea {linea}: sexo debe ser M o F")
    for obligatorio in ("apellidos", "nombres", "area_operacion", "tipo_contrato", "sede"):
        if not campo(obligatorio):
            raise ValueError(f"línea {linea}: falta '{obligatorio}'")
    try:
        nacimiento = date.fromisoformat(campo("fecha_nacimiento"))
    except ValueError:
        raise ValueError(f"línea {linea}: fecha_nacimiento debe ser AAAA-MM-DD") from None
    return {
        "dni": dni,
        "apellidos": campo("apellidos"),
        "nombres": campo("nombres"),
        "fecha_nacimiento": nacimiento,
        "categoria": campo("categoria"),
        "sexo": campo("sexo"),
        "celular": campo("celular") or None,
        "area_operacion": campo("area_operacion"),
        "tipo_contrato": campo("tipo_contrato"),
        "sede": campo("sede"),
        "activo": campo("activo").lower() not in {"0", "false", "no", "n"},
    }


async def _import_colaboradores(args: argparse.Namespace, settings: Settings) -> int:
    if settings.demo_mode:
        return _error("con DEMO_MODE=true no se importan colaboradores reales.")
    try:
        with open(args.archivo, encoding="utf-8-sig", newline="") as fh:
            lector = csv.DictReader(fh)
            faltan = [c for c in _COLUMNAS_CSV if c not in (lector.fieldnames or [])]
            if faltan:
                return _error("faltan columnas en el CSV: " + ", ".join(faltan))
            filas = [_fila_colaborador(fila, n) for n, fila in enumerate(lector, start=2)]
    except (OSError, ValueError) as exc:
        return _error(str(exc))

    creados = actualizados = 0
    db = Database(settings.database_url, pool_size=1)
    try:
        async with db.session() as session:
            for datos in filas:
                colaborador = await session.scalar(
                    select(Colaborador).where(Colaborador.dni == datos["dni"])
                )
                if colaborador is None:
                    colaborador = Colaborador()
                    session.add(colaborador)
                    creados += 1
                else:
                    actualizados += 1
                for nombre, valor in datos.items():
                    setattr(colaborador, nombre, valor)
                if colaborador.user_id is None:
                    colaborador.user = await session.scalar(
                        select(User).where(User.dni == datos["dni"])
                    )
                await session.flush()
            await session.commit()
    finally:
        await db.dispose()
    print(f"Colaboradores: {creados} creados, {actualizados} actualizados.")
    return 0


async def _seed_demo(args: argparse.Namespace, settings: Settings) -> int:
    db = Database(settings.database_url, pool_size=1)
    try:
        async with db.session() as session:
            if not settings.demo_mode:
                if not args.if_enabled:
                    return _error("DEMO_MODE no está activo.")
                desactivadas = await demo.disable(session)
                print(
                    f"DEMO_MODE=false: {desactivadas} cuentas de prueba desactivadas."
                    if desactivadas
                    else "DEMO_MODE=false: no hay nada que sembrar."
                )
                return 0
            resultado = await demo.seed(session, settings)
    finally:
        await db.dispose()
    print(
        f"Demo sembrada: {resultado.usuarios} cuentas de prueba, "
        f"{resultado.colaboradores} colaboradores de muestra."
    )
    return 0


async def _export_openapi(args: argparse.Namespace, settings: Settings) -> int:
    from humanaiz.main import create_app

    texto = json.dumps(create_app(settings).openapi(), ensure_ascii=False, indent=2)
    if args.output == "-":
        print(texto)
    else:
        with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(texto + "\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="humanaiz", description="Administración de HumanAIz")
    sub = parser.add_subparsers(dest="comando", required=True)

    crear = sub.add_parser("create-user", help="Crea una cuenta real")
    crear.add_argument("--dni", required=True)
    crear.add_argument("--nombres", required=True)
    crear.add_argument("--apellidos", required=True)
    crear.add_argument("--role", required=True, choices=ROLES)
    crear.add_argument("--password-stdin", action="store_true", help="Lee la contraseña de stdin")
    crear.set_defaults(handler=_create_user)

    clave = sub.add_parser("set-password", help="Cambia la contraseña y cierra sus sesiones")
    clave.add_argument("--dni", required=True)
    clave.add_argument("--password-stdin", action="store_true", help="Lee la contraseña de stdin")
    clave.set_defaults(handler=_set_password)

    importar = sub.add_parser(
        "import-colaboradores",
        help="Crea o actualiza colaboradores desde un CSV (" + ", ".join(_COLUMNAS_CSV) + ")",
    )
    importar.add_argument("archivo")
    importar.set_defaults(handler=_import_colaboradores)

    seed = sub.add_parser("seed-demo", help="Siembra las cuentas de prueba del modo demo")
    seed.add_argument(
        "--if-enabled",
        action="store_true",
        help="Con DEMO_MODE=false no falla: desactiva las cuentas de prueba que existan",
    )
    seed.set_defaults(handler=_seed_demo)

    openapi = sub.add_parser("export-openapi", help="Escribe el esquema OpenAPI de la API")
    openapi.add_argument("--output", "-o", default="-", help="Archivo de salida ('-' = stdout)")
    openapi.set_defaults(handler=_export_openapi)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    handler: Handler = args.handler
    try:
        sys.exit(asyncio.run(handler(args, get_settings())))
    except ConfigError as exc:
        sys.exit(_error(str(exc)))


if __name__ == "__main__":
    main()
