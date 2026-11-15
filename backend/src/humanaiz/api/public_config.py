"""Configuración pública que el SPA necesita antes de iniciar sesión."""

from __future__ import annotations

from fastapi import APIRouter

from humanaiz.api.deps import SettingsDep
from humanaiz.api.schemas import (
    CargaConfig,
    ConfigPublica,
    DemoConfig,
    DemoUsuario,
    LlmConfig,
    ModeloLlm,
    ProveedorLlm,
)
from humanaiz.config import Settings
from humanaiz.scanning.catalog import enabled_providers

router = APIRouter(tags=["configuración"])

TIPOS_MIME_ACEPTADOS = ("image/jpeg", "image/png", "image/webp", "application/pdf")


def _demo(settings: Settings) -> DemoConfig:
    if not settings.demo_mode:
        return DemoConfig(habilitado=False, aviso=None, usuarios=[])
    return DemoConfig(
        habilitado=True,
        aviso=(
            "Entorno de demostración. No subas documentos reales: lo que cargues se elimina "
            f"automáticamente a las {settings.demo_ttl_hours} horas. Al analizar un documento "
            "se envía al proveedor de IA que elijas, usando tu propia clave."
        ),
        # Credenciales públicas a propósito: son las cuentas de prueba.
        usuarios=[
            DemoUsuario(
                role="colaborador",
                dni=settings.demo_colaborador_dni,
                password=settings.demo_colaborador_password.get_secret_value(),
                etiqueta="Colaborador de prueba",
            ),
            DemoUsuario(
                role="analista_rrhh",
                dni=settings.demo_rrhh_dni,
                password=settings.demo_rrhh_password.get_secret_value(),
                etiqueta="Analista de RRHH de prueba",
            ),
        ],
    )


@router.get("/config", response_model=ConfigPublica)
async def public_config(settings: SettingsDep) -> ConfigPublica:
    return ConfigPublica(
        demo=_demo(settings),
        carga=CargaConfig(
            max_bytes=settings.max_upload_bytes,
            tipos_mime=list(TIPOS_MIME_ACEPTADOS),
            max_paginas_pdf=settings.max_pdf_pages,
        ),
        llm=LlmConfig(
            proveedores=[
                ProveedorLlm(
                    id=p.id,
                    nombre=p.nombre,
                    formato_clave=p.formato_clave,
                    modelos=[
                        ModeloLlm(id=m.id, nombre=m.nombre, predeterminado=m.predeterminado)
                        for m in p.modelos
                    ],
                )
                for p in enabled_providers(settings.llm_enabled_providers)
            ]
        ),
    )
