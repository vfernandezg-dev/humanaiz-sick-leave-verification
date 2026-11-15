"""Errores del motor de escaneo. No dependen del resto de la aplicación."""

from __future__ import annotations


class ScanningError(Exception):
    """Base de los errores del motor. `code` es estable y apto para la API."""

    code = "error_escaneo"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class DocumentoInvalido(ScanningError):
    """El archivo no se puede aceptar: tipo, tamaño o contenido."""

    code = "archivo_invalido"


class TipoNoSoportado(DocumentoInvalido):
    code = "tipo_no_soportado"


class ProviderError(ScanningError):
    """Fallo al llamar al proveedor de IA. Nunca incluye la clave ni la petición."""

    code = "llm_error"
    retry_after: int | None = None

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        retry_after: int | None = None,
        request_id: str | None = None,
        status: int | None = None,
    ) -> None:
        super().__init__(message, code=code)
        self.retry_after = retry_after
        self.request_id = request_id
        self.status = status


class ClaveInvalida(ProviderError):
    code = "llm_clave_invalida"


class SinAccesoModelo(ProviderError):
    code = "llm_sin_acceso_modelo"


class SinSaldo(ProviderError):
    code = "llm_sin_saldo"


class LimiteProveedor(ProviderError):
    code = "llm_limite_proveedor"


class ProveedorNoDisponible(ProviderError):
    code = "llm_proveedor_no_disponible"


class ErrorConexion(ProviderError):
    code = "llm_conexion"


class TiempoAgotado(ProviderError):
    code = "llm_timeout"


class Rechazo(ProviderError):
    code = "llm_rechazo"


class RespuestaIncompleta(ProviderError):
    code = "llm_respuesta_incompleta"


class RespuestaInvalida(ProviderError):
    code = "llm_respuesta_invalida"


class SolicitudRechazada(ProviderError):
    code = "llm_solicitud_rechazada"
