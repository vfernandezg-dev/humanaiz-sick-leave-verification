import { useState } from "react";
import { Segmentado } from "@/components/Segmentado";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useDecidir } from "@/hooks/queries";
import { useToast } from "@/hooks/use-toast";
import { useI18n } from "@/i18n/context";
import { ApiError } from "@/lib/api";
import type { Descanso } from "@/lib/types";

type Accion = "Aprobado" | "Rechazado";

/**
 * Decisión de RRHH. Si hubo lectura con IA, sus fechas se proponen, pero quien
 * las confirma es la persona.
 */
export function FormularioDecision({ descanso }: { descanso: Descanso }) {
  const decidir = useDecidir();
  const { t } = useI18n();
  const f = t.detalle.formulario;
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
      setError(f.faltanFechas);
      return;
    }
    if (inicio && fin && fin < inicio) {
      setError(f.finAntesDeInicio);
      return;
    }
    if (accion === "Rechazado" && !comentario.trim()) {
      setError(f.faltaComentario);
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
      toast({ title: accion === "Aprobado" ? f.aprobado : f.rechazado });
    } catch (causa) {
      setError(causa instanceof ApiError ? causa.message : f.noSeRegistro);
    }
  };

  return (
    // noValidate: los mensajes propios (en el idioma de la app y con contexto) sustituyen a los del navegador.
    <form onSubmit={confirmar} noValidate className="space-y-5 rounded-lg border p-4 sm:p-5">
      <Segmentado
        etiqueta={f.etiqueta}
        valor={accion}
        onCambio={(valor) => {
          setAccion(valor);
          setError(null);
        }}
        opciones={[
          { valor: "Aprobado", texto: f.aprobar },
          { valor: "Rechazado", texto: f.rechazar },
        ]}
      />

      {accion === null ? (
        <p className="text-sm text-muted-foreground">{f.elige}</p>
      ) : (
        <>
          <div className="space-y-2">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="decision-inicio">{f.inicio}</Label>
                <Input
                  id="decision-inicio"
                  type="date"
                  value={inicio}
                  onChange={(e) => setInicio(e.target.value)}
                  required={accion === "Aprobado"}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="decision-fin">{f.fin}</Label>
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
              {fechasDeLaIA ? f.fechasDeLaIA : accion === "Aprobado" ? f.obligatorias : f.opcionales}
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="decision-comentario">
              {f.comentario}
              <span className="font-normal text-muted-foreground">
                {accion === "Rechazado" ? f.obligatorio : f.opcional}
              </span>
            </Label>
            <Textarea
              id="decision-comentario"
              rows={3}
              maxLength={1000}
              placeholder={
                accion === "Rechazado" ? f.ejemploRechazo : ""
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
            {decidir.isPending ? f.guardando : accion === "Aprobado" ? f.confirmarAprobacion : f.confirmarRechazo}
          </Button>
        </>
      )}
    </form>
  );
}
