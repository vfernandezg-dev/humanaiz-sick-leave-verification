"""Padrón de colaboradores (solo lectura, solo RRHH)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from sqlalchemy import ColumnElement, func, or_, select

from humanaiz.api.deps import SessionDep
from humanaiz.api.schemas import Colaborador, ColaboradorFacetas, Pagina
from humanaiz.models import Colaborador as ColaboradorModel
from humanaiz.security.deps import RRHHUser

router = APIRouter(prefix="/colaboradores", tags=["colaboradores"])

Texto = Annotated[str | None, Query(max_length=100)]


def _like(texto: str) -> str:
    escapado = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado}%"


@router.get("", response_model=Pagina[Colaborador])
async def listar_colaboradores(
    _: RRHHUser,
    session: SessionDep,
    q: Texto = None,
    categoria: Literal["A", "B", "C", "D"] | None = None,
    area_operacion: Texto = None,
    tipo_contrato: Texto = None,
    sexo: Literal["M", "F"] | None = None,
    activo: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Pagina[Colaborador]:
    condiciones: list[ColumnElement[bool]] = []
    if q and q.strip():
        patron = _like(q.strip())
        condiciones.append(
            or_(
                ColaboradorModel.dni.like(patron, escape="\\"),
                ColaboradorModel.nombres.ilike(patron, escape="\\"),
                ColaboradorModel.apellidos.ilike(patron, escape="\\"),
            )
        )
    if categoria:
        condiciones.append(ColaboradorModel.categoria == categoria)
    if area_operacion:
        condiciones.append(ColaboradorModel.area_operacion == area_operacion)
    if tipo_contrato:
        condiciones.append(ColaboradorModel.tipo_contrato == tipo_contrato)
    if sexo:
        condiciones.append(ColaboradorModel.sexo == sexo)
    if activo is not None:
        condiciones.append(ColaboradorModel.activo.is_(activo))

    total = await session.scalar(select(func.count(ColaboradorModel.id)).where(*condiciones)) or 0
    filas = (
        await session.scalars(
            select(ColaboradorModel)
            .where(*condiciones)
            .order_by(ColaboradorModel.apellidos, ColaboradorModel.nombres, ColaboradorModel.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return Pagina[Colaborador](
        items=[Colaborador.model_validate(f) for f in filas],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/facetas", response_model=ColaboradorFacetas)
async def facetas(_: RRHHUser, session: SessionDep) -> ColaboradorFacetas:
    """Valores distintos para poblar los filtros del listado."""

    async def distintos(columna) -> list[str]:  # type: ignore[no-untyped-def]
        return list((await session.scalars(select(columna).distinct().order_by(columna))).all())

    return ColaboradorFacetas(
        areas_operacion=await distintos(ColaboradorModel.area_operacion),
        tipos_contrato=await distintos(ColaboradorModel.tipo_contrato),
        sedes=await distintos(ColaboradorModel.sede),
    )
