// La API devuelve las fechas de calendario como texto "AAAA-MM-DD".
// `new Date("2026-11-10")` las interpreta en UTC y en Perú (UTC-5) muestra el
// día anterior: por eso aquí se construyen siempre en hora local.

const FECHA = new Intl.DateTimeFormat("es-PE", { day: "2-digit", month: "2-digit", year: "numeric" });
const DIA_MES = new Intl.DateTimeFormat("es-PE", { day: "numeric", month: "short" });
const FECHA_HORA = new Intl.DateTimeFormat("es-PE", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function aFechaLocal(iso: string): Date | null {
  const partes = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!partes) return null;
  const fecha = new Date(Number(partes[1]), Number(partes[2]) - 1, Number(partes[3]));
  return Number.isNaN(fecha.getTime()) ? null : fecha;
}

/** "2026-11-10" -> "10/11/2026". Devuelve "—" si no hay fecha. */
export function formatoFecha(iso: string | null | undefined): string {
  const fecha = iso ? aFechaLocal(iso) : null;
  return fecha ? FECHA.format(fecha) : "—";
}

/** Marca de tiempo ISO con zona (created_at, etc.) -> fecha y hora locales. */
export function formatoFechaHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  const fecha = new Date(iso);
  return Number.isNaN(fecha.getTime()) ? "—" : FECHA_HORA.format(fecha);
}

/** Marca de tiempo ISO -> "15 nov." (para listados). */
export function formatoFechaCorta(iso: string | null | undefined): string {
  if (!iso) return "—";
  const fecha = new Date(iso);
  return Number.isNaN(fecha.getTime()) ? "—" : DIA_MES.format(fecha);
}

/** Días de calendario entre dos fechas, contando ambos extremos. */
export function diasInclusivos(inicio: string, fin: string): number | null {
  const a = aFechaLocal(inicio);
  const b = aFechaLocal(fin);
  if (!a || !b) return null;
  return Math.round((b.getTime() - a.getTime()) / 86_400_000) + 1;
}
