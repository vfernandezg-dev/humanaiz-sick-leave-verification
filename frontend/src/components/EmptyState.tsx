import type { ComponentType, ReactNode } from "react";

interface Props {
  icono: ComponentType<{ className?: string }>;
  titulo: string;
  descripcion?: ReactNode;
  accion?: ReactNode;
}

export function EmptyState({ icono: Icono, titulo, descripcion, accion }: Props) {
  return (
    <div className="flex flex-col items-center rounded-lg border border-dashed px-6 py-14 text-center">
      <Icono className="mb-3 h-8 w-8 text-muted-foreground/70" />
      <p className="font-medium">{titulo}</p>
      {descripcion && <p className="mt-1 max-w-sm text-sm text-muted-foreground">{descripcion}</p>}
      {accion && <div className="mt-5">{accion}</div>}
    </div>
  );
}
