import { useEffect, useRef, useState } from "react";
import { FileText, UploadCloud, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Props {
  id: string;
  archivo: File | null;
  onElegir: (archivo: File | null) => void;
  accept: string;
  ayuda: string;
  invalido?: boolean;
}

function tamano(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Zona para soltar o elegir el certificado, con vista previa si es una imagen. */
export function Dropzone({ id, archivo, onElegir, accept, ayuda, invalido }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [arrastrando, setArrastrando] = useState(false);
  const [vistaPrevia, setVistaPrevia] = useState<string | null>(null);

  useEffect(() => {
    if (!archivo || !archivo.type.startsWith("image/")) {
      setVistaPrevia(null);
      return;
    }
    const url = URL.createObjectURL(archivo);
    setVistaPrevia(url);
    return () => URL.revokeObjectURL(url);
  }, [archivo]);

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
          {vistaPrevia ? (
            <img src={vistaPrevia} alt="" className="h-16 w-12 shrink-0 rounded border object-cover" />
          ) : (
            <div className="flex h-16 w-12 shrink-0 items-center justify-center rounded border bg-muted">
              <FileText className="h-5 w-5 text-muted-foreground" aria-hidden />
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{archivo.name}</p>
            <p className="text-xs text-muted-foreground">{tamano(archivo.size)}</p>
          </div>
          <Button type="button" variant="ghost" size="sm" onClick={elegir}>
            Cambiar
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => onElegir(null)}
            aria-label="Quitar archivo"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ) : (
        <button
          type="button"
          onClick={elegir}
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
            "flex w-full flex-col items-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            arrastrando ? "border-primary bg-accent/60" : "hover:bg-muted/50",
            invalido && "border-destructive/60",
          )}
        >
          <UploadCloud className="h-8 w-8 text-muted-foreground" aria-hidden />
          <span className="text-sm font-medium">
            Arrastra el certificado aquí o <span className="text-primary underline">elige un archivo</span>
          </span>
          <span id={`${id}-ayuda`} className="text-xs text-muted-foreground">
            {ayuda}
          </span>
        </button>
      )}
    </div>
  );
}
