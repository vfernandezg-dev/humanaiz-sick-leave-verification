"""Proceso hijo que decodifica una imagen no confiable y la re-codifica a JPEG.

Es el único módulo que importa Pillow para leer lo que sube el usuario. Corre
aislado y con límites porque parsea bytes controlados por quien sube el archivo:
si una imagen maliciosa cuelga o revienta el decodificador, muere este proceso y
no la API. Tampoco comparte memoria con la petición de análisis, que es la única
que maneja la clave de IA del usuario.

La salida es siempre un JPEG nuevo, generado a partir de los píxeles: lo que el
archivo original llevara además de la imagen (metadatos, GPS, datos añadidos al
final, contenido de otro formato camuflado) no llega a guardarse.

Uso: python -m humanaiz.scanning._normalize_worker <kind> <entrada> <dir_salida>
         <max_pixeles> <min_lado_px> <max_lado_px> <segundos_cpu>
Escribe en <dir_salida>: page-1.jpg y result.json.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

JPEG_QUALITY = 88
_MEMORIA_MAXIMA = 2 * 1024**3
_FORMATOS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}


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
    # Sin `exif=` ni `icc_profile=`: el archivo resultante no conserva metadatos.
    imagen.save(destino, "JPEG", quality=JPEG_QUALITY, optimize=True)


def normalizar(
    formato: str, entrada: Path, salida: Path, max_pixeles: int, min_lado: int, max_lado: int
) -> None:
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
            if min(ancho, alto) < min_lado:
                raise Rechazo(
                    "imagen_demasiado_pequena",
                    "La imagen es demasiado pequeña para leer un documento.",
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


def main(argv: list[str]) -> int:
    kind, entrada, salida = argv[0], Path(argv[1]), Path(argv[2])
    max_pixeles, min_lado, max_lado, segundos_cpu = (int(v) for v in argv[3:7])
    _limitar_recursos(segundos_cpu)
    try:
        formato = _FORMATOS.get(kind)
        if formato is None:
            raise Rechazo("tipo_no_soportado", "Formato no admitido.")
        normalizar(formato, entrada, salida, max_pixeles, min_lado, max_lado)
        resultado: dict[str, object] = {"ok": True, "paginas": 1}
    except Rechazo as exc:
        resultado = {"ok": False, "code": exc.code, "message": exc.message}
    except MemoryError:
        resultado = {
            "ok": False,
            "code": "archivo_invalido",
            "message": "La imagen es demasiado compleja para procesarla.",
        }
    (salida / "result.json").write_text(json.dumps(resultado), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
