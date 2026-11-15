"""Proceso hijo que decodifica un archivo no confiable y lo re-codifica a JPEG.

Es el único módulo que importa Pillow y pypdfium2. Corre aislado y con límites
porque parsea bytes controlados por quien sube el archivo: si un PDF o una
imagen maliciosa cuelga o revienta el decodificador, muere este proceso y no la
API. Tampoco comparte memoria con la petición de análisis, que es la única que
maneja la clave de IA del usuario.

Uso: python -m humanaiz.scanning._normalize_worker <kind> <entrada> <dir_salida>
         <max_pixeles> <max_paginas> <max_lado_px> <segundos_cpu>
Escribe en <dir_salida>: page-N.jpg y result.json.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

JPEG_QUALITY = 88
_MEMORIA_MAXIMA = 2 * 1024**3


class Rechazo(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _limitar_recursos(segundos_cpu: int) -> None:
    try:
        import resource
    except ImportError:  # Windows (solo desarrollo): sin límites del SO.
        return
    resource.setrlimit(resource.RLIMIT_CPU, (segundos_cpu, segundos_cpu + 1))
    resource.setrlimit(resource.RLIMIT_AS, (_MEMORIA_MAXIMA, _MEMORIA_MAXIMA))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _guardar_jpeg(imagen, destino: Path, max_lado: int) -> None:  # type: ignore[no-untyped-def]
    from PIL import Image

    if imagen.mode in ("RGBA", "LA", "PA") or "transparency" in imagen.info:
        # Fondo blanco: un certificado con transparencia saldría negro en JPEG.
        rgba = imagen.convert("RGBA")
        fondo = Image.new("RGB", rgba.size, (255, 255, 255))
        fondo.paste(rgba, mask=rgba.getchannel("A"))
        imagen = fondo
    elif imagen.mode != "RGB":
        imagen = imagen.convert("RGB")
    imagen.thumbnail((max_lado, max_lado), Image.Resampling.LANCZOS)
    # Sin `exif=`: el archivo resultante no conserva metadatos (GPS, dispositivo).
    imagen.save(destino, "JPEG", quality=JPEG_QUALITY, optimize=True)


def _normalizar_imagen(
    formato: str, entrada: Path, salida: Path, max_pixeles: int, max_lado: int
) -> int:
    from PIL import Image, ImageOps, UnidentifiedImageError

    Image.MAX_IMAGE_PIXELS = max_pixeles
    warnings.simplefilter("error", Image.DecompressionBombWarning)
    try:
        # `formats` impide que Pillow pruebe otros decodificadores con el archivo.
        with Image.open(entrada, formats=[formato]) as imagen:
            ancho, alto = imagen.size
            if ancho * alto > max_pixeles:
                raise Rechazo(
                    "imagen_demasiado_grande",
                    "La imagen tiene demasiados píxeles. Súbela con menor resolución.",
                )
            if ancho < 200 or alto < 200:
                raise Rechazo(
                    "archivo_invalido", "La imagen es demasiado pequeña para leer un documento."
                )
            imagen.seek(0)  # solo el primer fotograma de un archivo animado
            imagen.load()
            # Antes de quitar el EXIF: las fotos de móvil guardan ahí la rotación.
            derecha = ImageOps.exif_transpose(imagen) or imagen
            _guardar_jpeg(derecha, salida / "page-1.jpg", max_lado)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise Rechazo(
            "imagen_demasiado_grande",
            "La imagen tiene demasiados píxeles. Súbela con menor resolución.",
        ) from None
    except Rechazo:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, EOFError):
        raise Rechazo(
            "archivo_invalido", "El archivo está dañado o no es una imagen válida."
        ) from None
    return 1


def _normalizar_pdf(entrada: Path, salida: Path, max_paginas: int, max_lado: int) -> int:
    import pypdfium2 as pdfium

    try:
        documento = pdfium.PdfDocument(entrada)
    except pdfium.PdfiumError as exc:
        if "password" in str(exc).lower():
            raise Rechazo(
                "pdf_protegido",
                "El PDF está protegido con contraseña. Sube una copia sin proteger.",
            ) from None
        raise Rechazo("archivo_invalido", "El archivo está dañado o no es un PDF válido.") from None
    try:
        paginas = len(documento)
        if paginas < 1:
            raise Rechazo("archivo_invalido", "El PDF no tiene páginas.")
        if paginas > max_paginas:
            raise Rechazo(
                "pdf_demasiadas_paginas",
                f"El PDF tiene {paginas} páginas; el máximo es {max_paginas}.",
            )
        for indice in range(paginas):
            pagina = documento[indice]
            ancho_pt, alto_pt = pagina.get_size()
            if ancho_pt <= 0 or alto_pt <= 0:
                raise Rechazo("archivo_invalido", "El PDF tiene una página sin dimensiones.")
            # Se renderiza a un tamaño en píxeles fijo, no a un DPI: una página
            # declarada como gigantesca no puede pedir un mapa de bits enorme.
            escala = max_lado / max(ancho_pt, alto_pt)
            imagen = pagina.render(scale=escala, may_draw_forms=True).to_pil()
            _guardar_jpeg(imagen, salida / f"page-{indice + 1}.jpg", max_lado)
            pagina.close()
    except pdfium.PdfiumError:
        raise Rechazo("archivo_invalido", "No se pudo leer el contenido del PDF.") from None
    finally:
        documento.close()
    return paginas


def main(argv: list[str]) -> int:
    kind, entrada, salida = argv[0], Path(argv[1]), Path(argv[2])
    max_pixeles, max_paginas, max_lado, segundos_cpu = (int(v) for v in argv[3:7])
    _limitar_recursos(segundos_cpu)
    try:
        if kind == "application/pdf":
            paginas = _normalizar_pdf(entrada, salida, max_paginas, max_lado)
        else:
            formato = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}[kind]
            paginas = _normalizar_imagen(formato, entrada, salida, max_pixeles, max_lado)
        resultado: dict[str, object] = {"ok": True, "paginas": paginas}
    except Rechazo as exc:
        resultado = {"ok": False, "code": exc.code, "message": exc.message}
    except MemoryError:
        resultado = {
            "ok": False,
            "code": "archivo_invalido",
            "message": "El archivo es demasiado complejo para procesarlo.",
        }
    (salida / "result.json").write_text(json.dumps(resultado), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
