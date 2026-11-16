import { Check, Loader2, X } from "lucide-react";
import { formatoFechaHora } from "@/lib/fechas";
import { LECTURA_IA } from "@/lib/textos";
import type { Descanso } from "@/lib/types";
import { cn } from "@/lib/utils";

type EstadoPaso = "hecho" | "en_curso" | "actual" | "opcional" | "error";

interface Paso {
  titulo: string;
  detalle: string;
  estado: EstadoPaso;
}

function Marca({ estado, numero }: { estado: EstadoPaso; numero: number }) {
  const base = "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-medium";
  if (estado === "hecho") {
    return (
      <span className={cn(base, "bg-foreground text-background")}>
        <Check className="h-3.5 w-3.5" aria-hidden />
      </span>
    );
  }
  if (estado === "error") {
    return (
      <span className={cn(base, "bg-red-600 text-white")}>
        <X className="h-3.5 w-3.5" aria-hidden />
      </span>
    );
  }
  if (estado === "en_curso") {
    return (
      <span className={cn(base, "border-2 border-primary text-primary")}>
        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
      </span>
    );
  }
  return (
    <span
      className={cn(
        base,
        estado === "actual"
          ? "border-2 border-primary text-primary"
          : "border border-dashed border-muted-foreground/50 text-muted-foreground",
      )}
    >
      {numero}
    </span>
  );
}

/** Los tres pasos de una solicitud y en cuál está. */
export function Progreso({ descanso, analizando }: { descanso: Descanso; analizando: boolean }) {
  const lectura = descanso.ultimo_analisis;
  const enLectura = analizando || descanso.analisis_en_curso;
  const pendiente = descanso.estado === "Pendiente";

  const pasos: Paso[] = [
    { titulo: "Registrado", detalle: formatoFechaHora(descanso.created_at), estado: "hecho" },
    {
      titulo: "Lectura con IA",
      detalle: enLectura
        ? "En curso…"
        : lectura
          ? LECTURA_IA[lectura.estado_documento].etiqueta
          : pendiente
            ? "Opcional"
            : "No se usó",
      estado: enLectura ? "en_curso" : lectura ? "hecho" : "opcional",
    },
    {
      titulo: "Decisión de RRHH",
      detalle: pendiente
        ? "En espera"
        : `${descanso.estado} · ${formatoFechaHora(descanso.decidido_at)}`,
      estado: pendiente ? "actual" : descanso.estado === "Rechazado" ? "error" : "hecho",
    },
  ];

  return (
    <ol aria-label="Progreso de la solicitud" className="grid gap-4 sm:grid-cols-3">
      {pasos.map((paso, indice) => (
        <li key={paso.titulo} className="flex items-start gap-3">
          <Marca estado={paso.estado} numero={indice + 1} />
          <div className="min-w-0 pt-0.5">
            <p className="text-sm font-medium">{paso.titulo}</p>
            <p className="truncate text-xs text-muted-foreground">{paso.detalle}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
