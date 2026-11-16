import { AlertTriangle, CheckCircle2, ChevronDown, Minus, X, XCircle } from "lucide-react";
import { formatoFecha, formatoFechaHora } from "@/lib/fechas";
import { LECTURA_IA, TIPO_DOCUMENTO, type Tono } from "@/lib/textos";
import { TONO_FONDO, TONO_TEXTO } from "@/lib/tonos";
import type { Analisis, ValidacionDetalle } from "@/lib/types";
import { cn } from "@/lib/utils";

const ICONO: Record<Tono, typeof CheckCircle2> = {
  ok: CheckCircle2,
  aviso: AlertTriangle,
  error: XCircle,
  neutro: Minus,
};

function Comprobacion({ regla }: { regla: ValidacionDetalle }) {
  const tono: Tono =
    regla.resultado === "ok" ? "ok" : regla.resultado === "falla" ? (regla.critica ? "error" : "aviso") : "neutro";
  const Icono = regla.resultado === "ok" ? CheckCircle2 : regla.resultado === "falla" ? X : Minus;
  return (
    <li className="flex items-start gap-2 text-sm">
      <Icono className={cn("mt-0.5 h-4 w-4 shrink-0", TONO_TEXTO[tono])} aria-hidden />
      <span>
        {regla.mensaje || "No se pudo comprobar."}
        {regla.critica && regla.resultado === "falla" && (
          <span className="ml-1 text-xs text-muted-foreground">(importante)</span>
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
  const lectura = LECTURA_IA[analisis.estado_documento];
  const Icono = ICONO[lectura.tono];
  const e = analisis.extraidos;
  const fallidas = analisis.validaciones_detalle.filter((r) => r.resultado !== "ok").length;
  const esEjemplo = analisis.proveedor === "muestra";

  return (
    <div className="space-y-4">
      <div className={cn("flex items-start gap-3 rounded-lg p-4", TONO_FONDO[lectura.tono])}>
        <Icono className={cn("mt-0.5 h-5 w-5 shrink-0", TONO_TEXTO[lectura.tono])} aria-hidden />
        <div className="space-y-1">
          <p className={cn("font-medium", TONO_TEXTO[lectura.tono])}>{lectura.etiqueta}</p>
          <p className="text-sm text-foreground/80">{analisis.comentario_general}</p>
          {analisis.motivos_rechazo.length > 0 && (
            <ul className="space-y-1 pt-1 text-sm">
              {analisis.motivos_rechazo.map((motivo) => (
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
          <span>
            Ver las {analisis.validaciones_detalle.length} comprobaciones
            {fallidas > 0 ? ` (${fallidas} con observaciones)` : ""} y los datos leídos
          </span>
          <ChevronDown className="h-4 w-4 shrink-0 transition-transform group-open:rotate-180" aria-hidden />
        </summary>
        <div className="space-y-5 border-t px-4 py-4">
          <ul className="space-y-2">
            {analisis.validaciones_detalle.map((regla) => (
              <Comprobacion key={regla.codigo} regla={regla} />
            ))}
          </ul>
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Lo que leyó la IA en el documento
            </p>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
              <Dato etiqueta="Tipo" valor={TIPO_DOCUMENTO[e.tipo_documento ?? ""] ?? e.tipo_documento} />
              <Dato etiqueta="DNI" valor={e.dni_en_documento} />
              <Dato etiqueta="Nombre" valor={e.nombre_en_documento} />
              <Dato etiqueta="Inicio" valor={e.fecha_inicio_doc ? formatoFecha(e.fecha_inicio_doc) : null} />
              <Dato etiqueta="Fin" valor={e.fecha_fin_doc ? formatoFecha(e.fecha_fin_doc) : null} />
              <Dato etiqueta="Días indicados" valor={e.dias_documento} />
              <Dato etiqueta="N.º de CITT" valor={e.citt} />
              <Dato etiqueta="Médico (CMP)" valor={e.codigo_medico} />
              <Dato etiqueta="Contingencia" valor={e.contingencia} />
            </dl>
          </div>
        </div>
      </details>

      <p className="text-xs leading-5 text-muted-foreground">
        {esEjemplo ? "Lectura de ejemplo incluida en la demo" : `${analisis.proveedor} · ${analisis.modelo}`}
        {" · "}
        {formatoFechaHora(analisis.created_at)} · pedida por {analisis.solicitado_por.nombres}{" "}
        {analisis.solicitado_por.apellidos}. La IA puede equivocarse: es una ayuda, la decisión
        la toma RRHH.
      </p>
    </div>
  );
}
