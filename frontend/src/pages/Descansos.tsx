import { useState } from "react";
import { FileText, Plus, Sparkles, Trash2 } from "lucide-react";
import { useAuth } from "@/auth/context";
import { DescansoCard } from "@/components/DescansoCard";
import { Layout } from "@/components/Layout";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useConfig, useCrearDescanso, useEliminarDescanso, useMisDescansos } from "@/hooks/queries";
import { useAnalizar } from "@/hooks/useAnalizar";
import { useToast } from "@/hooks/use-toast";
import { ApiError } from "@/lib/api";
import type { Descanso } from "@/lib/types";
import { useLlm } from "@/llm/context";

const MB = 1024 * 1024;
const TIPOS_POR_DEFECTO = ["image/jpeg", "image/png", "image/webp", "application/pdf"];

export default function Descansos() {
  const { usuario } = useAuth();
  const { credencial, abrir: abrirClave } = useLlm();
  const { toast } = useToast();
  const { data: config } = useConfig();
  const { data, isLoading, isError } = useMisDescansos({ limit: 100 });
  const crear = useCrearDescanso();
  const eliminar = useEliminarDescanso();
  const { analizar, analizando } = useAnalizar();

  const [formularioAbierto, setFormularioAbierto] = useState(false);
  const [sede, setSede] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [errorArchivo, setErrorArchivo] = useState<string | null>(null);
  const [analizarAlSubir, setAnalizarAlSubir] = useState(true);
  const [porEliminar, setPorEliminar] = useState<Descanso | null>(null);

  const tipos = config?.carga.tipos_mime ?? TIPOS_POR_DEFECTO;
  const maxBytes = config?.carga.max_bytes ?? 10 * MB;
  const sinFicha = !usuario?.colaborador;

  const abrirFormulario = () => {
    setSede(usuario?.colaborador?.sede ?? "");
    setArchivo(null);
    setErrorArchivo(null);
    setFormularioAbierto(true);
  };

  // Comprobaciones de cortesía: quien valida de verdad el archivo es el servidor.
  const elegirArchivo = (elegido: File | null) => {
    setErrorArchivo(null);
    if (elegido && elegido.size > maxBytes) {
      setArchivo(null);
      setErrorArchivo(`El archivo supera el máximo de ${Math.floor(maxBytes / MB)} MB.`);
      return;
    }
    if (elegido && elegido.type && !tipos.includes(elegido.type)) {
      setArchivo(null);
      setErrorArchivo("Formato no admitido. Sube una imagen JPG, PNG o WebP, o un PDF.");
      return;
    }
    setArchivo(elegido);
  };

  const registrar = async (evento: React.FormEvent) => {
    evento.preventDefault();
    if (!archivo) {
      setErrorArchivo("Adjunta el certificado médico.");
      return;
    }
    try {
      const creado = await crear.mutateAsync({ archivo, sede });
      setFormularioAbierto(false);
      toast({
        title: "Descanso registrado",
        description: "RRHH revisará tu certificado y confirmará las fechas.",
      });
      if (analizarAlSubir && credencial) await analizar(creado);
    } catch (error) {
      const mensaje =
        error instanceof ApiError ? error.message : "No se pudo registrar el descanso.";
      if (error instanceof ApiError && error.detalles.some((d) => d.campo === "sede")) {
        toast({ title: "Revisa la sede", description: mensaje, variant: "destructive" });
      } else {
        setErrorArchivo(mensaje);
      }
    }
  };

  const confirmarEliminar = async () => {
    if (!porEliminar) return;
    try {
      await eliminar.mutateAsync(porEliminar.id);
      toast({ title: "Descanso eliminado", description: "También se borró su documento." });
    } catch (error) {
      toast({
        title: "No se pudo eliminar",
        description: error instanceof ApiError ? error.message : "Inténtalo de nuevo.",
        variant: "destructive",
      });
    } finally {
      setPorEliminar(null);
    }
  };

  const descansos = data?.items ?? [];

  return (
    <Layout>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold">Mis descansos médicos</h1>
          <p className="mt-1 text-muted-foreground">
            Sube tu certificado y sigue el estado de la revisión.
          </p>
        </div>
        <Button className="gap-2" onClick={abrirFormulario} disabled={sinFicha}>
          <Plus className="h-4 w-4" />
          Nuevo descanso
        </Button>
      </div>

      {sinFicha && (
        <Alert>
          <AlertDescription>
            Tu cuenta todavía no está vinculada a una ficha de colaborador, así que no puedes
            registrar descansos. Contacta con Recursos Humanos.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4">
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : isError ? (
          <Alert variant="destructive">
            <AlertDescription>No se pudieron cargar tus descansos. Recarga la página.</AlertDescription>
          </Alert>
        ) : descansos.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <FileText className="mb-4 h-12 w-12 text-muted-foreground" aria-hidden />
              <p className="text-center text-muted-foreground">
                Aún no tienes descansos médicos registrados.
              </p>
            </CardContent>
          </Card>
        ) : (
          descansos.map((descanso) => (
            <DescansoCard
              key={descanso.id}
              descanso={descanso}
              analizando={analizando(descanso.id)}
              acciones={
                <>
                  {descanso.permisos.puede_analizar && (
                    <Button
                      variant="outline"
                      className="gap-2"
                      onClick={() => analizar(descanso)}
                      disabled={analizando(descanso.id) || descanso.analisis_en_curso}
                    >
                      <Sparkles className="h-4 w-4" />
                      {descanso.ultimo_analisis ? "Volver a analizar" : "Analizar con IA"}
                    </Button>
                  )}
                  {descanso.permisos.puede_eliminar && (
                    <Button
                      variant="ghost"
                      className="gap-2 text-destructive hover:text-destructive"
                      onClick={() => setPorEliminar(descanso)}
                    >
                      <Trash2 className="h-4 w-4" />
                      Eliminar
                    </Button>
                  )}
                </>
              }
            />
          ))
        )}
      </div>

      <Dialog open={formularioAbierto} onOpenChange={setFormularioAbierto}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Registrar descanso médico</DialogTitle>
            <DialogDescription>
              Sube una foto o un PDF de tu certificado. Las fechas las confirma RRHH al revisarlo.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={registrar} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="sede">Sede</Label>
              <Input
                id="sede"
                placeholder="Ej.: Lima Centro"
                value={sede}
                maxLength={100}
                onChange={(e) => setSede(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="archivo">Certificado médico</Label>
              <Input
                id="archivo"
                type="file"
                accept={tipos.join(",")}
                onChange={(e) => elegirArchivo(e.target.files?.[0] ?? null)}
                aria-invalid={Boolean(errorArchivo)}
              />
              <p className="text-xs text-muted-foreground">
                JPG, PNG, WebP o PDF de hasta {config?.carga.max_paginas_pdf ?? 5} páginas. Máximo{" "}
                {Math.floor(maxBytes / MB)} MB.
              </p>
              {errorArchivo && (
                <p className="text-sm text-destructive" role="alert">
                  {errorArchivo}
                </p>
              )}
            </div>

            {credencial ? (
              <div className="flex items-start gap-3">
                <Checkbox
                  id="analizar-al-subir"
                  checked={analizarAlSubir}
                  onCheckedChange={(valor) => setAnalizarAlSubir(valor === true)}
                  className="mt-0.5"
                />
                <Label htmlFor="analizar-al-subir" className="font-normal leading-snug">
                  Analizarlo ahora con mi clave de IA
                </Label>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                ¿Quieres comprobar el documento al subirlo?{" "}
                <button type="button" className="text-primary underline" onClick={abrirClave}>
                  Configura tu clave de IA
                </button>
                . Es opcional.
              </p>
            )}

            <DialogFooter>
              <Button type="submit" className="w-full" disabled={crear.isPending}>
                {crear.isPending ? "Subiendo…" : "Registrar descanso"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={porEliminar !== null} onOpenChange={(abierto) => !abierto && setPorEliminar(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>¿Eliminar este descanso?</DialogTitle>
            <DialogDescription>
              Se borrará la solicitud junto con el documento y sus análisis. No se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setPorEliminar(null)}>
              Cancelar
            </Button>
            <Button variant="destructive" onClick={confirmarEliminar} disabled={eliminar.isPending}>
              {eliminar.isPending ? "Eliminando…" : "Eliminar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
