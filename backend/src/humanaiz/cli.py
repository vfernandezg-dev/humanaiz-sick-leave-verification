"""Comandos de administración: `humanaiz <comando>` o `python -m humanaiz.cli`."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Awaitable, Callable

from humanaiz.config import Settings, get_settings

Handler = Callable[[argparse.Namespace, Settings], Awaitable[int]]


async def _seed_demo(args: argparse.Namespace, settings: Settings) -> int:
    if not settings.demo_mode:
        if args.if_enabled:
            print("DEMO_MODE=false: no se siembra nada.")
            return 0
        print("DEMO_MODE no está activo.", file=sys.stderr)
        return 2
    print("La siembra de la demo llega con el esquema de usuarios.", file=sys.stderr)
    return 0


async def _export_openapi(args: argparse.Namespace, settings: Settings) -> int:
    from humanaiz.main import create_app

    schema = create_app(settings).openapi()
    texto = json.dumps(schema, ensure_ascii=False, indent=2)
    if args.output == "-":
        print(texto)
    else:
        with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(texto + "\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="humanaiz", description="Administración de HumanAIz")
    sub = parser.add_subparsers(dest="comando", required=True)

    seed = sub.add_parser("seed-demo", help="Siembra los usuarios y muestras del modo demo")
    seed.add_argument(
        "--if-enabled", action="store_true", help="No falla si DEMO_MODE está apagado"
    )
    seed.set_defaults(handler=_seed_demo)

    openapi = sub.add_parser("export-openapi", help="Escribe el esquema OpenAPI de la API")
    openapi.add_argument("--output", "-o", default="-", help="Archivo de salida ('-' = stdout)")
    openapi.set_defaults(handler=_export_openapi)

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    handler: Handler = args.handler
    sys.exit(asyncio.run(handler(args, get_settings())))


if __name__ == "__main__":
    main()
