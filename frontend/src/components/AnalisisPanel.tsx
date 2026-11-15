import { AlertTriangle, CheckCircle2, CircleSlash, MinusCircle, XCircle } from "lucide-react";
import { formatoFecha, formatoFechaHora } from "@/lib/fechas";
import type { Analisis, EstadoDocumento, ValidacionDetalle } from "@/lib/types";
import { cn } from "@/lib/utils";

const ESTILO: Record<
  EstadoDocumento,
  { caja: string; texto: string; titulo: string; Icono: typeof CheckCircle2 }
> = {
  Aprobado: {
    caja: "border-success bg-success/10",
    texto: "text-success",
    titulo: "Análisis automático: sin observaciones",
    Icono: CheckCircle2,
  },
  Observado: {
    caja: "border-warning bg-warning/10",
    texto: "text-warning",
    titulo: "Análisis automático: conviene revisar",
    Icono: AlertTriangle,
  },
  Rechazado: {
    caja: "border-destructive bg-destructive/10",
    texto: "text-destructive",
    titulo: "Análisis automático: se detectaron problemas",
    Icono: XCircle,
  },
};

const TIPOS: Record<string, string> = {
  citt: "CITT (EsSalud)",
  certificado_particular: "Certificado particular",
  otro: "Otro documento",
};

function Dato({ etiqueta, valor }: { etiqueta: string; valor: string | number | null | undefined }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{etiqueta}</dt>
      <dd className="text-sm font-medium break-words">
        {valor === null || valor === undefined || valor === "" ? "—" : valor}
      </dd>
    </div>
  );
}

function Validacion({ regla }: { regla: ValidacionDetalle }) {
  const Icono =
    regla.resultado === "ok" ? CheckCircle2 : regla.resultado === "falla" ? CircleSlash : MinusCircle;
  const color =
    regla.resultado === "ok"
      ? "text-success"
      : regla.resultado === "falla"
        ? regla.critica
          ? "text-destructive"
          : "text-warning"
        : "text-muted-foreground";
  return (
    <li className="flex items-start gap-2 text-sm">
      <Icono className={cn("mt-0.5 h-4 w-4 shrink-0", color)} aria-hidden />
      <span>
        {regla.mensaje || "No se evaluó."}
        {regla.critica && regla.resultado !== "ok" && (
          <span className="ml-1 text-xs text-muted-foreground">(crítica)</span>
        )}
      </span>
    </li>
  );
}

/**
 * Resultado del análisis con IA. Todo se muestra como texto: nada de lo leído
 * del documento se interpreta como HTML.
 */
export function AnalisisPanel({ analisis }: { analisis: Analisis }) {
  const estilo = ESTILO[analisis.estado_documento];
  const e = analisis.extraidos;
  const solicitante = `${analisis.solicitado_por.nombres} ${analisis.solicitado_por.apellidos}`;

  return (
    <section className={cn("space-y-3 rounded-lg border-l-4 p-4", estilo.caja)}>
      <header className="flex items-start gap-2">
        <estilo.Icono className={cn("mt-0.5 h-5 w-5 shrink-0", estilo.texto)} aria-hidden />
        <div>
          <p className={cn("text-sm font-semibold", estilo.texto)}>{estilo.titulo}</p>
          <p className="text-sm text-muted-foreground">{analisis.comentario_general}</p>
        </div>
      </header>

      {analisis.motivos_rechazo.length > 0 && (
        <ul className="list-inside list-disc space-y-1 text-sm">
          {analisis.motivos_rechazo.map((motivo) => (
            <li key={motivo}>{motivo}</li>
          ))}
        </ul>
      )}

      <details className="group">
        <summary className="cursor-pointer text-sm font-medium text-primary hover:underline">
          Ver datos leídos y validaciones
        </summary>
        <div className="mt-3 space-y-4">
          <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Dato etiqueta="Tipo de documento" valor={TIPOS[e.tipo_documento ?? ""] ?? e.tipo_documento} />
            <Dato etiqueta="DNI en el documento" valor={e.dni_en_documento} />
            <Dato etiqueta="Nombre en el documento" valor={e.nombre_en_documento} />
            <Dato etiqueta="N.º de CITT" valor={e.citt} />
            <Dato etiqueta="Inicio" valor={formatoFecha(e.fecha_inicio_doc)} />
            <Dato etiqueta="Fin" valor={formatoFecha(e.fecha_fin_doc)} />
            <Dato etiqueta="Días indicados" valor={e.dias_documento} />
            <Dato etiqueta="Emisión" valor={formatoFecha(e.fecha_emision_doc)} />
            <Dato etiqueta="Contingencia" valor={e.contingencia} />
            <Dato etiqueta="Médico (CMP)" valor={e.codigo_medico} />
          </dl>
          <ul className="space-y-1.5">
            {analisis.validaciones_detalle.map((regla) => (
              <Validacion key={regla.codigo} regla={regla} />
            ))}
          </ul>
        </div>
      </details>

      <footer className="text-xs text-muted-foreground">
        {analisis.proveedor} · {analisis.modelo} · {formatoFechaHora(analisis.created_at)} · pedido
        por {solicitante}. Es una sugerencia: la decisión la toma RRHH.
      </footer>
    </section>
  );
}
