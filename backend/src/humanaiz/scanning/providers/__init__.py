"""Registro de adaptadores de proveedores de IA, construido desde el catálogo."""

from __future__ import annotations

from humanaiz.scanning.catalog import PROVIDERS, ProviderInfo
from humanaiz.scanning.providers.anthropic_adapter import AnthropicAdapter
from humanaiz.scanning.providers.base import ProviderAdapter
from humanaiz.scanning.providers.compatible_adapter import CompatibleAdapter
from humanaiz.scanning.providers.gemini_adapter import GeminiAdapter
from humanaiz.scanning.providers.openai_adapter import OpenAIAdapter


def _adaptador(info: ProviderInfo) -> ProviderAdapter:
    if info.familia == "anthropic":
        return AnthropicAdapter()
    if info.familia == "openai":
        return OpenAIAdapter()
    if info.familia == "gemini":
        return GeminiAdapter()
    if info.base_url is None:
        raise ValueError(f"el proveedor compatible {info.id} no tiene base_url")
    return CompatibleAdapter(info.id, info.base_url, max_imagenes=info.max_imagenes)


REGISTRY: dict[str, ProviderAdapter] = {info.id: _adaptador(info) for info in PROVIDERS}


def get_adapter(provider_id: str) -> ProviderAdapter | None:
    return REGISTRY.get(provider_id)
