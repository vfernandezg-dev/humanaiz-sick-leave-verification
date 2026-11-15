import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Download, FileWarning } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { api, ApiError } from "@/lib/api";
import type { Descanso } from "@/lib/types";

const EXTENSION: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
  "application/pdf": "pdf",
};

/**
 * Muestra las páginas del certificado. Las imágenes se piden con el token de
 * sesión y se muestran desde un blob: un `<img src>` normal no puede enviar la
 * cabecera Authorization y los documentos no tienen URL pública.
 */
export function CertificadoViewer({ descanso }: { descanso: Descanso }) {
  const { toast } = useToast();
  const total = descanso.archivo.paginas;
  const [pagina, setPagina] = useState(1);
  const [url, setUrl] = useState<string | null>(null);
  const [fallo, setFallo] = useState(false);
  const [descargando, setDescargando] = useState(false);

  useEffect(() => {
    const control = new AbortController();
    let creada: string | null = null;
    setUrl(null);
    setFallo(false);
    api
      .pagina(descanso.id, pagina, control.signal)
      .then((blob) => {
        if (control.signal.aborted) return;
        creada = URL.createObjectURL(blob);
        setUrl(creada);
      })
      .catch((error: unknown) => {
        if (!(error instanceof ApiError && error.code === "cancelada")) setFallo(true);
      });
    return () => {
      control.abort();
      // Libera la imagen de la memoria del navegador al cambiar de página o salir.
      if (creada) URL.revokeObjectURL(creada);
    };
  }, [descanso.id, pagina]);

  const descargar = async () => {
    setDescargando(true);
    try {
      const blob = await api.original(descanso.id);
      const enlace = document.createElement("a");
      const temporal = URL.createObjectURL(blob);
      enlace.href = temporal;
      enlace.download = `certificado-${descanso.id.slice(0, 8)}.${EXTENSION[descanso.archivo.mime] ?? "bin"}`;
      enlace.click();
      window.setTimeout(() => URL.revokeObjectURL(temporal), 1000);
    } catch (error) {
      toast({
        title: "No se pudo descargar",
        description: error instanceof ApiError ? error.message : "Inténtalo de nuevo.",
        variant: "destructive",
      });
    } finally {
      setDescargando(false);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex min-h-48 max-w-md items-center justify-center overflow-hidden rounded-lg border bg-muted/30">
        {fallo ? (
          <div className="flex flex-col items-center gap-2 p-6 text-sm text-muted-foreground">
            <FileWarning className="h-6 w-6" aria-hidden />
            No se pudo cargar el documento.
          </div>
        ) : url ? (
          <img
            src={url}
            alt={`Certificado médico, página ${pagina} de ${total}`}
            className="max-h-[32rem] w-full object-contain"
          />
        ) : (
          <Skeleton className="h-72 w-full" />
        )}
      </div>
      <div className="flex max-w-md flex-wrap items-center justify-between gap-2">
        {total > 1 ? (
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => setPagina((p) => Math.max(1, p - 1))}
              disabled={pagina === 1}
              aria-label="Página anterior"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="px-2 text-sm text-muted-foreground">
              Página {pagina} de {total}
            </span>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => setPagina((p) => Math.min(total, p + 1))}
              disabled={pagina === total}
              aria-label="Página siguiente"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <span />
        )}
        <Button variant="ghost" size="sm" className="gap-2" onClick={descargar} disabled={descargando}>
          <Download className="h-4 w-4" />
          {descargando ? "Descargando…" : "Descargar original"}
        </Button>
      </div>
    </div>
  );
}
