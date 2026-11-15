"""Registro de adaptadores de proveedores de IA."""

from __future__ import annotations

from humanaiz.scanning.providers.anthropic_adapter import AnthropicAdapter
from humanaiz.scanning.providers.base import ProviderAdapter
from humanaiz.scanning.providers.gemini_adapter import GeminiAdapter
from humanaiz.scanning.providers.openai_adapter import OpenAIAdapter

REGISTRY: dict[str, ProviderAdapter] = {
    adapter.id: adapter for adapter in (AnthropicAdapter(), OpenAIAdapter(), GeminiAdapter())
}


def get_adapter(provider_id: str) -> ProviderAdapter | None:
    return REGISTRY.get(provider_id)
