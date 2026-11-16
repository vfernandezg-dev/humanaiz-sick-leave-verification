"""Generadores de archivos de prueba: imágenes válidas, dañadas y hostiles, y
formatos que no se admiten."""

from __future__ import annotations

import io
import struct
import zlib

from PIL import Image, ImageDraw


def _lienzo(ancho: int, alto: int, texto: str = "CERTIFICADO DE PRUEBA") -> Image.Image:
    imagen = Image.new("RGB", (ancho, alto), (250, 250, 245))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rectangle((10, 10, ancho - 10, alto - 10), outline=(40, 40, 40), width=3)
    dibujo.text((30, 30), texto, fill=(10, 10, 10))
    # Marca en la esquina superior izquierda: permite comprobar la orientación.
    dibujo.rectangle((0, 0, 60, 60), fill=(200, 0, 0))
    return imagen


def jpeg_bytes(ancho: int = 800, alto: int = 600, *, orientacion: int | None = None) -> bytes:
    imagen = _lienzo(ancho, alto)
    buffer = io.BytesIO()
    if orientacion is None:
        imagen.save(buffer, "JPEG", quality=90)
    else:
        exif = Image.Exif()
        exif[0x0112] = orientacion  # Orientation
        exif[0x010F] = "FabricanteSecreto"  # Make
        exif[0x8825] = {1: "S", 2: (12.0, 2.0, 47.0), 3: "W", 4: (77.0, 1.0, 41.0)}  # GPS
        imagen.save(buffer, "JPEG", quality=90, exif=exif)
    return buffer.getvalue()


def png_bytes(ancho: int = 800, alto: int = 600, *, alfa: bool = False) -> bytes:
    imagen = _lienzo(ancho, alto)
    if alfa:
        imagen = imagen.convert("RGBA")
        imagen.putalpha(0)
    buffer = io.BytesIO()
    imagen.save(buffer, "PNG")
    return buffer.getvalue()


def webp_bytes(ancho: int = 800, alto: int = 600) -> bytes:
    buffer = io.BytesIO()
    _lienzo(ancho, alto).save(buffer, "WEBP", quality=90)
    return buffer.getvalue()


def png_bomba(ancho: int = 30_000, alto: int = 30_000) -> bytes:
    """PNG diminuto en disco que declara 900 megapíxeles en su cabecera."""
    original = png_bytes(64, 64)
    firma, resto = original[:8], original[8:]
    longitud = struct.unpack(">I", resto[:4])[0]
    ihdr = bytearray(resto[8 : 8 + longitud])
    ihdr[0:4] = struct.pack(">I", ancho)
    ihdr[4:8] = struct.pack(">I", alto)
    crc = zlib.crc32(b"IHDR" + bytes(ihdr)) & 0xFFFFFFFF
    nuevo_ihdr = struct.pack(">I", longitud) + b"IHDR" + bytes(ihdr) + struct.pack(">I", crc)
    return firma + nuevo_ihdr + resto[12 + longitud :]


def pdf_bytes() -> bytes:
    """Un PDF válido con una página que contiene la imagen de un certificado."""
    buffer = io.BytesIO()
    _lienzo(800, 600).save(buffer, "PDF")
    return buffer.getvalue()


def gif_bytes() -> bytes:
    buffer = io.BytesIO()
    _lienzo(800, 600).save(buffer, "GIF")
    return buffer.getvalue()


EJECUTABLE = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff" + b"\x00" * 200
HEIC = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic" + b"\x00" * 200
HTML_ADJUNTO = b"<html><script>alert('xss')</script></html>"
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
ZIP = b"PK\x03\x04\x14\x00\x00\x00\x08\x00" + b"\x00" * 200
