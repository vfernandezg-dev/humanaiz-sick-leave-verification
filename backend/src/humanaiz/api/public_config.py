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
    ProyectoConfig,
)
from humanaiz.config import Settings
from humanaiz.legal import TERMINOS_VERSION
from humanaiz.scanning.catalog import enabled_providers
from humanaiz.scanning.sniff import DocumentKind

router = APIRouter(tags=["configuración"])

TIPOS_MIME_ACEPTADOS = tuple(kind.value for kind in DocumentKind)


def _demo(settings: Settings) -> DemoConfig:
    if not settings.demo_mode:
        return DemoConfig(
            habilitado=False, aviso=None, usuarios=[], retencion_horas=settings.demo_ttl_hours
        )
    return DemoConfig(
        habilitado=True,
        retencion_horas=settings.demo_ttl_hours,
        aviso=(
            "Demostración de un proyecto de concurso, sin uso real. No subas documentos "
            f"reales: lo que cargues se elimina automáticamente a las {settings.demo_ttl_hours} "
            "horas. Al analizar un documento se envía al proveedor de IA que elijas, usando tu "
            "propia clave."
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
        proyecto=ProyectoConfig(
            concurso=settings.concurso_nombre.strip() or None,
            contacto=settings.contacto_proyecto.strip() or None,
            version_terminos=TERMINOS_VERSION,
            retencion_registros_dias=settings.audit_retention_days,
        ),
        demo=_demo(settings),
        carga=CargaConfig(
            max_bytes=settings.max_upload_bytes,
            tipos_mime=list(TIPOS_MIME_ACEPTADOS),
            min_lado_px=settings.min_image_side_px,
            max_lado_px=settings.page_max_side_px,
        ),
        llm=LlmConfig(
            proveedores=[
                ProveedorLlm(
                    id=p.id,
                    nombre=p.nombre,
                    formato_clave=p.formato_clave,
                    prefijos_clave=list(p.prefijos_clave),
                    url_claves=p.url_claves,
                    max_imagenes=p.max_imagenes,
                    modelos=[
                        ModeloLlm(id=m.id, nombre=m.nombre, predeterminado=m.predeterminado)
                        for m in p.modelos
                    ],
                )
                for p in enabled_providers(settings.llm_enabled_providers)
            ]
        ),
    )
