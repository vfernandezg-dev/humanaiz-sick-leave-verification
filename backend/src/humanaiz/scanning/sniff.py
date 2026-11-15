"""Detección del tipo de archivo por sus primeros bytes.

Nunca se confía en el Content-Type ni en el nombre que envía el cliente. La
firma solo decide a qué decodificador se entrega el archivo: la validación real
es que ese decodificador lo abra completo (ver `preprocess`).
"""

from __future__ import annotations

from enum import StrEnum


class DocumentKind(StrEnum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    WEBP = "image/webp"
    PDF = "application/pdf"

    @property
    def extension(self) -> str:
        return {
            DocumentKind.JPEG: "jpg",
            DocumentKind.PNG: "png",
            DocumentKind.WEBP: "webp",
            DocumentKind.PDF: "pdf",
        }[self]


def sniff(head: bytes) -> DocumentKind | None:
    """Devuelve el tipo según la firma en el desplazamiento 0, o None."""
    if head.startswith(b"\xff\xd8\xff"):
        return DocumentKind.JPEG
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return DocumentKind.PNG
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return DocumentKind.WEBP
    if head.startswith(b"%PDF-"):
        return DocumentKind.PDF
    return None


def looks_like_heic(head: bytes) -> bool:
    """Las fotos de iPhone en HEIC no se aceptan: sirve para dar un mensaje útil."""
    return (
        len(head) >= 12
        and head[4:8] == b"ftyp"
        and head[8:12]
        in {
            b"heic",
            b"heix",
            b"hevc",
            b"mif1",
            b"msf1",
            b"heif",
        }
    )
