"""Alias de dependencias compartidas por los routers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from humanaiz.config import Settings
from humanaiz.db import Database, get_db, get_session
from humanaiz.security.ratelimit import RateLimiter, client_ip, get_limiter


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_client_ip(request: Request) -> str | None:
    """IP para auditoría: None cuando no se puede determinar."""
    ip = client_ip(request)
    return None if ip == "desconocida" else ip


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
DbDep = Annotated[Database, Depends(get_db)]
LimiterDep = Annotated[RateLimiter, Depends(get_limiter)]
ClientIp = Annotated[str | None, Depends(get_client_ip)]
