import { FlaskConical } from "lucide-react";
import { Link } from "react-router-dom";
import { useConfig } from "@/hooks/queries";

/** Franja fija en todas las pantallas: recuerda que es un proyecto de concurso. */
export function AvisoConcurso() {
  const { data } = useConfig();
  const concurso = data?.proyecto.concurso;

  return (
    <div role="note" className="border-b border-amber-200 bg-amber-50 text-amber-950">
      <div className="mx-auto flex max-w-5xl items-start gap-2 px-4 py-2 text-xs leading-5 sm:items-center">
        <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-amber-700 sm:mt-0" aria-hidden />
        <p>
          <strong className="font-semibold">
            Proyecto de concurso{concurso ? ` · ${concurso}` : ""}.
          </strong>{" "}
          Es una demostración sin uso real: no subas datos ni documentos verdaderos.{" "}
          <Link
            to="/terminos"
            className="whitespace-nowrap font-medium underline underline-offset-2 hover:text-amber-800"
          >
            Ver términos
          </Link>
        </p>
      </div>
    </div>
  );
}
