import { useEffect, useRef, useState } from "react";
import { ImageIcon, Loader2, UploadCloud, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n/context";
import { cn } from "@/lib/utils";

interface Props {
  id: string;
  archivo: File | null;
  onElegir: (archivo: File | null) => void;
  accept: string;
  ayuda: string;
  invalido?: boolean;
  /** Mientras se prepara la imagen elegida. */
  ocupado?: boolean;
}

function tamano(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Vista previa de la imagen elegida. La URL temporal se crea y se libera en el
 * mismo efecto y se asigna directamente al elemento: sin estado intermedio, y
 * sin URLs revocadas si React repite el efecto (modo estricto).
 */
function Miniatura({ archivo }: { archivo: File }) {
  const imagen = useRef<HTMLImageElement>(null);
  useEffect(() => {
    const url = URL.createObjectURL(archivo);
    if (imagen.current) imagen.current.src = url;
    return () => URL.revokeObjectURL(url);
  }, [archivo]);
  return <img ref={imagen} alt="" className="h-16 w-12 shrink-0 rounded border object-cover" />;
}

/** Zona para soltar o elegir la imagen del certificado, con vista previa. */
export function Dropzone({ id, archivo, onElegir, accept, ayuda, invalido, ocupado }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const { t } = useI18n();
  const z = t.registro.zona;
  const [arrastrando, setArrastrando] = useState(false);

  const elegir = () => input.current?.click();

  return (
    <div>
      <input
        ref={input}
        id={id}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={(evento) => {
          onElegir(evento.target.files?.[0] ?? null);
          // Permite volver a elegir el mismo archivo tras quitarlo.
          evento.target.value = "";
        }}
      />
      {archivo ? (
        <div className="flex items-center gap-4 rounded-lg border p-3">
          {archivo.type.startsWith("image/") ? (
            <Miniatura archivo={archivo} />
          ) : (
            <div className="flex h-16 w-12 shrink-0 items-center justify-center rounded border bg-muted">
              <ImageIcon className="h-5 w-5 text-muted-foreground" aria-hidden />
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{archivo.name}</p>
            <p className="text-xs text-muted-foreground">{tamano(archivo.size)}</p>
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={elegir}>
            {z.cambiar}
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => onElegir(null)}
            aria-label={z.quitar}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ) : (
        <button
          type="button"
          onClick={elegir}
          disabled={ocupado}
          aria-busy={ocupado}
          onDragOver={(evento) => {
            evento.preventDefault();
            setArrastrando(true);
          }}
          onDragLeave={() => setArrastrando(false)}
          onDrop={(evento) => {
            evento.preventDefault();
            setArrastrando(false);
            const soltado = evento.dataTransfer.files?.[0];
            if (soltado) onElegir(soltado);
          }}
          aria-describedby={`${id}-ayuda`}
          className={cn(
            "flex w-full flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring",
            arrastrando ? "border-primary bg-accent/60" : "hover:bg-muted/50",
            invalido && "border-destructive/60",
          )}
        >
          {ocupado ? (
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden />
          ) : (
            <UploadCloud className="h-8 w-8 text-muted-foreground" aria-hidden />
          )}
          <span className="text-sm font-medium">
            {ocupado ? (
              z.preparando
            ) : (
              <>
                {z.arrastra}
                <span className="text-primary underline">{z.elige}</span>
              </>
            )}
          </span>
          <span id={`${id}-ayuda`} className="text-xs text-muted-foreground">
            {ayuda}
          </span>
        </button>
      )}
    </div>
  );
}
