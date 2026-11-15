from __future__ import annotations

import ast
import io
import time
from pathlib import Path

import pytest
from PIL import Image

import humanaiz.scanning as scanning_pkg
from humanaiz.scanning.errors import DocumentoInvalido
from humanaiz.scanning.preprocess import Limits, normalize
from humanaiz.scanning.sniff import DocumentKind, looks_like_heic, sniff
from tests import files

LIMITES = Limits(max_pixels=40_000_000, max_pdf_pages=5, page_max_side_px=2400, timeout_seconds=20)


def _abrir(pagina: bytes) -> Image.Image:
    imagen = Image.open(io.BytesIO(pagina))
    imagen.load()
    return imagen


@pytest.mark.parametrize(
    ("datos", "esperado"),
    [
        (files.jpeg_bytes(), DocumentKind.JPEG),
        (files.png_bytes(), DocumentKind.PNG),
        (files.webp_bytes(), DocumentKind.WEBP),
        (files.pdf_bytes(), DocumentKind.PDF),
        (files.EJECUTABLE, None),
        (files.HEIC, None),
        (b"", None),
        (b"<html>", None),
        # La firma debe estar al inicio: un PDF incrustado más adelante no cuenta.
        (b"basura" + files.pdf_bytes(), None),
    ],
)
def test_sniff_por_firma(datos: bytes, esperado: DocumentKind | None) -> None:
    assert sniff(datos[:16]) is esperado


def test_detecta_heic_para_dar_un_mensaje_util() -> None:
    assert looks_like_heic(files.HEIC[:16])
    assert not looks_like_heic(files.jpeg_bytes()[:16])


@pytest.mark.parametrize(
    ("datos", "kind"),
    [
        (files.jpeg_bytes(), DocumentKind.JPEG),
        (files.png_bytes(alfa=True), DocumentKind.PNG),
        (files.webp_bytes(), DocumentKind.WEBP),
    ],
)
async def test_imagenes_se_recodifican_a_jpeg(datos: bytes, kind: DocumentKind) -> None:
    documento = await normalize(datos, kind, LIMITES)
    assert len(documento.pages) == 1
    imagen = _abrir(documento.pages[0])
    assert imagen.format == "JPEG"
    assert imagen.mode == "RGB"
    assert imagen.size == (800, 600)


async def test_png_transparente_queda_sobre_fondo_blanco() -> None:
    documento = await normalize(files.png_bytes(alfa=True), DocumentKind.PNG, LIMITES)
    assert _abrir(documento.pages[0]).getpixel((400, 300)) >= (250, 250, 250)


async def test_foto_rotada_por_exif_sale_derecha_y_sin_metadatos() -> None:
    # Orientación 6: la cámara guardó la foto girada; hay que rotarla 90° al mostrarla.
    original = files.jpeg_bytes(800, 600, orientacion=6)
    assert b"FabricanteSecreto" in original
    documento = await normalize(original, DocumentKind.JPEG, LIMITES)
    imagen = _abrir(documento.pages[0])
    assert imagen.size == (600, 800)
    assert not imagen.getexif()
    assert b"FabricanteSecreto" not in documento.pages[0]
    # La marca roja de la esquina superior izquierda pasa a la superior derecha.
    r, g, b = imagen.getpixel((570, 30))
    assert r > 150 and g < 80 and b < 80


async def test_imagen_grande_se_reduce_al_lado_maximo() -> None:
    documento = await normalize(files.jpeg_bytes(5000, 3000), DocumentKind.JPEG, LIMITES)
    assert _abrir(documento.pages[0]).size == (2400, 1440)


async def test_contenido_agregado_al_final_no_pasa_a_la_pagina() -> None:
    poliglota = files.jpeg_bytes() + files.HTML_ADJUNTO
    documento = await normalize(poliglota, DocumentKind.JPEG, LIMITES)
    assert b"<script>" not in documento.pages[0]


async def test_pdf_se_rasteriza_por_pagina() -> None:
    documento = await normalize(files.pdf_bytes(3), DocumentKind.PDF, LIMITES)
    assert len(documento.pages) == 3
    for pagina in documento.pages:
        imagen = _abrir(pagina)
        assert imagen.format == "JPEG"
        assert max(imagen.size) == 2400


async def test_pdf_con_pagina_gigante_no_pide_un_mapa_de_bits_enorme() -> None:
    inicio = time.perf_counter()
    gigante = files.pdf_bytes(1, ancho_pt=14_400, alto_pt=14_400)
    documento = await normalize(gigante, DocumentKind.PDF, LIMITES)
    assert max(_abrir(documento.pages[0]).size) == 2400
    assert time.perf_counter() - inicio < LIMITES.timeout_seconds


@pytest.mark.parametrize(
    ("datos", "kind", "codigo"),
    [
        (files.png_bomba(), DocumentKind.PNG, "imagen_demasiado_grande"),
        (files.pdf_cifrado(), DocumentKind.PDF, "pdf_protegido"),
        (files.pdf_bytes(50), DocumentKind.PDF, "pdf_demasiadas_paginas"),
        (files.jpeg_bytes()[:400], DocumentKind.JPEG, "archivo_invalido"),
        (b"%PDF-1.7\nno es un pdf de verdad", DocumentKind.PDF, "archivo_invalido"),
        # Una firma JPEG no basta: el contenido tiene que decodificar como JPEG.
        (b"\xff\xd8\xff" + files.png_bytes()[3:], DocumentKind.JPEG, "archivo_invalido"),
        (files.jpeg_bytes(120, 90), DocumentKind.JPEG, "archivo_invalido"),
    ],
)
async def test_archivos_hostiles_o_danados_se_rechazan(
    datos: bytes, kind: DocumentKind, codigo: str
) -> None:
    inicio = time.perf_counter()
    with pytest.raises(DocumentoInvalido) as excinfo:
        await normalize(datos, kind, LIMITES)
    assert excinfo.value.code == codigo
    assert time.perf_counter() - inicio < LIMITES.timeout_seconds


async def test_el_proceso_hijo_se_corta_al_vencer_el_plazo(monkeypatch: pytest.MonkeyPatch) -> None:
    # Con un plazo imposible, el hijo se mata y la subida falla limpiamente.
    limites = Limits(timeout_seconds=0)  # type: ignore[arg-type]
    monkeypatch.setattr("humanaiz.scanning.preprocess.subprocess.run", _run_que_vence)
    with pytest.raises(DocumentoInvalido, match="tardó demasiado"):
        await normalize(files.jpeg_bytes(), DocumentKind.JPEG, limites)


def _run_que_vence(*args: object, **kwargs: object) -> None:
    import subprocess

    raise subprocess.TimeoutExpired(cmd="worker", timeout=0)


def test_el_motor_de_escaneo_no_depende_del_resto_de_la_aplicacion() -> None:
    """`scanning` debe poder extraerse a su propio servicio sin reescribirlo."""
    raiz = Path(scanning_pkg.__file__).parent
    intrusos: list[str] = []
    for archivo in raiz.rglob("*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            modulos: list[str] = []
            if isinstance(nodo, ast.Import):
                modulos = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
                modulos = [nodo.module]
            for modulo in modulos:
                if modulo.startswith("humanaiz") and not modulo.startswith("humanaiz.scanning"):
                    intrusos.append(f"{archivo.name}: {modulo}")
    assert intrusos == []
