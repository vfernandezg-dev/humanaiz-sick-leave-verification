import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Download, FileWarning } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { useI18n } from "@/i18n/context";
import { api, ApiError } from "@/lib/api";
import type { Descanso } from "@/lib/types";

/**
 * Imagen del certificado. Se pide con el token de sesión y se muestra desde un
 * blob: un `<img src>` normal no puede enviar la cabecera Authorization, y los
 * documentos no tienen URL pública. Los descansos antiguos pueden tener varias
 * páginas (cuando se admitían PDF), por eso se conserva la paginación.
 */
export function CertificadoViewer({ descanso }: { descanso: Descanso }) {
  const { toast } = useToast();
  const { t } = useI18n();
  const v = t.detalle.visor;
  const total = descanso.archivo.paginas;
  const [pagina, setPagina] = useState(1);
  const [descargando, setDescargando] = useState(false);
  // El resultado se guarda junto a la página que lo pidió: mientras llega la
  // siguiente, la anterior simplemente no coincide y se muestra el esqueleto,
  // sin tener que vaciar el estado al empezar cada carga.
  const clave = `${descanso.id}:${pagina}`;
  const [carga, setCarga] = useState<{ clave: string; url: string | null; fallo: boolean } | null>(null);
  const actual = carga?.clave === clave ? carga : null;
  const url = actual?.url ?? null;
  const fallo = actual?.fallo ?? false;

  useEffect(() => {
    const control = new AbortController();
    let creada: string | null = null;
    api
      .pagina(descanso.id, pagina, control.signal)
      .then((blob) => {
        if (control.signal.aborted) return;
        creada = URL.createObjectURL(blob);
        setCarga({ clave: `${descanso.id}:${pagina}`, url: creada, fallo: false });
      })
      .catch((error: unknown) => {
        if (!(error instanceof ApiError && error.code === "cancelada")) {
          setCarga({ clave: `${descanso.id}:${pagina}`, url: null, fallo: true });
        }
      });
    return () => {
      control.abort();
      if (creada) URL.revokeObjectURL(creada);
    };
  }, [descanso.id, pagina]);

  const descargar = async () => {
    setDescargando(true);
    try {
      const blob = await api.imagen(descanso.id);
      const temporal = URL.createObjectURL(blob);
      const enlace = document.createElement("a");
      enlace.href = temporal;
      enlace.download = `certificado-${descanso.id.slice(0, 8)}.jpg`;
      enlace.click();
      window.setTimeout(() => URL.revokeObjectURL(temporal), 1000);
    } catch (error) {
      toast({
        title: v.noSeDescargo,
        description: error instanceof ApiError ? error.message : t.detalle.intentaDeNuevo,
        variant: "destructive",
      });
    } finally {
      setDescargando(false);
    }
  };

  return (
    <figure className="space-y-2">
      <div className="flex min-h-64 items-center justify-center overflow-hidden rounded-lg border bg-muted/40">
        {fallo ? (
          <div className="flex flex-col items-center gap-2 p-6 text-sm text-muted-foreground">
            <FileWarning className="h-6 w-6" aria-hidden />
            {v.noCargo}
          </div>
        ) : url ? (
          <img
            src={url}
            alt={v.alt(pagina, total)}
            className="max-h-[36rem] w-full object-contain"
          />
        ) : (
          <Skeleton className="h-80 w-full rounded-none" />
        )}
      </div>
      <figcaption className="flex flex-wrap items-center justify-between gap-2">
        {total > 1 ? (
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setPagina((p) => Math.max(1, p - 1))}
              disabled={pagina === 1}
              aria-label={v.paginaAnterior}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="px-1 text-xs text-muted-foreground">{v.pagina(pagina, total)}</span>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setPagina((p) => Math.min(total, p + 1))}
              disabled={pagina === total}
              aria-label={v.paginaSiguiente}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <span className="text-xs text-muted-foreground">{v.optimizada}</span>
        )}
        <Button variant="ghost" size="sm" className="gap-2" onClick={descargar} disabled={descargando}>
          <Download className="h-4 w-4" aria-hidden />
          {descargando ? v.descargando : v.descargar}
        </Button>
      </figcaption>
    </figure>
  );
}
