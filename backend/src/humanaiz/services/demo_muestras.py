"""Descansos de muestra para la demo, con análisis precalculados.

Sirven para que quien entra sin una clave de IA vea igualmente cómo luce un
resultado en sus tres estados. Los "certificados" son imágenes sintéticas
generadas aquí, con datos ficticios y una marca visible de que no son válidos.
Los análisis salen del mismo `evaluate()` que usa la aplicación: no hay
resultados escritos a mano.
"""

from __future__ import annotations

import hashlib
import io
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.ext.asyncio import AsyncSession

from humanaiz.models import AnalisisDescanso, Colaborador, DescansoMedico, User
from humanaiz.scanning.preprocess import Limits, normalize
from humanaiz.scanning.prompt import PROMPT_VERSION
from humanaiz.scanning.rules import RULES_VERSION, evaluate
from humanaiz.scanning.sniff import DocumentKind
from humanaiz.scanning.types import ContextoValidacion, Extraccion
from humanaiz.storage.base import ORIGINAL, Storage, page_name

_NAMESPACE = uuid.UUID("6f3f1c1e-5a7b-4a0e-9d3a-0b6c2f0d7e11")
_ANCHO, _ALTO = 1240, 1754  # A4 a 150 ppp
_TINTA = (25, 30, 45)
_GRIS = (110, 115, 130)


@dataclass(frozen=True, slots=True)
class _Muestra:
    clave: str
    titulo: str
    emisor: str
    extraccion: dict[str, Any]
    estado: str
    comentario_rrhh: str | None


def _fuente(tamano: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=tamano)
    except TypeError:  # Pillow sin FreeType: fuente fija
        return ImageFont.load_default()


def _formato(fecha_iso: str | None) -> str:
    return date.fromisoformat(fecha_iso).strftime("%d/%m/%Y") if fecha_iso else "-"


def _ascii(texto: object) -> str:
    """La fuente integrada de Pillow no trae tildes ni rayas: se dibuja sin ellas."""
    plano = unicodedata.normalize("NFKD", str(texto).replace("—", "-").replace("°", "o"))
    return plano.encode("ascii", "ignore").decode()


def render_certificado(muestra: _Muestra) -> bytes:
    """Dibuja un certificado ficticio y lo devuelve como PNG."""
    e = muestra.extraccion
    imagen = Image.new("RGB", (_ANCHO, _ALTO), (252, 252, 248))
    d = ImageDraw.Draw(imagen)
    d.rectangle((40, 40, _ANCHO - 40, _ALTO - 40), outline=_TINTA, width=3)
    d.text((90, 90), _ascii(muestra.emisor), font=_fuente(34), fill=_GRIS)
    d.text((90, 150), _ascii(muestra.titulo), font=_fuente(46), fill=_TINTA)
    d.line((90, 225, _ANCHO - 90, 225), fill=_TINTA, width=2)

    campos = [
        ("Numero de certificado", e.get("citt") or "(no indica)"),
        ("Paciente", e.get("nombre_en_documento") or "-"),
        ("DNI", e.get("dni_en_documento") or "-"),
        ("Contingencia", e.get("contingencia") or "-"),
        ("Inicio del descanso", _formato(e.get("fecha_inicio_doc"))),
        ("Fin del descanso", _formato(e.get("fecha_fin_doc"))),
        ("Días de descanso", str(e.get("dias_documento") or "-")),
        ("Fecha de emisión", _formato(e.get("fecha_emision_doc"))),
        ("Médico tratante (CMP)", e.get("codigo_medico") or "(ilegible)"),
    ]
    y = 290
    for etiqueta, valor in campos:
        d.text((90, y), _ascii(etiqueta).upper(), font=_fuente(22), fill=_GRIS)
        d.text((90, y + 32), _ascii(valor), font=_fuente(36), fill=_TINTA)
        y += 120

    d.line((760, _ALTO - 330, _ANCHO - 110, _ALTO - 330), fill=_TINTA, width=2)
    d.text((800, _ALTO - 315), "Firma y sello del medico", font=_fuente(22), fill=_GRIS)
    # Marca inequívoca: esto no es un documento real.
    d.rectangle((90, _ALTO - 220, _ANCHO - 90, _ALTO - 110), outline=(170, 30, 30), width=4)
    d.text(
        (125, _ALTO - 195),
        "DOCUMENTO DE MUESTRA - DATOS FICTICIOS, SIN VALIDEZ",
        font=_fuente(34),
        fill=(170, 30, 30),
    )
    buffer = io.BytesIO()
    imagen.save(buffer, "PNG", optimize=True)
    return buffer.getvalue()


