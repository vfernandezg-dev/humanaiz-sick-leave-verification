import { AlertTriangle, CheckCircle2, ChevronDown, Minus, X, XCircle } from "lucide-react";
import { useI18n } from "@/i18n/context";
import { formatoFecha, formatoFechaHora } from "@/lib/fechas";
import { TONO_LECTURA, type Tono } from "@/lib/textos";
import { TONO_FONDO, TONO_TEXTO } from "@/lib/tonos";
import type { Analisis, ValidacionDetalle } from "@/lib/types";
import { cn } from "@/lib/utils";

const ICONO: Record<Tono, typeof CheckCircle2> = {
  ok: CheckCircle2,
  aviso: AlertTriangle,
  error: XCircle,
  neutro: Minus,
};

/**
 * Mensaje de una comprobación en el idioma activo. El servidor la guarda en
 * español (y a veces con más detalle, p. ej. los días exactos), así que en
 * español se usa tal cual; en otro idioma se reescribe desde su código.
 */
function useMensajeRegla() {
  const { t, idioma } = useI18n();
  const reglas = t.detalle.analisis.reglas as Record<string, Record<ValidacionDetalle["resultado"], string> | undefined>;
  return (regla: ValidacionDetalle): string => {
    const traducido = idioma === "es" ? null : reglas[regla.codigo]?.[regla.resultado];
    return traducido || regla.mensaje || t.detalle.analisis.noSePudo;
  };
}

function Comprobacion({ regla, mensaje }: { regla: ValidacionDetalle; mensaje: string }) {
  const { t } = useI18n();
  const tono: Tono =
    regla.resultado === "ok" ? "ok" : regla.resultado === "falla" ? (regla.critica ? "error" : "aviso") : "neutro";
  const Icono = regla.resultado === "ok" ? CheckCircle2 : regla.resultado === "falla" ? X : Minus;
  return (
    <li className="flex items-start gap-2 text-sm">
      <Icono className={cn("mt-0.5 h-4 w-4 shrink-0", TONO_TEXTO[tono])} aria-hidden />
      <span>
        {mensaje}
        {regla.critica && regla.resultado === "falla" && (
          <span className="ml-1 text-xs text-muted-foreground">{t.detalle.analisis.importante}</span>
        )}
      </span>
    </li>
  );
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: string | number | null | undefined }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{etiqueta}</dt>
      <dd className="break-words text-sm">{valor === null || valor === undefined || valor === "" ? "—" : valor}</dd>
    </div>
  );
}

/**
 * Resultado de la lectura con IA. Todo se muestra como texto plano: nada de lo
 * leído del documento se interpreta como HTML.
 */
export function AnalisisPanel({ analisis }: { analisis: Analisis }) {
  const { t, idioma } = useI18n();
  const textos = t.detalle.analisis;
  const mensajeRegla = useMensajeRegla();
  const tono = TONO_LECTURA[analisis.estado_documento];
  const lectura = t.comun.lectura[analisis.estado_documento];
  const Icono = ICONO[tono];
  const e = analisis.extraidos;
  const reglas = analisis.validaciones_detalle;
  const fallidas = reglas.filter((r) => r.resultado !== "ok").length;
  const esEjemplo = analisis.proveedor === "muestra";

  // Mismo criterio que el backend: los motivos son las críticas que fallan, y
  // el comentario cuenta las críticas que fallan o, si no hay, lo que conviene revisar.
  const criticasFallidas = reglas.filter((r) => r.critica && r.resultado === "falla");
  const pendientes = reglas.filter(
    (r) => (r.critica && r.resultado === "no_evaluada") || (!r.critica && r.resultado === "falla"),
  ).length;
  const comentario =
    idioma === "es"
      ? analisis.comentario_general
      : analisis.estado_documento === "Rechazado"
        ? textos.comentario.Rechazado(criticasFallidas.length || analisis.motivos_rechazo.length)
        : analisis.estado_documento === "Observado"
          ? textos.comentario.Observado(pendientes)
          : textos.comentario.Aprobado();
  const motivos =
    idioma === "es" || criticasFallidas.length === 0
      ? analisis.motivos_rechazo
      : criticasFallidas.map(mensajeRegla);
  const tipo = e.tipo_documento
    ? ((t.comun.tipoDocumento as Record<string, string | undefined>)[e.tipo_documento] ?? e.tipo_documento)
    : null;

  return (
    <div className="space-y-4">
      <div className={cn("flex items-start gap-3 rounded-lg p-4", TONO_FONDO[tono])}>
        <Icono className={cn("mt-0.5 h-5 w-5 shrink-0", TONO_TEXTO[tono])} aria-hidden />
        <div className="space-y-1">
          <p className={cn("font-medium", TONO_TEXTO[tono])}>{lectura.etiqueta}</p>
          <p className="text-sm text-foreground/80">{comentario}</p>
          {motivos.length > 0 && (
            <ul className="space-y-1 pt-1 text-sm">
              {motivos.map((motivo) => (
                <li key={motivo} className="flex items-start gap-2">
                  <X className="mt-0.5 h-4 w-4 shrink-0 text-red-700" aria-hidden />
                  {motivo}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <details className="group rounded-lg border">
        <summary className="flex cursor-pointer items-center justify-between gap-2 px-4 py-3 text-sm font-medium hover:bg-muted/50">
          <span>{textos.verComprobaciones(reglas.length, fallidas)}</span>
          <ChevronDown className="h-4 w-4 shrink-0 transition-transform group-open:rotate-180" aria-hidden />
        </summary>
        <div className="space-y-5 border-t px-4 py-4">
          <ul className="space-y-2">
            {reglas.map((regla) => (
              <Comprobacion key={regla.codigo} regla={regla} mensaje={mensajeRegla(regla)} />
            ))}
          </ul>
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{textos.loQueLeyo}</p>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
              <Dato etiqueta={textos.datos.tipo} valor={tipo} />
              <Dato etiqueta={textos.datos.dni} valor={e.dni_en_documento} />
              <Dato etiqueta={textos.datos.nombre} valor={e.nombre_en_documento} />
              <Dato etiqueta={textos.datos.inicio} valor={e.fecha_inicio_doc ? formatoFecha(e.fecha_inicio_doc) : null} />
              <Dato etiqueta={textos.datos.fin} valor={e.fecha_fin_doc ? formatoFecha(e.fecha_fin_doc) : null} />
              <Dato etiqueta={textos.datos.dias} valor={e.dias_documento} />
              <Dato etiqueta={textos.datos.citt} valor={e.citt} />
              <Dato etiqueta={textos.datos.medico} valor={e.codigo_medico} />
              <Dato etiqueta={textos.datos.contingencia} valor={e.contingencia} />
            </dl>
          </div>
        </div>
      </details>

      <p className="text-xs leading-5 text-muted-foreground">
        {esEjemplo ? textos.ejemplo : `${analisis.proveedor} · ${analisis.modelo}`}
        {" · "}
        {textos.pie(
          formatoFechaHora(analisis.created_at),
          `${analisis.solicitado_por.nombres} ${analisis.solicitado_por.apellidos}`,
        )}
      </p>
    </div>
  );
}
