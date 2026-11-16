"""Certificados médicos de ejemplo, generados para la demostración.

Reproducen la estructura habitual de un certificado de descanso médico en Perú
(datos del paciente, diagnóstico CIE-10, días y fechas, firma y sello con CMP)
para que la lectura con IA se pueda probar con algo realista. Son siempre
ficticios: entidad inventada, sin logos oficiales y con una marca de agua
"MUESTRA · SIN VALIDEZ" que cruza todo el documento.
"""

from __future__ import annotations

import hashlib
import io
import math
from dataclasses import dataclass, replace
from datetime import date, timedelta
from functools import cache
from importlib import resources
from typing import Literal

from PIL import Image, ImageDraw, ImageFont

TipoCertificado = Literal["particular", "citt"]
Variante = Literal["valido", "observado", "otra-persona", "citt"]

VARIANTES: tuple[Variante, ...] = ("valido", "observado", "otra-persona", "citt")
PIE_POR_DEFECTO = (
    "Documento de demostración generado por HumanAIz. Datos ficticios, sin validez médica ni legal."
)

ANCHO, ALTO = 1240, 1754  # A4 a 150 ppp
MARGEN = 96
TINTA = (24, 30, 42)
GRIS = (98, 106, 120)
LINEA = (210, 214, 222)
ACENTO = (15, 118, 110)
AZUL_FIRMA = (28, 58, 140)

_MESES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
_NUMEROS = (
    "",
    "UNO",
    "DOS",
    "TRES",
    "CUATRO",
    "CINCO",
    "SEIS",
    "SIETE",
    "OCHO",
    "NUEVE",
    "DIEZ",
    "ONCE",
    "DOCE",
    "TRECE",
    "CATORCE",
    "QUINCE",
    "DIECISÉIS",
    "DIECISIETE",
    "DIECIOCHO",
    "DIECINUEVE",
    "VEINTE",
    "VEINTIUNO",
    "VEINTIDÓS",
    "VEINTITRÉS",
    "VEINTICUATRO",
    "VEINTICINCO",
    "VEINTISÉIS",
    "VEINTISIETE",
    "VEINTIOCHO",
    "VEINTINUEVE",
    "TREINTA",
)


@dataclass(frozen=True, slots=True)
class DatosCertificado:
    tipo: TipoCertificado
    paciente: str  # "APELLIDOS, NOMBRES"
    dni: str
    edad: int
    diagnostico_cie10: str
    diagnostico: str
    contingencia: str
    fecha_inicio: date
    fecha_fin: date
    dias: int  # los que declara el documento (puede no cuadrar con las fechas)
    fecha_emision: date
    numero: str
    medico: str
    especialidad: str
    cmp: str | None
    rne: str | None
    establecimiento: str = "POLICLÍNICO HORIZONTE"
    direccion: str = "Av. Los Ejemplos 123, Lima · Tel. (01) 000-0000"


# ---------- fuentes ----------


@cache
def _fuente(nombre: str, tamano: int) -> ImageFont.FreeTypeFont:
    ruta = resources.files("humanaiz.assets").joinpath("fuentes", nombre)
    with resources.as_file(ruta) as archivo:
        return ImageFont.truetype(str(archivo), tamano)


def _sans(tamano: int) -> ImageFont.FreeTypeFont:
    return _fuente("DejaVuSans.ttf", tamano)


def _sans_negrita(tamano: int) -> ImageFont.FreeTypeFont:
    return _fuente("DejaVuSans-Bold.ttf", tamano)


def _serif_negrita(tamano: int) -> ImageFont.FreeTypeFont:
    return _fuente("DejaVuSerif-Bold.ttf", tamano)


def _serif(tamano: int) -> ImageFont.FreeTypeFont:
    return _fuente("DejaVuSerif.ttf", tamano)


# ---------- utilidades ----------


def fecha_larga(fecha: date) -> str:
    return f"{fecha.day} de {_MESES[fecha.month - 1]} de {fecha.year}"


def numero_en_letras(numero: int) -> str:
    return _NUMEROS[numero] if 0 < numero < len(_NUMEROS) else str(numero)