def _muestras(hoy: date, dni_colaborador: str) -> list[tuple[_Muestra, str]]:
    """Devuelve (muestra, DNI del colaborador al que pertenece)."""

    def iso(dias_atras: int) -> str:
        return (hoy - timedelta(days=dias_atras)).isoformat()

    return [
        (
            _Muestra(
                clave="aprobado",
                titulo="Certificado de Incapacidad Temporal",
                emisor="SEGURO SOCIAL — MUESTRA",
                extraccion={
                    "es_certificado_medico": True,
                    "legible": True,
                    "tipo_documento": "citt",
                    "dni_en_documento": dni_colaborador,
                    "nombre_en_documento": "RAMIREZ SOTO CARLOS DANIEL",
                    "citt": "A-000-00012345-00",
                    "codigo_medico": "CMP 000123",
                    "contingencia": "Enfermedad común",
                    "fecha_inicio_doc": iso(12),
                    "fecha_fin_doc": iso(10),
                    "fecha_emision_doc": iso(12),
                    "dias_documento": 3,
                },
                estado="Aprobado",
                comentario_rrhh="Conforme. Documento verificado.",
            ),
            dni_colaborador,
        ),
        (
            _Muestra(
                clave="observado",
                titulo="Certificado Médico de Descanso",
                emisor="CLÍNICA DE EJEMPLO — MUESTRA",
                extraccion={
                    "es_certificado_medico": True,
                    "legible": True,
                    "tipo_documento": "certificado_particular",
                    "dni_en_documento": "70000011",
                    "nombre_en_documento": "QUISPE MAMANI ROSA ELENA",
                    "citt": None,
                    "codigo_medico": None,
                    "contingencia": "Enfermedad común",
                    "fecha_inicio_doc": iso(3),
                    "fecha_fin_doc": iso(1),
                    "fecha_emision_doc": iso(3),
                    # El documento dice 5 días, pero entre las fechas hay 3.
                    "dias_documento": 5,
                },
                estado="Pendiente",
                comentario_rrhh=None,
            ),
            "70000011",
        ),
        (
            _Muestra(
                clave="rechazado",
                titulo="Certificado de Incapacidad Temporal",
                emisor="SEGURO SOCIAL — MUESTRA",
                extraccion={
                    "es_certificado_medico": True,
                    "legible": True,
                    "tipo_documento": "citt",
                    # DNI y nombre de otra persona: no corresponde al colaborador.
                    "dni_en_documento": "70000099",
                    "nombre_en_documento": "PAREDES LEON MIGUEL ANGEL",
                    "citt": "A-000-00067890-00",
                    "codigo_medico": "CMP 000456",
                    "contingencia": "Enfermedad común",
                    "fecha_inicio_doc": iso(6),
                    "fecha_fin_doc": iso(5),
                    "fecha_emision_doc": iso(6),
                    "dias_documento": 2,
                },
                estado="Rechazado",
                comentario_rrhh="El certificado está emitido a nombre de otra persona.",
            ),
            "70000012",
        ),
    ]


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
    """Crea las muestras que falten. Devuelve cuántas creó."""
    creadas = 0
    for muestra, dni in _muestras(hoy, colaborador_user.dni):
        descanso_id = uuid.uuid5(_NAMESPACE, f"muestra-{muestra.clave}")
        if await session.get(DescansoMedico, descanso_id) is not None:
            continue
        colaborador = colaboradores[dni]
        original = render_certificado(muestra)
        documento = await normalize(original, DocumentKind.PNG, limits)
        prefix = storage.new_prefix()
        await storage.put(prefix, ORIGINAL, original)
        for numero, pagina in enumerate(documento.pages, start=1):
            await storage.put(prefix, page_name(numero), pagina)

        extraccion = Extraccion(**muestra.extraccion)
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
                created_by=colaborador_user.id if dni == colaborador_user.dni else rrhh_user.id,
                estado=muestra.estado,
                sede=colaborador.sede,
                fecha_inicio=resultado.fecha_inicio if muestra.estado == "Aprobado" else None,
                fecha_fin=resultado.fecha_fin if muestra.estado == "Aprobado" else None,
                comentario_rrhh=muestra.comentario_rrhh,
                decidido_por=rrhh_user.id if decidido else None,
                decidido_at=ahora if decidido else None,
                archivo_key=prefix,
                archivo_mime=DocumentKind.PNG.value,
                archivo_size=len(original),
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
