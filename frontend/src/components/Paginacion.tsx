import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n/context";

interface Props {
  total: number;
  limit: number;
  offset: number;
  onCambio: (offset: number) => void;
  /** Qué se cuenta, ya traducido y en plural ("colaboradores", "employees"). */
  etiqueta: string;
}

export function Paginacion({ total, limit, offset, onCambio, etiqueta }: Props) {
  const { t } = useI18n();
  if (total === 0) return null;
  const desde = offset + 1;
  const hasta = Math.min(offset + limit, total);
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
      <span>{t.comun.paginacion(desde, hasta, total, etiqueta)}</span>
      {total > limit && (
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onCambio(Math.max(0, offset - limit))}
            disabled={offset === 0}
          >
            {t.comun.acciones.anterior}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onCambio(offset + limit)}
            disabled={hasta >= total}
          >
            {t.comun.acciones.siguiente}
          </Button>
        </div>
      )}
    </div>
  );
}
