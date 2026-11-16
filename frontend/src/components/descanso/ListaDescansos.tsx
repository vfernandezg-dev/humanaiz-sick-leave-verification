import { Link } from "react-router-dom";
import { ChevronRight, Loader2 } from "lucide-react";
import { EstadoBadge } from "@/components/Indicador";
import { formatoFechaCorta } from "@/lib/fechas";
import { LECTURA_IA, periodo } from "@/lib/textos";
import { TONO_TEXTO } from "@/lib/tonos";
import type { Descanso } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  descansos: Descanso[];
  /** "propia": la persona ve sus descansos; "rrhh": se identifica a cada colaborador. */
  vista: "propia" | "rrhh";
  /** Ruta a la que vuelve el detalle. */
  desde: string;
}

export function ListaDescansos({ descansos, vista, desde }: Props) {
  return (
    <ul className="divide-y overflow-hidden rounded-lg border">
      {descansos.map((d) => {
        const fechas = periodo(d) ?? "Fechas por confirmar";
        const lectura = d.ultimo_analisis ? LECTURA_IA[d.ultimo_analisis.estado_documento] : null;
        const titulo =
          vista === "rrhh" ? `${d.colaborador.apellidos}, ${d.colaborador.nombres}` : fechas;
        const detalle = [
          vista === "rrhh" ? `DNI ${d.colaborador.dni}` : null,
          vista === "rrhh" ? fechas : null,
          d.sede,
          `Registrado el ${formatoFechaCorta(d.created_at)}`,
        ]
          .filter(Boolean)
          .join(" · ");

        return (
          <li key={d.id}>
            <Link
              to={`/descansos/${d.id}`}
              state={{ desde }}
              className="group flex items-center gap-4 px-4 py-3.5 transition-colors hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:outline-none"
            >
              <div className="min-w-0 flex-1 space-y-1">
                <p className="flex items-center gap-2 text-sm font-medium">
                  <span className="truncate">{titulo}</span>
                  {d.es_muestra && (
                    <span className="shrink-0 rounded border px-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                      Ejemplo
                    </span>
                  )}
                </p>
                <p className="truncate text-xs text-muted-foreground">{detalle}</p>
              </div>
              <span className="hidden shrink-0 text-xs sm:block">
                {d.analisis_en_curso ? (
                  <span className="inline-flex items-center gap-1.5 text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
                    Leyendo con IA…
                  </span>
                ) : (
                  lectura && (
                    <span className={TONO_TEXTO[lectura.tono]}>IA: {lectura.etiqueta.toLowerCase()}</span>
                  )
                )}
              </span>
              <EstadoBadge estado={d.estado} />
              <ChevronRight
                className={cn(
                  "h-4 w-4 shrink-0 text-muted-foreground transition-transform",
                  "group-hover:translate-x-0.5",
                )}
                aria-hidden
              />
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
