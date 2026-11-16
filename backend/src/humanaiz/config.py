"""Configuración de la aplicación, leída solo de variables de entorno."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Variables que cambiarían en silencio el destino o las credenciales de las
# llamadas a los proveedores de LLM, o que volcarían secretos TLS a disco. La
# clave siempre la aporta el usuario en cada petición: el servidor no debe
# tener ninguna, ni un proxy o una URL base alternativa.
FORBIDDEN_ENV_VARS: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_LOG",
    "OPENAI_ORG_ID",
    "OPENAI_PROJECT_ID",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_LOG",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GOOGLE_GENAI_USE_VERTEXAI",
    "GOOGLE_GEMINI_BASE_URL",
    "GOOGLE_VERTEX_BASE_URL",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "SSLKEYLOGFILE",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
)

_LOG_LEVELS_PRODUCCION = {"INFO", "WARNING", "ERROR", "CRITICAL"}


class ConfigError(RuntimeError):
    """La configuración impide arrancar de forma segura."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    environment: Literal["development", "test", "production"] = "development"
    public_origin: str = "http://localhost:5173"
    log_level: str = "INFO"
    tz_negocio: str = "America/Lima"
    enable_docs: bool = False

    # Datos del proyecto que se muestran en la interfaz y en los textos legales.
    concurso_nombre: str = Field(default="", max_length=120)
    contacto_proyecto: str = Field(default="", max_length=200)
    # Días que se conserva la bitácora de auditoría (contiene IPs).
    audit_retention_days: int = Field(default=30, ge=1, le=3650)

    database_url: str
    db_pool_size: int = Field(default=5, ge=1, le=50)

    jwt_secret: SecretStr
    access_token_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    session_idle_ttl_seconds: int = Field(default=28_800, ge=300)
    session_absolute_ttl_seconds: int = Field(default=604_800, ge=300)
    cookie_secure: bool = True

    storage_local_path: Path = Path("/data/uploads")
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    max_image_pixels: int = Field(default=40_000_000, ge=1_000_000)
    max_pdf_pages: int = Field(default=5, ge=1, le=20)
    page_max_side_px: int = Field(default=2400, ge=600, le=8000)
    normalize_timeout_seconds: int = Field(default=15, ge=1, le=120)
    normalize_max_concurrency: int = Field(default=2, ge=1, le=16)
    min_free_disk_mb: int = Field(default=500, ge=0)

    llm_enabled_providers: Annotated[tuple[str, ...], NoDecode] = (
        "anthropic",
        "openai",
        "gemini",
        "openrouter",
        "xai",
        "mistral",
        "groq",
    )
    llm_request_timeout_seconds: int = Field(default=90, ge=1, le=300)
    analysis_deadline_seconds: int = Field(default=100, ge=2, le=330)
    analysis_max_concurrency: int = Field(default=8, ge=1, le=64)
    analysis_max_per_descanso: int = Field(default=10, ge=1, le=100)

    rate_limit_storage_uri: str = "memory://"
    rate_limit_login: str = "5/minute"
    rate_limit_upload: str = "10/hour"
    rate_limit_analysis: str = "30/hour"
    rate_limit_modelos: str = "30/hour"
    rate_limit_general: str = "240/minute"

    # 0 desactiva la purga periódica dentro de la API (se puede lanzar con `humanaiz purge`).
    purge_interval_seconds: int = Field(default=900, ge=0)

    demo_mode: bool = False
    demo_ttl_hours: int = Field(default=24, ge=1, le=720)
    demo_session_ttl_seconds: int = Field(default=7200, ge=300)
    demo_max_descansos_per_visitor: int = Field(default=5, ge=1, le=100)
    demo_colaborador_dni: str = ""
    demo_colaborador_password: SecretStr = SecretStr("")
    demo_rrhh_dni: str = ""
    demo_rrhh_password: SecretStr = SecretStr("")

    @field_validator("llm_enabled_providers", mode="before")
    @classmethod
    def _split_providers(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(p.strip().lower() for p in value.split(",") if p.strip())
        return value

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        return value.upper()

    @field_validator("public_origin")
    @classmethod
    def _normalize_origin(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("PUBLIC_ORIGIN debe empezar por http:// o https://")
        return value

    @model_validator(mode="after")
    def _check_consistency(self) -> Settings:
        if len(self.jwt_secret.get_secret_value().encode()) < 32:
            raise ValueError("JWT_SECRET debe tener al menos 32 bytes aleatorios")
        if self.analysis_deadline_seconds <= self.llm_request_timeout_seconds:
            raise ValueError(
                "ANALYSIS_DEADLINE_SECONDS debe ser mayor que LLM_REQUEST_TIMEOUT_SECONDS"
            )
        if self.environment == "production":
            if self.log_level not in _LOG_LEVELS_PRODUCCION:
                raise ValueError("En producción LOG_LEVEL no puede ser DEBUG ni TRACE")
            if not self.cookie_secure:
                raise ValueError("En producción COOKIE_SECURE debe ser true")
            if not self.public_origin.startswith("https://"):
                raise ValueError("En producción PUBLIC_ORIGIN debe ser https://")
            if self.enable_docs:
                raise ValueError("En producción ENABLE_DOCS debe ser false")
        if self.demo_mode:
            faltan = [
                nombre
                for nombre, valor in (
                    ("DEMO_COLABORADOR_DNI", self.demo_colaborador_dni),
                    (
                        "DEMO_COLABORADOR_PASSWORD",
                        self.demo_colaborador_password.get_secret_value(),
                    ),
                    ("DEMO_RRHH_DNI", self.demo_rrhh_dni),
                    ("DEMO_RRHH_PASSWORD", self.demo_rrhh_password.get_secret_value()),
                )
                if not valor
            ]
            if faltan:
                raise ValueError("DEMO_MODE=true requiere: " + ", ".join(faltan))
        return self

    @property
    def session_cookie_name(self) -> str:
        # El prefijo __Host- exige Secure, así que solo se usa con HTTPS.
        return "__Host-hz_session" if self.cookie_secure else "hz_session"

    @property
    def visitor_cookie_name(self) -> str:
        return "__Host-hz_visitor" if self.cookie_secure else "hz_visitor"


def forbidden_env_present(environ: os._Environ[str] | dict[str, str] | None = None) -> list[str]:
    """Devuelve las variables prohibidas que están definidas (en cualquier caja)."""
    environ = os.environ if environ is None else environ
    definidas = {nombre.upper() for nombre, valor in environ.items() if valor}
    return [nombre for nombre in FORBIDDEN_ENV_VARS if nombre in definidas]


def enforce_boot_guard(settings: Settings) -> list[str]:
    """Impide arrancar en producción con variables que desvían o exponen claves.

    Fuera de producción devuelve la lista para que se registre como aviso: los
    adaptadores igual pasan siempre `api_key` y `base_url` explícitos.
    """
    presentes = forbidden_env_present()
    if presentes and settings.environment == "production":
        raise ConfigError(
            "Variables de entorno no permitidas en este servicio: "
            + ", ".join(presentes)
            + ". HumanAIz no usa claves de LLM del servidor: cada usuario aporta la suya "
            "por petición. Elimínalas del entorno y vuelve a arrancar."
        )
    return presentes


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
