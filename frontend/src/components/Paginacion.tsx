import { Button } from "@/components/ui/button";

interface Props {
  total: number;
  limit: number;
  offset: number;
  onCambio: (offset: number) => void;
  etiqueta: string;
}

export function Paginacion({ total, limit, offset, onCambio, etiqueta }: Props) {
  if (total === 0) return null;
  const desde = offset + 1;
  const hasta = Math.min(offset + limit, total);
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
      <span>
        Mostrando {desde}–{hasta} de {total} {etiqueta}
      </span>
      {total > limit && (
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onCambio(Math.max(0, offset - limit))}
            disabled={offset === 0}
          >
            Anterior
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onCambio(offset + limit)}
            disabled={hasta >= total}
          >
            Siguiente
          </Button>
        </div>
      )}
    </div>
  );
}