def _semilla(texto: str) -> int:
    return int(hashlib.sha256(texto.encode()).hexdigest()[:8], 16)


def _firma(dibujo: ImageDraw.ImageDraw, x: int, y: int, ancho: int, semilla: int) -> None:
    """Rúbrica estilizada (bucles como de letra cursiva), distinta y estable por médico."""
    fase = (semilla % 360) * math.pi / 180
    vueltas = 5 + semilla % 3
    puntos = []
    for i in range(480):
        t = i / 479
        # Velocidad y tamaño variables: los bucles no son todos iguales.
        angulo = 2 * math.pi * vueltas * (t + 0.07 * math.sin(t * math.pi * 3 + fase)) + fase
        radio_x = 7 + 9 * abs(math.sin(t * math.pi * 2.2 + fase))
        alto = 12 + 30 * abs(math.sin(t * math.pi * 2.6 + fase * 1.3))
        px = x + t * ancho - radio_x * math.sin(angulo)
        py = y - 22 * t + alto * math.cos(angulo) - 8 * math.sin(t * math.pi)
        puntos.append((px, py))
    dibujo.line(puntos, fill=AZUL_FIRMA, width=3, joint="curve")
    # Trazo final que subraya la rúbrica.
    dibujo.line(
        [(x + ancho * 0.05, y + 40), (x + ancho * 0.55, y + 30), (x + ancho * 1.02, y + 4)],
        fill=AZUL_FIRMA,
        width=3,
        joint="curve",
    )


def _iniciales(medico: str) -> str:
    """'Dr. Julio César Paredes Luna' -> 'DR. J. C. PAREDES L.'"""
    partes = medico.replace("Dr.", "").replace("Dra.", "").split()
    if len(partes) < 3:
        return medico.upper()
    nombres, paterno, materno = partes[:-2], partes[-2], partes[-1]
    titulo = "DRA." if medico.startswith("Dra.") else "DR."
    return " ".join([titulo, *(n[0] + "." for n in nombres), paterno, materno[0] + "."]).upper()


