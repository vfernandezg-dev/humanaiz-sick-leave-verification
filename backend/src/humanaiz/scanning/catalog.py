"""Proveedores y modelos permitidos para el análisis.

La lista vive en código, no en variables de entorno: añadir o quitar un modelo
pasa por revisión. Los identificadores se tomaron de la documentación oficial
de cada proveedor (noviembre de 2026); al actualizarlos, comprueba que el
modelo acepte imágenes y salida estructurada.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelInfo:
    id: str
    nombre: str
    predeterminado: bool = False


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    id: str
    nombre: str
    modelos: tuple[ModelInfo, ...]
    # Texto de ayuda para el campo de la clave en la interfaz.
    formato_clave: str

    def modelo_predeterminado(self) -> str:
        return next(m.id for m in self.modelos if m.predeterminado)

    def permite(self, modelo: str) -> bool:
        return any(m.id == modelo for m in self.modelos)


PROVIDERS: tuple[ProviderInfo, ...] = (
    ProviderInfo(
        id="anthropic",
        nombre="Anthropic (Claude)",
        formato_clave="Empieza por sk-ant-",
        modelos=(
            ModelInfo("claude-opus-5-5", "Claude Opus 5.5", predeterminado=True),
            ModelInfo("claude-sonnet-5-5", "Claude Sonnet 5.5"),
            ModelInfo("claude-haiku-5-5", "Claude Haiku 5.5"),
        ),
    ),
    ProviderInfo(
        id="openai",
        nombre="OpenAI",
        formato_clave="Empieza por sk-",
        modelos=(
            ModelInfo("gpt-6.1-sol", "GPT-6.1 Sol", predeterminado=True),
            ModelInfo("gpt-6-astra", "GPT-6 Astra"),
            ModelInfo("gpt-6.1-terra", "GPT-6.1 Terra"),
            ModelInfo("gpt-6-luna", "GPT-6 Luna"),
        ),
    ),
    ProviderInfo(
        id="gemini",
        nombre="Google Gemini",
        formato_clave="Empieza por AIza",
        modelos=(
            ModelInfo("gemini-3.8-flash", "Gemini 3.8 Flash", predeterminado=True),
            ModelInfo("gemini-3.6-flash", "Gemini 3.6 Flash"),
            ModelInfo("gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite"),
        ),
    ),
)

_BY_ID = {p.id: p for p in PROVIDERS}


def get_provider(provider_id: str) -> ProviderInfo | None:
    return _BY_ID.get(provider_id)


def enabled_providers(enabled: tuple[str, ...]) -> tuple[ProviderInfo, ...]:
    return tuple(p for p in PROVIDERS if p.id in enabled)
