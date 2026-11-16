// La API devuelve las fechas de calendario como texto "AAAA-MM-DD".
// `new Date("2026-11-10")` las interpreta en UTC y en Perú (UTC-5) muestra el
// día anterior: por eso aquí se construyen siempre en hora local.
//
// El formato sigue el idioma activo. En inglés se escribe el mes con letras
// ("Nov 10, 2026"): "10/11/2026" se leería como 11 de octubre en EE. UU.
import { idiomaActual, type Idioma } from "@/i18n/definir";

interface Formatos {
  fecha: Intl.DateTimeFormat;
  diaMes: Intl.DateTimeFormat;
  fechaHora: Intl.DateTimeFormat;
}

const FORMATOS: Record<Idioma, Formatos> = {
  es: {
    fecha: new Intl.DateTimeFormat("es-PE", { day: "2-digit", month: "2-digit", year: "numeric" }),
    diaMes: new Intl.DateTimeFormat("es-PE", { day: "numeric", month: "short" }),
    fechaHora: new Intl.DateTimeFormat("es-PE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }),
  },
  en: {
    fecha: new Intl.DateTimeFormat("en-US", { day: "numeric", month: "short", year: "numeric" }),
    diaMes: new Intl.DateTimeFormat("en-US", { day: "numeric", month: "short" }),
    fechaHora: new Intl.DateTimeFormat("en-US", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }),
  },
};

const formatos = () => FORMATOS[idiomaActual()];

function aFechaLocal(iso: string): Date | null {
  const partes = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!partes) return null;
  const fecha = new Date(Number(partes[1]), Number(partes[2]) - 1, Number(partes[3]));
  return Number.isNaN(fecha.getTime()) ? null : fecha;
}

/** "2026-11-10" -> "10/11/2026" (o "Nov 10, 2026"). Devuelve "—" si no hay fecha. */
export function formatoFecha(iso: string | null | undefined): string {
  const fecha = iso ? aFechaLocal(iso) : null;
  return fecha ? formatos().fecha.format(fecha) : "—";
}

/** Marca de tiempo ISO con zona (created_at, etc.) -> fecha y hora locales. */
export function formatoFechaHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  const fecha = new Date(iso);
  return Number.isNaN(fecha.getTime()) ? "—" : formatos().fechaHora.format(fecha);
}

/** Marca de tiempo ISO -> "15 nov." / "Nov 15" (para listados). */
export function formatoFechaCorta(iso: string | null | undefined): string {
  if (!iso) return "—";
  const fecha = new Date(iso);
  return Number.isNaN(fecha.getTime()) ? "—" : formatos().diaMes.format(fecha);
}

/** Días de calendario entre dos fechas, contando ambos extremos. */
export function diasInclusivos(inicio: string, fin: string): number | null {
  const a = aFechaLocal(inicio);
  const b = aFechaLocal(fin);
  if (!a || !b) return null;
  return Math.round((b.getTime() - a.getTime()) / 86_400_000) + 1;
}
