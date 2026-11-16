import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { FileQuestion, Info, Loader2, Sparkles, Trash2 } from "lucide-react";
import { useAuth } from "@/auth/context";
import { AnalisisPanel } from "@/components/descanso/AnalisisPanel";
import { CertificadoViewer } from "@/components/descanso/CertificadoViewer";
import { FormularioDecision } from "@/components/descanso/FormularioDecision";
import { Progreso } from "@/components/descanso/Progreso";
import { EmptyState } from "@/components/EmptyState";
import { EstadoBadge } from "@/components/Indicador";
import { PageHeader } from "@/components/PageHeader";
import { Seccion } from "@/components/Seccion";
import { AppShell } from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useDescanso, useEliminarDescanso } from "@/hooks/queries";
import { useAnalizar } from "@/hooks/useAnalizar";
import { useToast } from "@/hooks/use-toast";
import { useI18n } from "@/i18n/context";
import { ApiError } from "@/lib/api";
import { formatoFechaHora } from "@/lib/fechas";
import { explicacion, periodo } from "@/lib/textos";
import { useLlm } from "@/llm/context";

interface EstadoNavegacion {
  desde?: string;
  /** Tras registrar el descanso, lanza la lectura con IA al llegar aquí. */
  analizar?: boolean;
}

export default function DescansoDetalle() {
  const { id } = useParams();
  const { esRRHH } = useAuth();
  const { credencial } = useLlm();
  const { toast } = useToast();
  const { t } = useI18n();
  const d = t.detalle;
  const navigate = useNavigate();
  const location = useLocation();
  const estado = (location.state as EstadoNavegacion | null) ?? {};
  const { data: descanso, isLoading, error } = useDescanso(id);
  const { analizar, analizando } = useAnalizar();
  const eliminar = useEliminarDescanso();
  const [confirmarBorrado, setConfirmarBorrado] = useState(false);
  const lecturaAutomatica = useRef(false);

  useEffect(() => {
    if (!estado.analizar || !descanso || lecturaAutomatica.current) return;
    lecturaAutomatica.current = true;
    // Se limpia la marca para que recargar la página no repita la lectura.
    navigate(location.pathname, { replace: true, state: { desde: estado.desde } });
    if (descanso.permisos.puede_analizar) void analizar(descanso);
  }, [estado.analizar, estado.desde, descanso, analizar, navigate, location.pathname]);

  const volver =
    estado.desde ??
    (esRRHH && descanso && !descanso.es_propio ? "/rrhh/descansos" : "/descansos");
  const textoVolver =
    volver === "/rrhh/descansos" ? d.volver.solicitudes : volver === "/" ? d.volver.inicio : d.volver.misDescansos;

  if (isLoading) {
    return (
      <AppShell seccion={volver === "/rrhh/descansos" ? "solicitudes" : "mis-descansos"}>
        <Skeleton className="mb-6 h-10 w-64" />
        <Skeleton className="h-96 w-full" />
      </AppShell>
    );
  }

  if (!descanso) {
    const noExiste = error instanceof ApiError && error.status === 404;
    return (
      <AppShell seccion={volver === "/rrhh/descansos" ? "solicitudes" : "mis-descansos"}>
        <PageHeader volver={{ to: volver, texto: textoVolver }} titulo={d.titulo} />
        <EmptyState
          icono={FileQuestion}
          titulo={noExiste ? d.noEncontrado : d.errorCarga}
          descripcion={noExiste ? d.noEncontradoDetalle : d.errorCargaDetalle}
        />
      </AppShell>
    );
  }

  const { colaborador } = descanso;
  const enLectura = analizando(descanso.id) || descanso.analisis_en_curso;
  const titulo =
    esRRHH && !descanso.es_propio ? `${colaborador.nombres} ${colaborador.apellidos}` : d.titulo;
  const subtitulo = [
    esRRHH && !descanso.es_propio ? d.dni(colaborador.dni) : null,
    d.sede(descanso.sede),
    periodo(descanso) ?? d.fechasPorConfirmar,
  ]
    .filter(Boolean)
    .join(" · ");

  const borrar = async () => {
    try {
      await eliminar.mutateAsync(descanso.id);
      toast({ title: d.eliminado, description: d.eliminadoDetalle });
      navigate(volver, { replace: true });
    } catch (causa) {
      toast({
        title: d.noSeEliminó,
        description: causa instanceof ApiError ? causa.message : d.intentaDeNuevo,
        variant: "destructive",
      });
      setConfirmarBorrado(false);
    }
  };

  return (
    <AppShell seccion={volver === "/rrhh/descansos" ? "solicitudes" : "mis-descansos"}>
      <PageHeader
        volver={{ to: volver, texto: textoVolver }}
        titulo={
          <span className="flex flex-wrap items-center gap-3">
            {titulo}
            <EstadoBadge estado={descanso.estado} />
          </span>
        }
        descripcion={subtitulo}
      />

      <div className="space-y-8">
        <Progreso descanso={descanso} analizando={analizando(descanso.id)} />

        <div className="flex items-start gap-3 rounded-lg bg-muted/60 p-4 text-sm">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
          <p>{explicacion(descanso, esRRHH)}</p>
        </div>

        <div className="grid gap-10 lg:grid-cols-[minmax(0,24rem)_minmax(0,1fr)]">
          <CertificadoViewer descanso={descanso} />

          <div className="space-y-10">
            <Seccion
              titulo={d.lectura.titulo}
              descripcion={d.lectura.descripcion}
              accion={
                descanso.permisos.puede_analizar && descanso.ultimo_analisis && !enLectura ? (
                  <Button variant="outline" size="sm" className="gap-2" onClick={() => analizar(descanso)}>
                    <Sparkles className="h-4 w-4" aria-hidden />
                    {d.lectura.volverALeer}
                  </Button>
                ) : undefined
              }
            >
              {enLectura ? (
                <p className="flex items-center gap-2 rounded-lg border p-4 text-sm text-muted-foreground" role="status">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  {d.lectura.leyendo}
                </p>
              ) : descanso.ultimo_analisis ? (
                <AnalisisPanel analisis={descanso.ultimo_analisis} />
              ) : descanso.permisos.puede_analizar ? (
                <div className="space-y-3 rounded-lg border border-dashed p-4">
                  <p className="text-sm text-muted-foreground">{d.lectura.sinLeer(Boolean(credencial))}</p>
                  <Button variant="outline" size="sm" className="gap-2" onClick={() => analizar(descanso)}>
                    <Sparkles className="h-4 w-4" aria-hidden />
                    {d.lectura.leer}
                  </Button>
                </div>
              ) : (
                <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                  {d.lectura.noSePidio}
                </p>
              )}
            </Seccion>

            {descanso.permisos.puede_decidir && (
              <Seccion
                titulo={d.decision.titulo}
                descripcion={d.decision.descripcion}
              >
                <FormularioDecision
                  key={descanso.ultimo_analisis?.id ?? "sin-lectura"}
                  descanso={descanso}
                />
              </Seccion>
            )}

            {descanso.estado !== "Pendiente" && (
              <Seccion titulo={d.decision.seccionRRHH}>
                <dl className="space-y-3 rounded-lg border p-4 text-sm">
                  <div className="flex flex-wrap justify-between gap-2">
                    <dt className="text-muted-foreground">{d.decision.resultado}</dt>
                    <dd>
                      <EstadoBadge estado={descanso.estado} />
                    </dd>
                  </div>
                  {periodo(descanso) && (
                    <div className="flex flex-wrap justify-between gap-2">
                      <dt className="text-muted-foreground">{d.decision.periodo}</dt>
                      <dd>{periodo(descanso)}</dd>
                    </div>
                  )}
                  <div className="flex flex-wrap justify-between gap-2">
                    <dt className="text-muted-foreground">{d.decision.fecha}</dt>
                    <dd>{formatoFechaHora(descanso.decidido_at)}</dd>
                  </div>
                  {descanso.comentario_rrhh && (
                    <div className="space-y-1 border-t pt-3">
                      <dt className="text-muted-foreground">{d.decision.comentario}</dt>
                      <dd className="whitespace-pre-wrap">{descanso.comentario_rrhh}</dd>
                    </div>
                  )}
                </dl>
              </Seccion>
            )}

            {descanso.permisos.puede_eliminar && (
              <div className="border-t pt-6">
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-2 text-red-700 hover:bg-red-50 hover:text-red-800"
                  onClick={() => setConfirmarBorrado(true)}
                >
                  <Trash2 className="h-4 w-4" aria-hidden />
                  {d.eliminar.boton}
                </Button>
              </div>
            )}

          </div>
        </div>
      </div>

      <Dialog open={confirmarBorrado} onOpenChange={setConfirmarBorrado}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{d.eliminar.pregunta}</DialogTitle>
            <DialogDescription>{d.eliminar.detalle}</DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setConfirmarBorrado(false)}>
              {t.comun.acciones.cancelar}
            </Button>
            <Button variant="destructive" onClick={borrar} disabled={eliminar.isPending}>
              {eliminar.isPending ? d.eliminar.eliminando : d.eliminar.confirmar}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
