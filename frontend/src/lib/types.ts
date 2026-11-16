// Alias legibles sobre los tipos generados desde el OpenAPI del backend.
// Regenerar con `pnpm gen:api` cuando cambie la API (ver README).
import type { components } from "./api-types";

type Schemas = components["schemas"];

export type Usuario = Schemas["Usuario"];
export type Sesion = Schemas["Sesion"];
export type ConfigPublica = Schemas["ConfigPublica"];
export type ProveedorLlm = Schemas["ProveedorLlm"];
export type Descanso = Schemas["Descanso"];
export type Analisis = Schemas["Analisis"];
export type ValidacionDetalle = Schemas["ValidacionDetalle"];
export type Colaborador = Schemas["Colaborador"];
export type Facetas = Schemas["ColaboradorFacetas"];
export type PaginaDescansos = Schemas["Pagina_Descanso_"];
export type PaginaColaboradores = Schemas["Pagina_Colaborador_"];
export type DecisionRequest = Schemas["DecisionRequest"];
export type AnalisisRequest = Schemas["AnalisisRequest"];
export type ModelosDisponibles = Schemas["ModelosDisponibles"];
export type ModeloDisponible = Schemas["ModeloDisponibleSalida"];

export type Role = Usuario["role"];
export type EstadoDescanso = Descanso["estado"];
export type EstadoDocumento = Analisis["estado_documento"];
