import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

interface Props {
  titulo: ReactNode;
  descripcion?: ReactNode;
  accion?: ReactNode;
  volver?: { to: string; texto: string };
}

export function PageHeader({ titulo, descripcion, accion, volver }: Props) {
  return (
    <div className="mb-8 space-y-4">
      {volver && (
        <Link
          to={volver.to}
          className="inline-flex items-center gap-1.5 rounded text-sm text-muted-foreground hover:text-foreground focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          {volver.texto}
        </Link>
      )}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{titulo}</h1>
          {descripcion && <p className="text-sm text-muted-foreground">{descripcion}</p>}
        </div>
        {accion}
      </div>
    </div>
  );
}
