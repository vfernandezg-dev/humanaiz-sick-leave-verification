import { CheckCircle2, Sparkles } from "lucide-react";
import { Indicador } from "@/components/Indicador";

const COMPROBACIONES = [
  "El DNI coincide con la ficha del colaborador",
  "El nombre coincide con la ficha",
  "Fechas coherentes · 3 días de descanso",
  "Figura el CMP del médico tratante",
];

/**
 * Ilustración de la pantalla de ingreso: un certificado de ejemplo (generado
 * por la propia aplicación, ficticio) con el resultado de su lectura con IA.
 */
export function VistaProducto() {
  return (
    <figure className="relative mx-auto w-full max-w-md select-none" aria-label="Vista de ejemplo del producto">
      <div
        className="absolute -inset-8 -z-10 rounded-[2rem] bg-gradient-to-br from-accent via-background to-background"
        aria-hidden
      />
      <img
        src="/ilustraciones/certificado-ejemplo.webp"
        alt="Certificado médico de ejemplo, con datos ficticios y marca de agua de muestra"
        width={760}
        height={1075}
        className="w-[82%] -rotate-2 rounded-md border bg-white shadow-2xl shadow-foreground/10"
        draggable={false}
      />
      <div className="absolute -right-2 bottom-8 w-[78%] rounded-xl border bg-background/95 p-4 shadow-xl shadow-foreground/10 backdrop-blur sm:-right-6">
        <div className="mb-3 flex items-center justify-between gap-2">
          <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden />
            Lectura con IA
          </p>
          <Indicador tono="ok">Sin observaciones</Indicador>
        </div>
        <ul className="space-y-1.5">
          {COMPROBACIONES.map((texto) => (
            <li key={texto} className="flex items-start gap-2 text-xs">
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" aria-hidden />
              {texto}
            </li>
          ))}
        </ul>
        <div className="mt-3 flex items-center justify-between border-t pt-3 text-xs">
          <span className="text-muted-foreground">Decisión de RRHH</span>
          <Indicador tono="ok">Aprobado</Indicador>
        </div>
      </div>
      <figcaption className="sr-only">
        Ejemplo ficticio: certificado médico y resultado de su lectura automática.
      </figcaption>
    </figure>
  );
}
