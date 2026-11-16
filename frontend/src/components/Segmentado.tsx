import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface OpcionSegmentada<T extends string> {
  valor: T;
  texto: ReactNode;
}

interface Props<T extends string> {
  etiqueta: string;
  opciones: OpcionSegmentada<T>[];
  valor: T | null;
  onCambio: (valor: T) => void;
  className?: string;
}

/** Selector de una opción entre pocas, visible de un vistazo (en vez de un desplegable). */
export function Segmentado<T extends string>({
  etiqueta,
  opciones,
  valor,
  onCambio,
  className,
}: Props<T>) {
  return (
    <div
      role="radiogroup"
      aria-label={etiqueta}
      className={cn("inline-flex flex-wrap gap-1 rounded-lg border bg-muted/50 p-1", className)}
    >
      {opciones.map((opcion) => {
        const activa = opcion.valor === valor;
        return (
          <button
            key={opcion.valor}
            type="button"
            role="radio"
            aria-checked={activa}
            onClick={() => onCambio(opcion.valor)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring",
              activa
                ? "bg-background font-medium text-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {opcion.texto}
          </button>
        );
      })}
    </div>
  );
}
