import { useState } from "react";
import { Check, Filter, Sparkles, X } from "lucide-react";
import { DescansoCard } from "@/components/DescansoCard";
import { Layout } from "@/components/Layout";
import { Paginacion } from "@/components/Paginacion";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useDecidir, useDescansos } from "@/hooks/queries";
import { useAnalizar } from "@/hooks/useAnalizar";
import { useDebounce } from "@/hooks/useDebounce";
import { useToast } from "@/hooks/use-toast";
import { ApiError } from "@/lib/api";
import type { Descanso, EstadoDescanso } from "@/lib/types";

const POR_PAGINA = 20;
type Accion = "Aprobado" | "Rechazado";

interface Decision {
  descanso: Descanso;
  accion: Accion;
  inicio: string;
  fin: string;
  comentario: string;
  deAnalisis: boolean;
}

export default function RRHHDescansos() {
  const { toast } = useToast();
  const [estado, setEstado] = useState<EstadoDescanso | "todos">("Pendiente");
  const [dni, setDni] = useState("");
  const [sede, setSede] = useState("");
  const [offset, setOffset] = useState(0);
  const dniFiltro = useDebounce(dni);
  const sedeFiltro = useDebounce(sede.trim());

  const { data, isLoading, isError, isFetching } = useDescansos({
    estado: estado === "todos" ? undefined : estado,
    dni: dniFiltro || undefined,
    sede: sedeFiltro || undefined,
    limit: POR_PAGINA,
    offset,
  });
  const decidir = useDecidir();
  const { analizar, analizando } = useAnalizar();
  const [decision, setDecision] = useState<Decision | null>(null);
  const [errorDecision, setErrorDecision] = useState<string | null>(null);

  const abrirDecision = (descanso: Descanso, accion: Accion) => {
    const leido = descanso.ultimo_analisis?.extraidos;
    // Las fechas que leyó la IA solo se proponen: quien las confirma es la persona.
    const usarAnalisis = !descanso.fecha_inicio && !descanso.fecha_fin && Boolean(leido);
    setErrorDecision(null);
    setDecision({
      descanso,
      accion,
      inicio: descanso.fecha_inicio ?? leido?.fecha_inicio_doc ?? "",
      fin: descanso.fecha_fin ?? leido?.fecha_fin_doc ?? "",
      comentario: "",
      deAnalisis: usarAnalisis && Boolean(leido?.fecha_inicio_doc || leido?.fecha_fin_doc),
    });
  };

  const confirmar = async (evento: React.FormEvent) => {
    evento.preventDefault();
    if (!decision) return;
    const { descanso, accion, inicio, fin, comentario } = decision;
    if (accion === "Aprobado" && (!inicio || !fin)) {
      setErrorDecision("Indica las fechas de inicio y fin para aprobar.");
      return;
    }
    if (inicio && fin && fin < inicio) {
      setErrorDecision("La fecha de fin no puede ser anterior a la de inicio.");
      return;
    }
    if (accion === "Rechazado" && !comentario.trim()) {
      setErrorDecision("Explica el motivo del rechazo: el colaborador lo verá.");
      return;
    }
    try {
      await decidir.mutateAsync({
        id: descanso.id,
        decision: {
          estado: accion,
          comentario_rrhh: comentario.trim() || null,
          fecha_inicio: inicio || null,
          fecha_fin: fin || null,
        },
      });
      toast({ title: accion === "Aprobado" ? "Descanso aprobado" : "Descanso rechazado" });
      setDecision(null);
    } catch (error) {
      setErrorDecision(
        error instanceof ApiError ? error.message : "No se pudo registrar la decisión.",
      );
    }
  };

  const cambiarFiltro = <T,>(setter: (valor: T) => void) => (valor: T) => {
    setter(valor);
    setOffset(0);
  };

  const descansos = data?.items ?? [];

  return (
    <Layout>
      <div>
        <h1 className="text-3xl font-bold">Gestión de descansos médicos</h1>
        <p className="mt-1 text-muted-foreground">
          Revisa cada certificado, analízalo con IA si quieres una segunda lectura y decide.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Filter className="h-5 w-5" aria-hidden />
            Filtros
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="filtro-estado">Estado</Label>
            <Select
              value={estado}
              onValueChange={(v) => cambiarFiltro(setEstado)(v as EstadoDescanso | "todos")}
            >
              <SelectTrigger id="filtro-estado">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todos">Todos</SelectItem>
                <SelectItem value="Pendiente">Pendiente</SelectItem>
                <SelectItem value="Aprobado">Aprobado</SelectItem>
                <SelectItem value="Rechazado">Rechazado</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="filtro-dni">DNI</Label>
            <Input
              id="filtro-dni"
              inputMode="numeric"
              maxLength={8}
              placeholder="Buscar por DNI"
              value={dni}
              onChange={(e) => cambiarFiltro(setDni)(e.target.value.replace(/\D/g, ""))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="filtro-sede">Sede</Label>
            <Input
              id="filtro-sede"
              maxLength={100}
              placeholder="Buscar por sede"
              value={sede}
              onChange={(e) => cambiarFiltro(setSede)(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <div className={isFetching && !isLoading ? "grid gap-4 opacity-70" : "grid gap-4"}>
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : isError ? (
          <Alert variant="destructive">
            <AlertDescription>No se pudieron cargar los descansos. Recarga la página.</AlertDescription>
          </Alert>
        ) : descansos.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              No hay descansos que coincidan con los filtros.
            </CardContent>
          </Card>
        ) : (
          descansos.map((descanso) => (
            <DescansoCard
              key={descanso.id}
              descanso={descanso}
              mostrarColaborador
              analizando={analizando(descanso.id)}
              acciones={
                <>
                  {descanso.permisos.puede_decidir && (
                    <>
                      <Button
                        className="gap-2 bg-success hover:bg-success/90"
                        onClick={() => abrirDecision(descanso, "Aprobado")}
                      >
                        <Check className="h-4 w-4" />
                        Aprobar
                      </Button>
                      <Button
                        variant="destructive"
                        className="gap-2"
                        onClick={() => abrirDecision(descanso, "Rechazado")}
                      >
                        <X className="h-4 w-4" />
                        Rechazar
                      </Button>
                    </>
                  )}
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
                </>
              }
            />
          ))
        )}
      </div>

      {data && (
        <Paginacion
          total={data.total}
          limit={data.limit}
          offset={data.offset}
          onCambio={setOffset}
          etiqueta="descansos"
        />
      )}

      <Dialog open={decision !== null} onOpenChange={(abierto) => !abierto && setDecision(null)}>
        <DialogContent>
          {decision && (
            <form onSubmit={confirmar} className="space-y-4">
              <DialogHeader>
                <DialogTitle>
                  {decision.accion === "Aprobado" ? "Aprobar descanso" : "Rechazar descanso"}
                </DialogTitle>
                <DialogDescription>
                  {decision.descanso.colaborador.nombres} {decision.descanso.colaborador.apellidos}{" "}
                  · DNI {decision.descanso.colaborador.dni}
                </DialogDescription>
              </DialogHeader>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="decision-inicio">Inicio del descanso</Label>
                  <Input
                    id="decision-inicio"
                    type="date"
                    value={decision.inicio}
                    onChange={(e) => setDecision({ ...decision, inicio: e.target.value })}
                    required={decision.accion === "Aprobado"}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="decision-fin">Fin del descanso</Label>
                  <Input
                    id="decision-fin"
                    type="date"
                    value={decision.fin}
                    min={decision.inicio || undefined}
                    onChange={(e) => setDecision({ ...decision, fin: e.target.value })}
                    required={decision.accion === "Aprobado"}
                  />
                </div>
              </div>
              {decision.deAnalisis && (
                <p className="text-xs text-muted-foreground">
                  Fechas propuestas por el análisis con IA. Compáralas con el certificado antes de
                  confirmar.
                </p>
              )}

              <div className="space-y-2">
                <Label htmlFor="decision-comentario">
                  Comentario{decision.accion === "Rechazado" ? " (obligatorio)" : " (opcional)"}
                </Label>
                <Textarea
                  id="decision-comentario"
                  rows={4}
                  maxLength={1000}
                  placeholder={
                    decision.accion === "Rechazado"
                      ? "Motivo del rechazo. El colaborador lo verá."
                      : "Nota para el colaborador."
                  }
                  value={decision.comentario}
                  onChange={(e) => setDecision({ ...decision, comentario: e.target.value })}
                />
              </div>

              {errorDecision && (
                <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive" role="alert">
                  {errorDecision}
                </p>
              )}

              <DialogFooter className="gap-2">
                <Button type="button" variant="outline" onClick={() => setDecision(null)}>
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  disabled={decidir.isPending}
                  variant={decision.accion === "Rechazado" ? "destructive" : "default"}
                  className={decision.accion === "Aprobado" ? "bg-success hover:bg-success/90" : ""}
                >
                  {decidir.isPending
                    ? "Guardando…"
                    : decision.accion === "Aprobado"
                      ? "Confirmar aprobación"
                      : "Confirmar rechazo"}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
