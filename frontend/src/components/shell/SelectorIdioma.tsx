import { IDIOMAS, NOMBRE_IDIOMA } from "@/i18n/definir";
import { useI18n } from "@/i18n/context";
import { cn } from "@/lib/utils";

/** Conmutador ES / EN. Cada opción se anuncia con el nombre del idioma en ese idioma. */
export function SelectorIdioma({ className }: { className?: string }) {
  const { idioma, cambiarIdioma, t } = useI18n();
  return (
    <div role="group" aria-label={t.shell.idioma} className={cn("flex rounded-md border p-0.5", className)}>
      {IDIOMAS.map((opcion) => (
        <button
          key={opcion}
          type="button"
          lang={opcion}
          aria-pressed={idioma === opcion}
          aria-label={NOMBRE_IDIOMA[opcion]}
          title={NOMBRE_IDIOMA[opcion]}
          onClick={() => cambiarIdioma(opcion)}
          className={cn(
            "rounded px-2 py-0.5 text-xs font-medium uppercase transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring",
            idioma === opcion ? "bg-foreground text-background" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {opcion}
        </button>
      ))}
    </div>
  );
}
