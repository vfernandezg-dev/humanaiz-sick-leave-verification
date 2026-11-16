// Textos de interfaz que se repiten en varias pantallas. Un solo vocabulario:
// "estado" es la decisión de RRHH; "lectura con IA" es la sugerencia
// automática. Usan palabras distintas a propósito para no confundirlas.
import { diasInclusivos, formatoFecha } from "./fechas";
import type { Descanso, EstadoDescanso, EstadoDocumento, Role } from "./types";

export const NOMBRE_APP = "HumanAIz";

export const ROL: Record<Role, string> = {
  colaborador: "Colaborador",
  analista_rrhh: "Analista de RRHH",
};

export type Tono = "neutro" | "ok" | "aviso" | "error";

export const ESTADO: Record<EstadoDescanso, { etiqueta: string; tono: Tono }> = {
  Pendiente: { etiqueta: "Pendiente", tono: "aviso" },
  Aprobado: { etiqueta: "Aprobado", tono: "ok" },
  Rechazado: { etiqueta: "Rechazado", tono: "error" },
};

export const LECTURA_IA: Record<
  EstadoDocumento,
  { etiqueta: string; descripcion: string; tono: Tono }
> = {
  Aprobado: {
    etiqueta: "Sin observaciones",
    descripcion: "Los datos del certificado coinciden con la ficha del colaborador.",
    tono: "ok",
  },
  Observado: {
    etiqueta: "Para revisar",
    descripcion: "Hay datos que la IA no pudo confirmar o que no cuadran del todo.",
    tono: "aviso",
  },
  Rechazado: {
    etiqueta: "Con problemas",
    descripcion: "Hay datos que no coinciden con la ficha o el documento no parece válido.",
    tono: "error",
  },
};

export const TIPO_DOCUMENTO: Record<string, string> = {
  citt: "CITT (EsSalud)",
  certificado_particular: "Certificado particular",
  otro: "Otro documento",
};

/** "10/11/2026 – 12/11/2026 · 3 días", o null si aún no hay fechas confirmadas. */
export function periodo(descanso: Pick<Descanso, "fecha_inicio" | "fecha_fin">): string | null {
  const { fecha_inicio: inicio, fecha_fin: fin } = descanso;
  if (!inicio || !fin) return null;
  const dias = diasInclusivos(inicio, fin);
  const duracion = dias === null ? "" : ` · ${dias} ${dias === 1 ? "día" : "días"}`;
  return `${formatoFecha(inicio)} – ${formatoFecha(fin)}${duracion}`;
}

/** Qué está pasando con el descanso y qué sigue, dicho para quien lo mira. */
export function explicacion(descanso: Descanso, esRRHH: boolean): string {
  if (descanso.es_muestra) {
    return "Es un ejemplo incluido en la demostración: puedes verlo, pero no modificarlo.";
  }
  if (descanso.estado === "Aprobado") {
    const fechas = periodo(descanso);
    return fechas ? `RRHH aprobó el descanso (${fechas}).` : "RRHH aprobó el descanso.";
  }
  if (descanso.estado === "Rechazado") {
    return "RRHH rechazó el descanso. El motivo está en la sección «Decisión de RRHH».";
  }
  if (descanso.permisos.puede_decidir) {
    return "Revisa el certificado y decide. Si quieres una segunda opinión, pide antes una lectura con IA (es opcional).";
  }
  if (esRRHH && descanso.es_propio) {
    return "Es tu propio descanso: lo revisará otra persona de RRHH.";
  }
  return "Tu certificado está registrado. RRHH lo revisará y confirmará las fechas; vuelve a esta página para ver la decisión.";
}