def _sello(texto_superior: str, lineas: list[str], diametro: int = 280) -> Image.Image:
    """Sello circular en tinta azul, levemente girado."""
    capa = Image.new("RGBA", (diametro, diametro), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    tinta = (*AZUL_FIRMA, 175)
    d.ellipse((4, 4, diametro - 4, diametro - 4), outline=tinta, width=6)
    d.ellipse((24, 24, diametro - 24, diametro - 24), outline=tinta, width=2)
    centro = diametro / 2
    d.text((centro, 76), texto_superior, font=_sans_negrita(13), fill=tinta, anchor="mm")
    d.line((60, 92, diametro - 60, 92), fill=tinta, width=2)
    for i, linea in enumerate(lineas):
        d.text((centro, 124 + i * 32), linea, font=_sans_negrita(17), fill=tinta, anchor="mm")
    return capa.rotate(-9, resample=Image.Resampling.BICUBIC, expand=False)


def _marca_de_agua(imagen: Image.Image) -> Image.Image:
    capa = Image.new("RGBA", imagen.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    texto = "MUESTRA · SIN VALIDEZ"
    fuente = _sans_negrita(86)
    for y in (430, 980, 1530):
        d.text((ANCHO / 2, y), texto, font=fuente, fill=(200, 40, 40, 38), anchor="mm")
    capa = capa.rotate(28, resample=Image.Resampling.BICUBIC, center=(ANCHO / 2, ALTO / 2))
    return Image.alpha_composite(imagen.convert("RGBA"), capa)


class _Lienzo:
    def __init__(self) -> None:
        self.imagen = Image.new("RGB", (ANCHO, ALTO), (255, 255, 255))
        self.d = ImageDraw.Draw(self.imagen)
        self.y = MARGEN

    def texto(self, x: float, texto: str, fuente: ImageFont.FreeTypeFont, color=TINTA, anchor="la"):  # type: ignore[no-untyped-def]
        self.d.text((x, self.y), texto, font=fuente, fill=color, anchor=anchor)

    def linea(self, grosor: int = 1, color=LINEA) -> None:  # type: ignore[no-untyped-def]
        self.d.line((MARGEN, self.y, ANCHO - MARGEN, self.y), fill=color, width=grosor)

    def fila(self, etiqueta: str, valor: str, *, alto: int = 58) -> None:
        izquierda, divisor, derecha = MARGEN, MARGEN + 330, ANCHO - MARGEN
        self.d.rectangle((izquierda, self.y, derecha, self.y + alto), outline=LINEA, width=2)
        self.d.rectangle((izquierda, self.y, divisor, self.y + alto), fill=(245, 247, 250))
        self.d.line((divisor, self.y, divisor, self.y + alto), fill=LINEA, width=2)
        medio = self.y + alto / 2
        self.d.text((izquierda + 20, medio), etiqueta, font=_sans(21), fill=GRIS, anchor="lm")
        disponible = derecha - divisor - 40
        tamano = 23
        while tamano > 15 and _sans_negrita(tamano).getlength(valor) > disponible:
            tamano -= 1
        self.d.text(
            (divisor + 20, medio), valor, font=_sans_negrita(tamano), fill=TINTA, anchor="lm"
        )
        self.y += alto


def _encabezado(lienzo: _Lienzo, datos: DatosCertificado) -> None:
    d = lienzo.d
    # Isotipo: cruz blanca sobre cuadrado redondeado (genérico, sin marcas reales).
    x0, y0 = MARGEN, MARGEN
    d.rounded_rectangle((x0, y0, x0 + 92, y0 + 92), radius=18, fill=ACENTO)
    d.rectangle((x0 + 36, y0 + 18, x0 + 56, y0 + 74), fill="white")
    d.rectangle((x0 + 18, y0 + 36, x0 + 74, y0 + 56), fill="white")
    d.text((x0 + 118, y0 + 6), datos.establecimiento, font=_sans_negrita(32), fill=TINTA)
    d.text(
        (x0 + 118, y0 + 50),
        "Entidad ficticia para demostración · RUC 00000000000",
        font=_sans(19),
        fill=GRIS,
    )
    d.text((x0 + 118, y0 + 76), datos.direccion, font=_sans(19), fill=GRIS)
    etiqueta = "N.º de CITT" if datos.tipo == "citt" else "N.º de certificado"
    d.text((ANCHO - MARGEN, y0 + 14), etiqueta, font=_sans(18), fill=GRIS, anchor="ra")
    d.text((ANCHO - MARGEN, y0 + 40), datos.numero, font=_sans_negrita(24), fill=TINTA, anchor="ra")
    lienzo.y = y0 + 126
    lienzo.linea(grosor=4, color=ACENTO)


def _cuerpo_particular(lienzo: _Lienzo, datos: DatosCertificado) -> None:
    lienzo.y += 62
    lienzo.texto(ANCHO / 2, "CERTIFICADO MÉDICO", _serif_negrita(46), anchor="mt")
    lienzo.y += 66
    lienzo.texto(ANCHO / 2, "DE DESCANSO MÉDICO", _sans(22), GRIS, anchor="mt")
    lienzo.y += 76
    lienzo.texto(MARGEN, "El médico que suscribe certifica que el(la) paciente:", _serif(24))
    lienzo.y += 52
    lienzo.fila("Apellidos y nombres", datos.paciente)
    lienzo.fila("DNI", datos.dni)
    lienzo.fila("Edad", f"{datos.edad} años")
    lienzo.y += 36
    lienzo.texto(
        MARGEN, "Ha sido atendido(a) en este establecimiento con el diagnóstico:", _serif(24)
    )
    lienzo.y += 48
    lienzo.fila("Diagnóstico (CIE-10)", f"{datos.diagnostico_cie10} · {datos.diagnostico}")
    lienzo.fila("Contingencia", datos.contingencia)
    lienzo.y += 40
    _bloque_descanso(lienzo, datos)
    lienzo.y += 46
    lienzo.texto(
        MARGEN,
        "Se expide el presente certificado a solicitud del interesado, para los fines que",
        _serif(22),
        GRIS,
    )
    lienzo.y += 34
    lienzo.texto(MARGEN, "estime conveniente.", _serif(22), GRIS)


def _cuerpo_citt(lienzo: _Lienzo, datos: DatosCertificado) -> None:
    lienzo.y += 58
    lienzo.texto(ANCHO / 2, "CERTIFICADO DE INCAPACIDAD", _serif_negrita(40), anchor="mt")
    lienzo.y += 54
    lienzo.texto(ANCHO / 2, "TEMPORAL PARA EL TRABAJO", _serif_negrita(40), anchor="mt")
    lienzo.y += 64
    lienzo.texto(ANCHO / 2, "FORMATO ILUSTRATIVO · NO OFICIAL", _sans(20), GRIS, anchor="mt")
    lienzo.y += 72
    lienzo.fila("Asegurado(a)", datos.paciente)
    lienzo.fila("DNI", datos.dni)
    lienzo.fila("Centro asistencial", datos.establecimiento)
    lienzo.fila("Contingencia", datos.contingencia)
    lienzo.fila("Diagnóstico (CIE-10)", datos.diagnostico_cie10)
    lienzo.fila("Fecha de otorgamiento", datos.fecha_emision.strftime("%d/%m/%Y"))
    lienzo.y += 44
    _bloque_descanso(lienzo, datos)


def _bloque_descanso(lienzo: _Lienzo, datos: DatosCertificado) -> None:
    d = lienzo.d
    alto = 150
    d.rounded_rectangle(
        (MARGEN, lienzo.y, ANCHO - MARGEN, lienzo.y + alto),
        radius=14,
        fill=(240, 248, 247),
        outline=(176, 216, 210),
        width=2,
    )
    titulo = (
        "Días de incapacidad otorgados" if datos.tipo == "citt" else "Se otorga descanso médico por"
    )
    d.text((MARGEN + 30, lienzo.y + 26), titulo, font=_sans(22), fill=GRIS)
    d.text(
        (MARGEN + 30, lienzo.y + 60),
        f"{numero_en_letras(datos.dias)} ({datos.dias}) {'DÍA' if datos.dias == 1 else 'DÍAS'}",
        font=_sans_negrita(38),
        fill=TINTA,
    )
    columna = ANCHO - MARGEN - 470
    d.text((columna, lienzo.y + 30), "Desde", font=_sans(20), fill=GRIS)
    d.text((columna + 235, lienzo.y + 30), "Hasta", font=_sans(20), fill=GRIS)
    d.text(
        (columna, lienzo.y + 62),
        datos.fecha_inicio.strftime("%d/%m/%Y"),
        font=_sans_negrita(30),
        fill=TINTA,
    )
    d.text(
        (columna + 235, lienzo.y + 62),
        datos.fecha_fin.strftime("%d/%m/%Y"),
        font=_sans_negrita(30),
        fill=TINTA,
    )
    lienzo.y += alto


def _firma_y_sello(lienzo: _Lienzo, datos: DatosCertificado) -> None:
    d = lienzo.d
    lienzo.y = max(lienzo.y + 60, 1230)
    d.text(
        (ANCHO - MARGEN, lienzo.y),
        f"Lima, {fecha_larga(datos.fecha_emision)}",
        font=_serif(23),
        fill=TINTA,
        anchor="ra",
    )
    base = 1470
    centro = ANCHO / 2 + 170
    _firma(d, int(centro - 190), base - 70, 380, _semilla(datos.medico))
    d.line((centro - 230, base, centro + 230, base), fill=TINTA, width=2)
    d.text((centro, base + 16), datos.medico, font=_sans_negrita(23), fill=TINTA, anchor="mt")
    d.text(
        (centro, base + 50),
        f"Médico cirujano · {datos.especialidad}",
        font=_sans(20),
        fill=GRIS,
        anchor="mt",
    )
    registro = " · ".join(
        p
        for p in (
            f"CMP {datos.cmp}" if datos.cmp else None,
            f"RNE {datos.rne}" if datos.rne else None,
        )
        if p
    )
    if registro:
        d.text((centro, base + 80), registro, font=_sans(20), fill=GRIS, anchor="mt")
    lineas_sello = [_iniciales(datos.medico), "MÉDICO CIRUJANO"]
    if datos.cmp:
        lineas_sello.append(f"CMP {datos.cmp}")
    sello = _sello(datos.establecimiento[:24], lineas_sello)
    lienzo.imagen.paste(sello, (MARGEN + 30, base - 200), sello)


def _pie(lienzo: _Lienzo, pie: str) -> None:
    d = lienzo.d
    y = ALTO - MARGEN - 20
    d.line((MARGEN, y - 22, ANCHO - MARGEN, y - 22), fill=LINEA, width=2)
    d.text((ANCHO / 2, y), pie, font=_sans(17), fill=GRIS, anchor="mm")


def renderizar(datos: DatosCertificado, *, pie: str | None = None) -> Image.Image:
    lienzo = _Lienzo()
    _encabezado(lienzo, datos)
    if datos.tipo == "citt":
        _cuerpo_citt(lienzo, datos)
    else:
        _cuerpo_particular(lienzo, datos)
    _firma_y_sello(lienzo, datos)
    _pie(
        lienzo,
        pie or PIE_POR_DEFECTO,
    )
    return _marca_de_agua(lienzo.imagen).convert("RGB")


def exportar(imagen: Image.Image, formato: Literal["jpg", "png"]) -> bytes:
    buffer = io.BytesIO()
    if formato == "png":
        imagen.save(buffer, "PNG", optimize=True)
    else:
        imagen.save(buffer, "JPEG", quality=88, optimize=True)
    return buffer.getvalue()


# ---------- variantes para probar la lectura con IA ----------


def base_para(*, nombres: str, apellidos: str, dni: str, hoy: date) -> DatosCertificado:
    """Certificado coherente con la ficha del colaborador: la lectura no encuentra problemas."""
    inicio = hoy - timedelta(days=2)
    return DatosCertificado(
        tipo="particular",
        paciente=f"{apellidos}, {nombres}".upper(),
        dni=dni,
        edad=35,
        diagnostico_cie10="J06.9",
        diagnostico="Infección aguda de vías respiratorias superiores",
        contingencia="Enfermedad común",
        fecha_inicio=inicio,
        fecha_fin=hoy,
        dias=3,
        fecha_emision=inicio,
        numero=f"CM-{hoy.year}-{_semilla(dni + str(hoy)) % 1_000_000:06d}",
        medico="Dr. Julio César Paredes Luna",
        especialidad="Medicina interna",
        cmp="054321",
        rne="027384",
    )


def variante(nombre: Variante, base: DatosCertificado) -> DatosCertificado:
    if nombre == "observado":
        # Declara más días de los que hay entre las fechas y no muestra el CMP.
        return replace(base, dias=base.dias + 2, cmp=None, rne=None)
    if nombre == "otra-persona":
        return replace(base, paciente="PAREDES LEÓN, MIGUEL ÁNGEL", dni="70000099", edad=41)
    if nombre == "citt":
        return replace(
            base,
            tipo="citt",
            numero=(
                f"A-104-{_semilla(base.dni) % 100_000_000:08d}-{base.fecha_emision.year % 100:02d}"
            ),
        )
    return base


def extraccion_de(datos: DatosCertificado) -> dict[str, object]:
    """Lo que una lectura correcta extraería de este certificado (para las muestras)."""
    return {
        "es_certificado_medico": True,
        "legible": True,
        "tipo_documento": "citt" if datos.tipo == "citt" else "certificado_particular",
        "dni_en_documento": datos.dni,
        "nombre_en_documento": datos.paciente,
        "citt": datos.numero if datos.tipo == "citt" else None,
        "codigo_medico": f"CMP {datos.cmp}" if datos.cmp else None,
        "contingencia": datos.contingencia,
        "fecha_inicio_doc": datos.fecha_inicio.isoformat(),
        "fecha_fin_doc": datos.fecha_fin.isoformat(),
        "fecha_emision_doc": datos.fecha_emision.isoformat(),
        "dias_documento": datos.dias,
    }
