"""Descansos de muestra para la demo, con documentos y lecturas precalculadas.

Sirven para que quien entra sin una clave de IA vea igualmente cómo luce un
resultado en sus tres estados. Los certificados los genera `certificados.py`
(ficticios y con marca de agua), y las lecturas salen del mismo `evaluate()`
que usa la aplicación a partir de los datos dibujados en cada documento: no hay
resultados escritos a mano.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from humanaiz.models import AnalisisDescanso, Colaborador, DescansoMedico, User
from humanaiz.scanning.preprocess import Limits, normalize
from humanaiz.scanning.prompt import PROMPT_VERSION
from humanaiz.scanning.rules import RULES_VERSION, evaluate
from humanaiz.scanning.sniff import DocumentKind
from humanaiz.scanning.types import ContextoValidacion, Extraccion
from humanaiz.services import certificados
from humanaiz.storage.base import Storage, page_name

# Cambiar la versión regenera las muestras en el siguiente despliegue.
_VERSION_MUESTRAS = "v3"
_NAMESPACE = uuid.UUID("6f3f1c1e-5a7b-4a0e-9d3a-0b6c2f0d7e11")


@dataclass(frozen=True, slots=True)
class _Muestra:
    clave: str
    dni: str
    dias_atras: int
    variante: certificados.Variante
    estado: str
    comentario_rrhh: str | None


def _muestras(dni_colaborador_demo: str) -> list[_Muestra]:
    return [
        _Muestra(
            clave="aprobado",
            dni=dni_colaborador_demo,
            dias_atras=10,
            variante="citt",
            estado="Aprobado",
            comentario_rrhh="Conforme. Documento verificado.",
        ),
        # Declara más días de los que hay entre las fechas y no muestra el CMP.
        _Muestra(
            clave="observado",
            dni="70000011",
            dias_atras=1,
            variante="observado",
            estado="Pendiente",
            comentario_rrhh=None,
        ),
        # El certificado está a nombre de otra persona.
        _Muestra(
            clave="rechazado",
            dni="70000012",
            dias_atras=5,
            variante="otra-persona",
            estado="Rechazado",
            comentario_rrhh="El certificado está emitido a nombre de otra persona.",
        ),
    ]


def _id_muestra(clave: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, f"muestra-{_VERSION_MUESTRAS}-{clave}")


async def sembrar(
    session: AsyncSession,
    storage: Storage,
    *,
    hoy: date,
    limits: Limits,
    colaboradores: dict[str, Colaborador],
    colaborador_user: User,
    rrhh_user: User,
) -> int:
    """Crea las muestras que falten y retira las de versiones anteriores. Devuelve cuántas creó."""
    muestras = _muestras(colaborador_user.dni)
    vigentes = {_id_muestra(m.clave) for m in muestras}
    antiguas = (
        await session.scalars(
            select(DescansoMedico).where(
                DescansoMedico.es_muestra.is_(True), DescansoMedico.id.not_in(vigentes)
            )
        )
    ).all()
    for antigua in antiguas:
        await storage.delete_prefix(antigua.archivo_key)
        await session.delete(antigua)
    await session.flush()

    creadas = 0
    for muestra in muestras:
        descanso_id = _id_muestra(muestra.clave)
        if await session.get(DescansoMedico, descanso_id) is not None:
            continue
        colaborador = colaboradores[muestra.dni]
        datos = certificados.variante(
            muestra.variante,
            certificados.base_para(
                nombres=colaborador.nombres,
                apellidos=colaborador.apellidos,
                dni=colaborador.dni,
                hoy=hoy - timedelta(days=muestra.dias_atras),
            ),
        )
        original = certificados.exportar(certificados.renderizar(datos), "jpg")
        documento = await normalize(original, DocumentKind.JPEG, limits)
        prefix = storage.new_prefix()
        for numero, pagina in enumerate(documento.pages, start=1):
            await storage.put(prefix, page_name(numero), pagina)

        extraccion = Extraccion(**certificados.extraccion_de(datos))
        resultado = evaluate(
            extraccion,
            ContextoValidacion(
                dni=colaborador.dni,
                nombres=colaborador.nombres,
                apellidos=colaborador.apellidos,
                hoy=hoy,
            ),
        )
        decidido = muestra.estado != "Pendiente"
        ahora = datetime.now(UTC)
        session.add(
            DescansoMedico(
                id=descanso_id,
                colaborador_id=colaborador.id,
                created_by=(
                    colaborador_user.id if muestra.dni == colaborador_user.dni else rrhh_user.id
                ),
                estado=muestra.estado,
                sede=colaborador.sede,
                fecha_inicio=resultado.fecha_inicio if muestra.estado == "Aprobado" else None,
                fecha_fin=resultado.fecha_fin if muestra.estado == "Aprobado" else None,
                comentario_rrhh=muestra.comentario_rrhh,
                decidido_por=rrhh_user.id if decidido else None,
                decidido_at=ahora if decidido else None,
                archivo_key=prefix,
                archivo_mime=DocumentKind.JPEG.value,
                archivo_size=sum(len(p) for p in documento.pages),
                archivo_sha256=hashlib.sha256(original).digest(),
                paginas=len(documento.pages),
                es_muestra=True,
            )
        )
        await session.flush()
        session.add(
            AnalisisDescanso(
                descanso_id=descanso_id,
                solicitado_por=rrhh_user.id,
                proveedor="muestra",
                modelo="análisis precalculado",
                estado="completado",
                extraccion=extraccion.model_dump(),
                resultado=resultado.to_dict(),
                estado_documento=resultado.estado_documento,
                version_prompt=PROMPT_VERSION,
                version_reglas=RULES_VERSION,
                finished_at=ahora,
            )
        )
        creadas += 1
    return creadas
