"""Validaciones deterministas sobre lo que el modelo leyó del documento.

El modelo solo transcribe campos; el veredicto lo calcula este módulo, que es
código puro (sin red ni base de datos). Así el contenido de un documento no
puede producir un veredicto por sí mismo, las reglas se prueban con tablas de
casos, y una extracción guardada puede reevaluarse cuando cambien las reglas.

Estas reglas son una reconstrucción propia: revísalas con RRHH antes de darles
peso en decisiones reales. El resultado es siempre una sugerencia; decide una
persona.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta

from humanaiz.scanning.dates import parse_fecha
from humanaiz.scanning.names import nombre_coincide
from humanaiz.scanning.types import (
    ContextoValidacion,
    EstadoDocumento,
    Extraccion,
    Regla,
    ResultadoAnalisis,
    ResultadoRegla,
)

RULES_VERSION = "2026.11-1"

_TEXTO_MAX = 160
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]+")
_CONTINGENCIAS = (
    "enfermedad comun",
    "enfermedad profesional",
    "accidente comun",
    "accidente de trabajo",
    "accidente laboral",
    "maternidad",
    "pre natal",
    "prenatal",
    "post natal",
    "postnatal",
)


def _texto(valor: str | None) -> str | None:
    """Limpia un texto leído por el modelo: sin caracteres de control y acotado."""
    if valor is None:
        return None
    limpio = " ".join(_CONTROL.sub(" ", valor).split())
    return limpio[:_TEXTO_MAX] or None


def _digitos(valor: str | None) -> str:
    return re.sub(r"\D", "", valor or "")


def _dni(valor: str | None) -> str | None:
    digitos = _digitos(valor)
    # Algunos documentos añaden el dígito verificador: "12345678-9".
    if len(digitos) == 9:
        digitos = digitos[:8]
    return digitos if len(digitos) == 8 else None


def _sin_tildes(valor: str) -> str:
    plano = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z]+", " ", plano).split())


def _regla(
    codigo: str,
    *,
    critica: bool,
    ok: bool | None,
    mensaje_ok: str,
    mensaje_falla: str,
    mensaje_no_evaluada: str = "",
) -> Regla:
    if ok is None:
        return Regla(codigo, critica, "no_evaluada", mensaje_no_evaluada)
    resultado: ResultadoRegla = "ok" if ok else "falla"
    return Regla(codigo, critica, resultado, mensaje_ok if ok else mensaje_falla)


def _formato(fecha: date) -> str:
    return fecha.strftime("%d/%m/%Y")


def evaluate(extraccion: Extraccion, contexto: ContextoValidacion) -> ResultadoAnalisis:
    inicio = parse_fecha(extraccion.fecha_inicio_doc)
    fin = parse_fecha(extraccion.fecha_fin_doc)
    emision = parse_fecha(extraccion.fecha_emision_doc)
    dni_documento = _dni(extraccion.dni_en_documento)
    nombre_documento = _texto(extraccion.nombre_en_documento)
    citt = _texto(extraccion.citt)
    codigo_medico = _texto(extraccion.codigo_medico)
    contingencia = _texto(extraccion.contingencia)
    dias = extraccion.dias_documento if (extraccion.dias_documento or 0) > 0 else None
    fechas_completas = inicio is not None and fin is not None
    fechas_ordenadas = fechas_completas and fin >= inicio  # type: ignore[operator]
    dias_calculados = (fin - inicio).days + 1 if fechas_ordenadas else None  # type: ignore[operator]

    reglas: list[Regla] = [
        _regla(
            "es_certificado_medico",
            critica=True,
            ok=extraccion.es_certificado_medico,
            mensaje_ok="El documento es un certificado de descanso médico.",
            mensaje_falla="El documento no parece un certificado de descanso médico.",
        ),
        _regla(
            "documento_legible",
            critica=True,
            ok=extraccion.legible,
            mensaje_ok="El documento es legible.",
            mensaje_falla="El documento no se puede leer con claridad.",
        ),
        _regla(
            "dni_coincide",
            critica=True,
            ok=None if dni_documento is None else dni_documento == contexto.dni,
            mensaje_ok="El DNI del documento coincide con el del colaborador.",
            mensaje_falla="El DNI del documento no coincide con el del colaborador.",
            mensaje_no_evaluada="El documento no muestra un DNI legible.",
        ),
        _regla(
            "nombre_coincide",
            # Sin DNI en el documento, el nombre es la única prueba de identidad.
            critica=dni_documento is None,
            ok=(
                None
                if nombre_documento is None
                else nombre_coincide(nombre_documento, contexto.nombres, contexto.apellidos)
            ),
            mensaje_ok="El nombre del documento coincide con el del colaborador.",
            mensaje_falla="El nombre del documento no coincide con el del colaborador.",
            mensaje_no_evaluada="El documento no muestra un nombre legible.",
        ),
        _regla(
            "fechas_presentes",
            critica=True,
            ok=fechas_completas,
            mensaje_ok="El documento indica las fechas de inicio y fin.",
            mensaje_falla="No se pudieron leer las fechas de inicio y fin del descanso.",
        ),
        _regla(
            "fechas_coherentes",
            critica=True,
            ok=fechas_ordenadas if fechas_completas else None,
            mensaje_ok="La fecha de fin no es anterior a la de inicio.",
            mensaje_falla="La fecha de fin es anterior a la de inicio.",
            mensaje_no_evaluada="No se evaluó: faltan fechas.",
        ),
    ]

    if extraccion.tipo_documento == "citt":
        # Solo los CITT de EsSalud llevan número: un certificado particular
        # válido no lo tiene y no debe rechazarse por eso.
        reglas.append(
            _regla(
                "citt_presente",
                critica=True,
                ok=citt is not None,
                mensaje_ok="El CITT tiene número.",
                mensaje_falla="El documento es un CITT pero no se lee su número.",
            )
        )

    reglas.extend(
        [
            _regla(
                "dias_coinciden",
                critica=False,
                ok=None if dias is None or dias_calculados is None else dias == dias_calculados,
                mensaje_ok="Los días indicados coinciden con las fechas.",
                mensaje_falla=(
                    f"El documento indica {dias} día(s), pero entre las fechas hay "
                    f"{dias_calculados}."
                ),
                mensaje_no_evaluada="No se evaluó: faltan los días o las fechas.",
            ),
            _regla(
                "codigo_medico_presente",
                critica=False,
                ok=len(_digitos(codigo_medico)) >= 3,
                mensaje_ok="Figura el número de colegiatura del médico.",
                mensaje_falla="No se lee el número de colegiatura (CMP) del médico.",
            ),
            _regla(
                "contingencia_reconocida",
                critica=False,
                ok=(
                    None
                    if contingencia is None
                    else any(c in _sin_tildes(contingencia) for c in _CONTINGENCIAS)
                ),
                mensaje_ok="La contingencia indicada es de un tipo conocido.",
                mensaje_falla="La contingencia indicada no es de un tipo conocido.",
                mensaje_no_evaluada="El documento no indica la contingencia.",
            ),
            _regla(
                "duracion_razonable",
                critica=False,
                ok=None if dias_calculados is None else 1 <= dias_calculados <= contexto.max_dias,
                mensaje_ok="La duración está dentro de lo habitual.",
                mensaje_falla=(
                    f"El descanso dura {dias_calculados} días, más de los {contexto.max_dias} "
                    "habituales."
                ),
                mensaje_no_evaluada="No se evaluó: faltan fechas.",
            ),
            _regla(
                "vigencia",
                critica=False,
                ok=(
                    None
                    if not fechas_ordenadas
                    else (
                        inicio <= contexto.hoy + timedelta(days=contexto.max_dias_futuro)  # type: ignore[operator]
                        and fin >= contexto.hoy - timedelta(days=contexto.max_dias_antiguedad)  # type: ignore[operator]
                    )
                ),
                mensaje_ok="Las fechas son recientes.",
                mensaje_falla="Las fechas del descanso son muy antiguas o muy futuras.",
                mensaje_no_evaluada="No se evaluó: faltan fechas.",
            ),
            _regla(
                "sin_solapamiento",
                critica=False,
                ok=(
                    None
                    if not fechas_ordenadas
                    else not any(
                        inicio <= b and a <= fin  # type: ignore[operator]
                        for a, b in contexto.rangos_aprobados
                    )
                ),
                mensaje_ok="No se cruza con otros descansos aprobados.",
                mensaje_falla="Las fechas se cruzan con otro descanso ya aprobado.",
                mensaje_no_evaluada="No se evaluó: faltan fechas.",
            ),
            _regla(
                "documento_no_duplicado",
                critica=False,
                ok=not (contexto.archivo_duplicado or contexto.citt_duplicado),
                mensaje_ok="El documento no se había presentado antes.",
                mensaje_falla="Este documento (o su número de CITT) ya se presentó antes.",
            ),
        ]
    )

    criticas_fallidas = [r for r in reglas if r.critica and r.resultado == "falla"]
    criticas_sin_evaluar = [r for r in reglas if r.critica and r.resultado == "no_evaluada"]
    informativas_fallidas = [r for r in reglas if not r.critica and r.resultado == "falla"]

    estado: EstadoDocumento
    if criticas_fallidas:
        estado = "Rechazado"
        comentario = (
            f"Se detectaron {len(criticas_fallidas)} problema(s) que impiden validar el "
            "documento automáticamente."
        )
    elif criticas_sin_evaluar or informativas_fallidas:
        estado = "Observado"
        pendientes = len(criticas_sin_evaluar) + len(informativas_fallidas)
        comentario = (
            f"El documento parece válido, pero hay {pendientes} punto(s) que conviene revisar "
            "a mano."
        )
    else:
        estado = "Aprobado"
        comentario = "El documento supera todas las validaciones automáticas."

    return ResultadoAnalisis(
        estado_documento=estado,
        extraidos={
            "es_certificado_medico": extraccion.es_certificado_medico,
            "legible": extraccion.legible,
            "tipo_documento": extraccion.tipo_documento,
            "dni_en_documento": dni_documento or _texto(extraccion.dni_en_documento),
            "nombre_en_documento": nombre_documento,
            "citt": citt,
            "codigo_medico": codigo_medico,
            "contingencia": contingencia,
            "fecha_inicio_doc": inicio.isoformat() if inicio else None,
            "fecha_fin_doc": fin.isoformat() if fin else None,
            "fecha_emision_doc": emision.isoformat() if emision else None,
            "dias_documento": dias,
        },
        reglas=tuple(reglas),
        motivos_rechazo=tuple(r.mensaje for r in criticas_fallidas),
        comentario_general=comentario,
        fecha_inicio=inicio if fechas_ordenadas else None,
        fecha_fin=fin if fechas_ordenadas else None,
    )
