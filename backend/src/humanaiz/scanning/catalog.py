"""Proveedores de IA admitidos y reglas para elegir modelo.

Cada proveedor tiene una URL base fija en código: el usuario aporta su clave y
elige modelo, pero nunca el servidor al que se envía (evita SSRF y que alguien
apunte a un servidor propio que devuelva lecturas falsas).

Los modelos "sugeridos" son una comodidad para la interfaz. Se acepta cualquier
modelo que cumpla el patrón del proveedor: así funcionan modelos nuevos sin
tocar el código, y el endpoint /llm/modelos lista los que tiene cada clave.
Identificadores verificados en la documentación oficial (noviembre de 2026).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

Familia = Literal["anthropic", "openai", "gemini", "compatible"]

_PATRON_GENERICO = r"[A-Za-z0-9][A-Za-z0-9._:/@-]{0,119}"


@dataclass(frozen=True, slots=True)
class ModelInfo:
    id: str
    nombre: str
    predeterminado: bool = False


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    id: str
    nombre: str
    familia: Familia
    # Texto de ayuda para el campo de la clave en la interfaz.
    formato_clave: str
    # Prefijos con los que la interfaz reconoce el proveedor al pegar la clave.
    prefijos_clave: tuple[str, ...]
    # Dónde crea el usuario su clave (se muestra como enlace).
    url_claves: str
    modelos: tuple[ModelInfo, ...] = ()
    # Solo para la familia "compatible" (API de OpenAI en otro servidor).
    base_url: str | None = None
    # Algunos modelos aceptan pocas imágenes por petición.
    max_imagenes: int = 20
    patron_modelo: str = _PATRON_GENERICO
    _regex: re.Pattern[str] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_regex", re.compile(self.patron_modelo))

    def modelo_predeterminado(self) -> str | None:
        return next((m.id for m in self.modelos if m.predeterminado), None)

    def normalizar_modelo(self, modelo: str) -> str:
        modelo = modelo.strip()
        if self.familia == "gemini":
            modelo = modelo.removeprefix("models/")
        return modelo

    def permite(self, modelo: str) -> bool:
        """El modelo tiene una forma válida para este proveedor.

        No garantiza que exista ni que la clave tenga acceso: eso lo responde
        el proveedor. Solo impide valores que no son un identificador.
        """
        return ".." not in modelo and self._regex.fullmatch(modelo) is not None


PROVIDERS: tuple[ProviderInfo, ...] = (
    ProviderInfo(
        id="anthropic",
        nombre="Anthropic (Claude)",
        familia="anthropic",
        formato_clave="Empieza por sk-ant-",
        prefijos_clave=("sk-ant-",),
        url_claves="https://console.anthropic.com/settings/keys",
        patron_modelo=r"claude-[a-z0-9.-]{1,80}",
        modelos=(
            ModelInfo("claude-opus-5-5", "Claude Opus 5.5", predeterminado=True),
            ModelInfo("claude-sonnet-5-5", "Claude Sonnet 5.5"),
            ModelInfo("claude-haiku-5-5", "Claude Haiku 5.5"),
        ),
    ),
    ProviderInfo(
        id="openai",
        nombre="OpenAI",
        familia="openai",
        formato_clave="Empieza por sk-",
        prefijos_clave=("sk-",),
        url_claves="https://platform.openai.com/api-keys",
        patron_modelo=r"[a-z0-9][a-z0-9._:-]{0,119}",
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
        familia="gemini",
        formato_clave="Empieza por AIza",
        prefijos_clave=("AIza",),
        url_claves="https://aistudio.google.com/apikey",
        # Sin "/": el modelo forma parte de la ruta de la URL de Google.
        patron_modelo=r"(models/)?[a-z0-9][a-z0-9.-]{1,80}",
        modelos=(
            ModelInfo("gemini-3.8-flash", "Gemini 3.8 Flash", predeterminado=True),
            ModelInfo("gemini-3.6-flash", "Gemini 3.6 Flash"),
            ModelInfo("gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite"),
        ),
    ),
    ProviderInfo(
        id="openrouter",
        nombre="OpenRouter (muchos modelos con una clave)",
        familia="compatible",
        formato_clave="Empieza por sk-or-",
        prefijos_clave=("sk-or-",),
        url_claves="https://openrouter.ai/keys",
        base_url="https://openrouter.ai/api/v1",
        # "autor/modelo", p. ej. anthropic/claude-sonnet-5.5 o google/gemini-3.8-flash:free
        patron_modelo=r"~?[a-z0-9][a-z0-9._-]{0,60}/[A-Za-z0-9._:-]{1,100}",
    ),
    ProviderInfo(
        id="xai",
        nombre="xAI (Grok)",
        familia="compatible",
        formato_clave="Empieza por xai-",
        prefijos_clave=("xai-",),
        url_claves="https://console.x.ai",
        base_url="https://api.x.ai/v1",
        modelos=(ModelInfo("grok-4.7", "Grok 4.7"),),
    ),
    ProviderInfo(
        id="mistral",
        nombre="Mistral AI",
        familia="compatible",
        formato_clave="Clave de 32 caracteres de console.mistral.ai",
        prefijos_clave=(),
        url_claves="https://console.mistral.ai/api-keys",
        base_url="https://api.mistral.ai/v1",
    ),
    ProviderInfo(
        id="groq",
        nombre="Groq",
        familia="compatible",
        formato_clave="Empieza por gsk_",
        prefijos_clave=("gsk_",),
        url_claves="https://console.groq.com/keys",
        base_url="https://api.groq.com/openai/v1",
        max_imagenes=3,
        modelos=(ModelInfo("qwen/qwen3.8-27b", "Qwen 3.8 27B (visión)", predeterminado=True),),
    ),
)

_BY_ID = {p.id: p for p in PROVIDERS}


def get_provider(provider_id: str) -> ProviderInfo | None:
    return _BY_ID.get(provider_id)


def enabled_providers(enabled: tuple[str, ...]) -> tuple[ProviderInfo, ...]:
    return tuple(p for p in PROVIDERS if p.id in enabled)
