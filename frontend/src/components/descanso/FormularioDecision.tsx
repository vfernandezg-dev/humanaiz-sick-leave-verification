import { useState } from "react";
import { Segmentado } from "@/components/Segmentado";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useDecidir } from "@/hooks/queries";
import { useToast } from "@/hooks/use-toast";
import { ApiError } from "@/lib/api";
import type { Descanso } from "@/lib/types";

type Accion = "Aprobado" | "Rechazado";

/**
 * Decisión de RRHH. Si hubo lectura con IA, sus fechas se proponen, pero quien
 * las confirma es la persona.
 */
export function FormularioDecision({ descanso }: { descanso: Descanso }) {
  const decidir = useDecidir();
  const { toast } = useToast();
  const leido = descanso.ultimo_analisis?.extraidos;
  const [accion, setAccion] = useState<Accion | null>(null);
  const [inicio, setInicio] = useState(descanso.fecha_inicio ?? leido?.fecha_inicio_doc ?? "");
  const [fin, setFin] = useState(descanso.fecha_fin ?? leido?.fecha_fin_doc ?? "");
  const [comentario, setComentario] = useState("");
  const [error, setError] = useState<string | null>(null);
  const fechasDeLaIA =
    !descanso.fecha_inicio && Boolean(leido?.fecha_inicio_doc || leido?.fecha_fin_doc);

  const confirmar = async (evento: React.FormEvent) => {
    evento.preventDefault();
    if (!accion) return;
    setError(null);
    if (accion === "Aprobado" && (!inicio || !fin)) {
      setError("Indica la fecha de inicio y la de fin para aprobar.");
      return;
    }
    if (inicio && fin && fin < inicio) {
      setError("La fecha de fin no puede ser anterior a la de inicio.");
      return;
    }
    if (accion === "Rechazado" && !comentario.trim()) {
      setError("Explica el motivo del rechazo: el colaborador lo verá.");
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
    } catch (causa) {
      setError(causa instanceof ApiError ? causa.message : "No se pudo registrar la decisión.");
    }
  };

  return (
    // noValidate: los mensajes propios (en español y con contexto) sustituyen a los del navegador.
    <form onSubmit={confirmar} noValidate className="space-y-5 rounded-lg border p-4 sm:p-5">
      <Segmentado
        etiqueta="Decisión"
        valor={accion}
        onCambio={(valor) => {
          setAccion(valor);
          setError(null);
        }}
        opciones={[
          { valor: "Aprobado", texto: "Aprobar" },
          { valor: "Rechazado", texto: "Rechazar" },
        ]}
      />

      {accion === null ? (
        <p className="text-sm text-muted-foreground">Elige si apruebas o rechazas el descanso.</p>
      ) : (
        <>
          <div className="space-y-2">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="decision-inicio">Inicio del descanso</Label>
                <Input
                  id="decision-inicio"
                  type="date"
                  value={inicio}
                  onChange={(e) => setInicio(e.target.value)}
                  required={accion === "Aprobado"}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="decision-fin">Fin del descanso</Label>
                <Input
                  id="decision-fin"
                  type="date"
                  value={fin}
                  min={inicio || undefined}
                  onChange={(e) => setFin(e.target.value)}
                  required={accion === "Aprobado"}
                />
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              {fechasDeLaIA
                ? "Fechas propuestas por la lectura con IA: compáralas con el certificado antes de confirmar."
                : accion === "Aprobado"
                  ? "Obligatorias para aprobar."
                  : "Opcionales al rechazar."}
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="decision-comentario">
              Comentario para el colaborador
              <span className="font-normal text-muted-foreground">
                {accion === "Rechazado" ? " (obligatorio)" : " (opcional)"}
              </span>
            </Label>
            <Textarea
              id="decision-comentario"
              rows={3}
              maxLength={1000}
              placeholder={
                accion === "Rechazado" ? "Por ejemplo: el certificado está a nombre de otra persona." : ""
              }
              value={comentario}
              onChange={(e) => setComentario(e.target.value)}
            />
          </div>

          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
              {error}
            </p>
          )}

          <Button
            type="submit"
            variant={accion === "Rechazado" ? "destructive" : "default"}
            disabled={decidir.isPending}
          >
            {decidir.isPending
              ? "Guardando…"
              : accion === "Aprobado"
                ? "Confirmar aprobación"
                : "Confirmar rechazo"}
          </Button>
        </>
      )}
    </form>
  );
}
