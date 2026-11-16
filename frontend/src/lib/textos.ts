// Textos derivados de los datos que se usan en varias pantallas. Las palabras
// viven en `@/i18n/textos/comun`; aquí solo se combinan con los datos.
import { textosActuales } from "@/i18n/context";
import { diasInclusivos, formatoFecha } from "./fechas";
import type { Descanso, EstadoDescanso, EstadoDocumento } from "./types";

export const NOMBRE_APP = "HumanAIz";

export type Tono = "neutro" | "ok" | "aviso" | "error";

export const TONO_ESTADO: Record<EstadoDescanso, Tono> = {
  Pendiente: "aviso",
  Aprobado: "ok",
  Rechazado: "error",
};

export const TONO_LECTURA: Record<EstadoDocumento, Tono> = {
  Aprobado: "ok",
  Observado: "aviso",
  Rechazado: "error",
};

/** "10/11/2026 – 12/11/2026 · 3 días", o null si aún no hay fechas confirmadas. */
export function periodo(descanso: Pick<Descanso, "fecha_inicio" | "fecha_fin">): string | null {
  const { fecha_inicio: inicio, fecha_fin: fin } = descanso;
  if (!inicio || !fin) return null;
  const dias = diasInclusivos(inicio, fin);
  const duracion = dias === null ? "" : ` · ${textosActuales().comun.dias(dias)}`;
  return `${formatoFecha(inicio)} – ${formatoFecha(fin)}${duracion}`;
}

/** Qué está pasando con el descanso y qué sigue, dicho para quien lo mira. */
export function explicacion(descanso: Descanso, esRRHH: boolean): string {
  const t = textosActuales().comun.explicacion;
  if (descanso.es_muestra) return t.muestra;
  if (descanso.estado === "Aprobado") return t.aprobado(periodo(descanso));
  if (descanso.estado === "Rechazado") return t.rechazado;
  if (descanso.permisos.puede_decidir) return t.decidir;
  if (esRRHH && descanso.es_propio) return t.propioRRHH;
  return t.pendiente;
}
