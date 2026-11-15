import type { ReactNode } from "react";
import { Calendar, Loader2 } from "lucide-react";
import { AnalisisPanel } from "@/components/AnalisisPanel";
import { CertificadoViewer } from "@/components/CertificadoViewer";
import { EstadoBadge } from "@/components/EstadoBadge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { diasInclusivos, formatoFecha, formatoFechaHora } from "@/lib/fechas";
import type { Descanso } from "@/lib/types";

interface Props {
  descanso: Descanso;
  /** En la vista de RRHH el título es la persona; en "Mis descansos", las fechas. */
  mostrarColaborador?: boolean;
  analizando?: boolean;
  acciones?: ReactNode;
}

function Periodo({ descanso }: { descanso: Descanso }) {
  if (!descanso.fecha_inicio || !descanso.fecha_fin) {
    return <span className="text-muted-foreground">Fechas por confirmar</span>;
  }
  const dias = diasInclusivos(descanso.fecha_inicio, descanso.fecha_fin);
  return (
    <span>
      {formatoFecha(descanso.fecha_inicio)} – {formatoFecha(descanso.fecha_fin)}
      {dias !== null && (
        <span className="ml-2 text-sm font-normal text-muted-foreground">
          ({dias} {dias === 1 ? "día" : "días"})
        </span>
      )}
    </span>
  );
}

export function DescansoCard({ descanso, mostrarColaborador, analizando, acciones }: Props) {
  const { colaborador } = descanso;
  const enAnalisis = analizando || descanso.analisis_en_curso;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2 text-xl">
              {mostrarColaborador ? (
                <>
                  {colaborador.nombres} {colaborador.apellidos}
                </>
              ) : (
                <>
                  <Calendar className="h-5 w-5 shrink-0" aria-hidden />
                  <Periodo descanso={descanso} />
                </>
              )}
            </CardTitle>
            <CardDescription>
              {mostrarColaborador && <>DNI {colaborador.dni} · </>}
              Sede: {descanso.sede} · Registrado el {formatoFechaHora(descanso.created_at)}
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {descanso.es_muestra && <Badge variant="outline">Muestra</Badge>}
            {mostrarColaborador && descanso.es_propio && <Badge variant="outline">Tuyo</Badge>}
            <EstadoBadge estado={descanso.estado} />
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-6 lg:grid-cols-[minmax(0,28rem)_minmax(0,1fr)]">
        <CertificadoViewer descanso={descanso} />

        <div className="space-y-4">
          {mostrarColaborador && (
            <p className="text-sm">
              <strong>Periodo:</strong> <Periodo descanso={descanso} />
            </p>
          )}

          {enAnalisis && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              Analizando el documento con IA. Puede tardar hasta un par de minutos…
            </p>
          )}
          {descanso.ultimo_analisis ? (
            <AnalisisPanel analisis={descanso.ultimo_analisis} />
          ) : (
            !enAnalisis && (
              <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
                Este documento aún no se ha analizado con IA.
              </p>
            )
          )}

          {descanso.comentario_rrhh && (
            <div className="rounded-lg bg-muted p-3">
              <p className="text-sm font-medium">Comentario de RRHH</p>
              <p className="whitespace-pre-wrap text-sm text-muted-foreground">
                {descanso.comentario_rrhh}
              </p>
            </div>
          )}

          {acciones && <div className="flex flex-wrap gap-2 pt-1">{acciones}</div>}
        </div>
      </CardContent>
    </Card>
  );
}
