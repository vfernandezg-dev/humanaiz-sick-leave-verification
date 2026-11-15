"""Tipos de datos del motor de escaneo."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TipoDocumento = Literal["citt", "certificado_particular", "otro"]
EstadoDocumento = Literal["Aprobado", "Observado", "Rechazado"]
ResultadoRegla = Literal["ok", "falla", "no_evaluada"]


class Extraccion(BaseModel):
    """Lo único que se le pide al modelo: leer campos del documento.

    Objeto plano, todos los campos obligatorios y solo tipos primitivos que
    admiten null: es el subconjunto de JSON Schema que aceptan los tres
    proveedores en modo de salida estructurada. No hay ningún campo de texto
    libre dirigido a quien revisa, para que el documento no pueda "escribirle"
    a RRHH a través del modelo.
    """

    model_config = ConfigDict(extra="forbid")

    es_certificado_medico: bool = Field(
        description="true si la imagen es un certificado o constancia de descanso médico."
    )
    legible: bool = Field(
        description="true si el documento se puede leer lo suficiente para extraer sus datos."
    )
    tipo_documento: TipoDocumento = Field(
        description=(
            "'citt' si es un Certificado de Incapacidad Temporal para el Trabajo de EsSalud; "
            "'certificado_particular' si lo emite una clínica, hospital o médico; "
            "'otro' en cualquier otro caso."
        )
    )
    dni_en_documento: str | None = Field(
        description="DNI del paciente tal como aparece, solo dígitos. null si no figura."
    )
    nombre_en_documento: str | None = Field(
        description="Nombre completo del paciente tal como aparece. null si no figura."
    )
    citt: str | None = Field(
        description="Número de CITT tal como aparece. null si el documento no tiene."
    )
    codigo_medico: str | None = Field(
        description="Número de colegiatura (CMP) del médico tratante. null si no figura."
    )
    contingencia: str | None = Field(
        description=(
            "Contingencia o tipo de incapacidad indicada (p. ej. enfermedad común, "
            "accidente de trabajo, maternidad). null si no figura."
        )
    )
    fecha_inicio_doc: str | None = Field(
        description="Fecha de inicio del descanso en formato AAAA-MM-DD. null si no figura."
    )
    fecha_fin_doc: str | None = Field(
        description="Fecha de fin del descanso en formato AAAA-MM-DD. null si no figura."
    )
    fecha_emision_doc: str | None = Field(
        description="Fecha de emisión del documento en formato AAAA-MM-DD. null si no figura."
    )
    dias_documento: int | None = Field(
        description="Número de días de descanso que indica el documento. null si no figura."
    )

    @field_validator("tipo_documento", mode="before")
    @classmethod
    def _tipo_en_minusculas(cls, value: object) -> object:
        # Algún proveedor no garantiza la caja de los valores enumerados.
        return value.strip().lower() if isinstance(value, str) else value


@dataclass(frozen=True, slots=True)
class ExtractionOutcome:
    extraccion: Extraccion
    tokens_entrada: int | None = None
    tokens_salida: int | None = None
    # Modelo que respondió de verdad (puede diferir del pedido si hubo fallback).
    modelo_efectivo: str | None = None
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class ContextoValidacion:
    """Datos del sistema contra los que se contrasta lo leído en el documento."""

    dni: str
    nombres: str
    apellidos: str
    hoy: date
    rangos_aprobados: tuple[tuple[date, date], ...] = ()
    archivo_duplicado: bool = False
    citt_duplicado: bool = False
    max_dias: int = 30
    max_dias_futuro: int = 30
    max_dias_antiguedad: int = 90


@dataclass(frozen=True, slots=True)
class Regla:
    codigo: str
    critica: bool
    resultado: ResultadoRegla
    mensaje: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "codigo": self.codigo,
            "critica": self.critica,
            "resultado": self.resultado,
            "mensaje": self.mensaje,
        }


@dataclass(frozen=True, slots=True)
class ResultadoAnalisis:
    estado_documento: EstadoDocumento
    extraidos: dict[str, Any]
    reglas: tuple[Regla, ...]
    motivos_rechazo: tuple[str, ...]
    comentario_general: str
    fecha_inicio: date | None = field(default=None)
    fecha_fin: date | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        """Forma que se guarda y se devuelve por la API (compatible con el panel existente)."""
        return {
            "estado_documento": self.estado_documento,
            "extraidos": self.extraidos,
            # Mapa booleano heredado: solo las reglas que sí se pudieron evaluar.
            "validaciones": {
                r.codigo: r.resultado == "ok" for r in self.reglas if r.resultado != "no_evaluada"
            },
            "validaciones_detalle": [r.to_dict() for r in self.reglas],
            "motivos_rechazo": list(self.motivos_rechazo),
            "comentario_general": self.comentario_general,
        }
