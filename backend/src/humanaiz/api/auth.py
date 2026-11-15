"""Sesión: login, renovación, cierre y usuario actual."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from humanaiz.api.deps import ClientIp, LimiterDep, SessionDep, SettingsDep
from humanaiz.api.schemas import LoginRequest, Sesion, Usuario, UsuarioColaborador
from humanaiz.config import Settings
from humanaiz.errors import AppError, error_body
from humanaiz.security.deps import CurrentUser, Principal, principal_from_user, require_same_origin
from humanaiz.security.ratelimit import client_ip, scale_limit
from humanaiz.services import auth as auth_service
from humanaiz.services.auth import SesionIniciada

router = APIRouter(prefix="/auth", tags=["sesión"])

# El tope por IP es más holgado que el de IP + DNI: muchas personas pueden
# compartir una IP (redes móviles con CGNAT, oficinas).
_FACTOR_LIMITE_IP = 4


def usuario_from_principal(principal: Principal) -> Usuario:
    colaborador = None
    if principal.colaborador_id is not None:
        colaborador = UsuarioColaborador(
            id=principal.colaborador_id,
            sede=principal.colaborador_sede,
            area_operacion=principal.colaborador_area,
        )
    return Usuario(
        id=principal.id,
        dni=principal.dni,
        nombres=principal.nombres,
        apellidos=principal.apellidos,
        role=principal.role,  # type: ignore[arg-type]
        is_demo=principal.is_demo,
        colaborador=colaborador,
    )


def _sesion(result: SesionIniciada, settings: Settings) -> Sesion:
    principal = principal_from_user(
        result.user, session_id=result.session_id, visitor_id=result.visitor_id
    )
    return Sesion(
        access_token=result.access_token,
        expires_in=settings.access_token_ttl_seconds,
        usuario=usuario_from_principal(principal),
    )


def _set_cookie(
    response: Response, settings: Settings, name: str, value: str, max_age: int
) -> None:
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )


@router.post("/login", response_model=Sesion, dependencies=[Depends(require_same_origin)])
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    limiter: LimiterDep,
    ip: ClientIp,
) -> Sesion:
    bucket = client_ip(request)
    await limiter.check(
        scale_limit(settings.rate_limit_login, _FACTOR_LIMITE_IP), "login-ip", bucket
    )
    await limiter.check(settings.rate_limit_login, "login", bucket, payload.dni)

    result = await auth_service.login(
        session,
        settings,
        dni=payload.dni,
        password=payload.password,
        ip=ip,
        user_agent=request.headers.get("user-agent"),
        visitor_cookie=request.cookies.get(settings.visitor_cookie_name),
    )
    if result.session_token is None:  # login siempre emite un token de sesión
        raise RuntimeError("login sin token de sesión")
    _set_cookie(
        response,
        settings,
        settings.session_cookie_name,
        result.session_token,
        result.session_max_age,
    )
    if result.visitor_id is not None:
        _set_cookie(
            response,
            settings,
            settings.visitor_cookie_name,
            str(result.visitor_id),
            settings.demo_ttl_hours * 3600,
        )
    return _sesion(result, settings)


@router.post("/refresh", response_model=Sesion, dependencies=[Depends(require_same_origin)])
async def refresh(
    request: Request, session: SessionDep, settings: SettingsDep
) -> Response | Sesion:
    try:
        result = await auth_service.refresh(
            session, settings, session_token=request.cookies.get(settings.session_cookie_name)
        )
    except AppError as exc:
        # La cookie ya no sirve: se borra para que el navegador deje de enviarla.
        failed = JSONResponse(error_body(exc.code, exc.message), status_code=exc.status_code)
        _clear_session_cookie(failed, settings)
        return failed
    return _sesion(result, settings)


@router.post("/logout", status_code=204, dependencies=[Depends(require_same_origin)])
async def logout(
    request: Request, session: SessionDep, settings: SettingsDep, ip: ClientIp
) -> Response:
    await auth_service.logout(
        session, session_token=request.cookies.get(settings.session_cookie_name), ip=ip
    )
    response = Response(status_code=204)
    # La cookie de visitante de la demo se conserva a propósito.
    _clear_session_cookie(response, settings)
    return response


@router.get("/me", response_model=Usuario)
async def me(principal: CurrentUser) -> Usuario:
    return usuario_from_principal(principal)
