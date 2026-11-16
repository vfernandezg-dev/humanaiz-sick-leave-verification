import type { ReactNode } from "react";
import { useI18n } from "@/i18n/context";
import { TONO_ESTADO, type Tono } from "@/lib/textos";
import { TONO_PUNTO } from "@/lib/tonos";
import type { EstadoDescanso } from "@/lib/types";
import { cn } from "@/lib/utils";

export function Indicador({ tono, children }: { tono: Tono; children: ReactNode }) {
  return (
    <span className="inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border bg-background px-2.5 py-0.5 text-xs font-medium">
      <span className={cn("h-1.5 w-1.5 rounded-full", TONO_PUNTO[tono])} aria-hidden />
      {children}
    </span>
  );
}

/** Estado de la solicitud: es la decisión de RRHH, no la lectura con IA. */
export function EstadoBadge({ estado }: { estado: EstadoDescanso }) {
  const { t } = useI18n();
  return <Indicador tono={TONO_ESTADO[estado]}>{t.comun.estado[estado]}</Indicador>;
}
