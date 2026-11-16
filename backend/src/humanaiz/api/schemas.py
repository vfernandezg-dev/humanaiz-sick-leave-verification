"""Formas de entrada y salida de la API (el contrato con el frontend)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Role = Literal["colaborador", "analista_rrhh"]
EstadoDescanso = Literal["Pendiente", "Aprobado", "Rechazado"]
EstadoDocumento = Literal["Aprobado", "Observado", "Rechazado"]

Dni = Annotated[str, StringConstraints(pattern=r"^[0-9]{8}$")]


class _Salida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Pagina[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


# ---------- sesión ----------


class LoginRequest(BaseModel):
    dni: Dni
    password: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    # Cada inicio de sesión exige aceptar la versión vigente de los términos.
    acepta_terminos: bool = False
    terminos_version: Annotated[str, StringConstraints(max_length=20)] | None = None


class UsuarioColaborador(BaseModel):
    id: uuid.UUID
    sede: str | None
    area_operacion: str | None


class Usuario(BaseModel):
    id: uuid.UUID
    dni: str
    nombres: str
    apellidos: str
    role: Role
    is_demo: bool
    colaborador: UsuarioColaborador | None


class Sesion(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in: int
    usuario: Usuario


# ---------- configuración pública ----------


class DemoUsuario(BaseModel):
    role: Role
    dni: str
    password: str
    etiqueta: str


class DemoConfig(BaseModel):
    habilitado: bool
    aviso: str | None
    usuarios: list[DemoUsuario]
    retencion_horas: int


class ProyectoConfig(BaseModel):
    concurso: str | None
    puesto: int | None = Field(description="Puesto obtenido en el concurso (1 = ganador).")
    contacto: str | None
    version_terminos: str
    retencion_registros_dias: int


class CargaConfig(BaseModel):
    max_bytes: int
    tipos_mime: list[str]
    min_lado_px: int = Field(description="Lado corto mínimo de la imagen, en píxeles.")
    max_lado_px: int = Field(
        description=(
            "Lado largo con el que se guarda la imagen. El navegador puede reducirla a "
            "este tamaño antes de subirla sin perder nada de lo que se conserva."
        )
    )


class ModeloLlm(BaseModel):
    id: str
    nombre: str
    predeterminado: bool


class ProveedorLlm(BaseModel):
    id: str
    nombre: str
    formato_clave: str
    # Prefijos con los que la interfaz reconoce el proveedor al pegar la clave.
    prefijos_clave: list[str]
    url_claves: str
    max_imagenes: int
    # Modelos sugeridos; se acepta cualquier otro con nombre válido.
    modelos: list[ModeloLlm]


class LlmConfig(BaseModel):
    proveedores: list[ProveedorLlm]


class ConfigPublica(BaseModel):
    proyecto: ProyectoConfig
    demo: DemoConfig
    carga: CargaConfig
    llm: LlmConfig


# ---------- colaboradores ----------


class Colaborador(_Salida):
    id: uuid.UUID
    dni: str
    apellidos: str
    nombres: str
    fecha_nacimiento: date
    categoria: str
    sexo: str
    celular: str | None
    area_operacion: str
    tipo_contrato: str
    sede: str
    activo: bool


class ColaboradorFacetas(BaseModel):
    areas_operacion: list[str]
    tipos_contrato: list[str]
    sedes: list[str]


# ---------- análisis ----------


class Extraidos(BaseModel):
    """Campos leídos del documento. `null` significa "no legible o ausente"."""

    dni_en_documento: str | None = None
    nombre_en_documento: str | None = None
    citt: str | None = None
    fecha_inicio_doc: date | None = None
    fecha_fin_doc: date | None = None
    dias_documento: int | None = None
    contingencia: str | None = None
    codigo_medico: str | None = None
    tipo_documento: str | None = None
    es_certificado_medico: bool | None = None
    legible: bool | None = None
    fecha_emision_doc: date | None = None


class ValidacionDetalle(BaseModel):
    codigo: str
    critica: bool
    resultado: Literal["ok", "falla", "no_evaluada"]
    mensaje: str


class UsoTokens(BaseModel):
    tokens_entrada: int | None
    tokens_salida: int | None


class Solicitante(BaseModel):
    id: uuid.UUID
    nombres: str
    apellidos: str
    role: Role


class Analisis(BaseModel):
    id: uuid.UUID
    created_at: datetime
    proveedor: str
    modelo: str
    solicitado_por: Solicitante
    estado_documento: EstadoDocumento
    extraidos: Extraidos
    validaciones: dict[str, bool]
    validaciones_detalle: list[ValidacionDetalle]
    motivos_rechazo: list[str]
    comentario_general: str
    uso: UsoTokens | None
    duracion_ms: int | None
    version_prompt: str
    version_reglas: str


class ModelosRequest(BaseModel):
    proveedor: Annotated[str, StringConstraints(min_length=1, max_length=20)]


class ModeloDisponibleSalida(BaseModel):
    id: str
    nombre: str
    sugerido: bool


class ModelosDisponibles(BaseModel):
    proveedor: str
    modelos: list[ModeloDisponibleSalida]


class AnalisisRequest(BaseModel):
    proveedor: Annotated[str, StringConstraints(min_length=1, max_length=20)]
    modelo: Annotated[str, StringConstraints(min_length=1, max_length=120)] | None = None


# ---------- descansos ----------


class DescansoColaborador(BaseModel):
    id: uuid.UUID
    dni: str
    nombres: str
    apellidos: str


class DescansoArchivo(BaseModel):
    mime: str = Field(description="Formato de la imagen que se subió.")
    size_bytes: int = Field(description="Lo que ocupa la imagen guardada (re-codificada).")
    paginas: int


class DescansoPermisos(BaseModel):
    puede_analizar: bool
    puede_decidir: bool
    puede_eliminar: bool


class Descanso(BaseModel):
    id: uuid.UUID
    estado: EstadoDescanso
    sede: str
    # Fechas como texto YYYY-MM-DD: no pasarlas por `new Date()` en el cliente.
    fecha_inicio: date | None
    fecha_fin: date | None
    comentario_rrhh: str | None
    created_at: datetime
    updated_at: datetime
    decidido_at: datetime | None
    colaborador: DescansoColaborador
    archivo: DescansoArchivo
    ultimo_analisis: Analisis | None
    analisis_en_curso: bool
    es_muestra: bool
    es_propio: bool
    permisos: DescansoPermisos


class DecisionRequest(BaseModel):
    estado: Literal["Aprobado", "Rechazado"]
    comentario_rrhh: Annotated[str, StringConstraints(max_length=1000)] | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None


class PaginacionParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
