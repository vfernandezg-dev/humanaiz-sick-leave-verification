import { Link } from "react-router-dom";
import { ArrowRight, BookOpen, Inbox, KeyRound, Plus } from "lucide-react";
import { useAuth } from "@/auth/context";
import { ListaDescansos } from "@/components/descanso/ListaDescansos";
import { EmptyState } from "@/components/EmptyState";
import { AppShell } from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useDescansos, useMisDescansos } from "@/hooks/queries";
import { useI18n } from "@/i18n/context";
import { useLlm } from "@/llm/context";
import type { EstadoDescanso } from "@/lib/types";

const RECIENTES = 3;

function Cifra({ valor, etiqueta }: { valor: number | undefined; etiqueta: string }) {
  return (
    <div className="rounded-lg border p-4">
      <p className="text-2xl font-semibold tabular-nums">{valor ?? "—"}</p>
      <p className="text-xs text-muted-foreground">{etiqueta}</p>
    </div>
  );
}

export default function Inicio() {
  const { usuario, esRRHH } = useAuth();
  const { credencial, abrir } = useLlm();
  const { t } = useI18n();
  const i = t.inicio.inicio;
  const mios = useMisDescansos({ limit: 100 });
  const pendientesRRHH = useDescansos(
    { estado: "Pendiente", limit: 1, offset: 0 },
    { enabled: esRRHH },
  );
  const sinFicha = !usuario?.colaborador;

  const items = mios.data?.items ?? [];
  const cuenta = (estado: EstadoDescanso) =>
    mios.data ? items.filter((d) => d.estado === estado).length : undefined;

  return (
    <AppShell>
      <div className="space-y-10">
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
            {usuario ? t.comun.rol[usuario.role] : ""}
          </p>
          <h1 className="text-2xl font-semibold tracking-tight">
            {usuario ? `${usuario.nombres} ${usuario.apellidos}` : i.tituloSinUsuario}
          </h1>
          <p className="text-sm text-muted-foreground">
            {esRRHH ? i.descripcionRRHH : i.descripcionColaborador}
          </p>
        </div>

        {esRRHH && (
          <section className="flex flex-col gap-4 rounded-lg border p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-accent text-accent-foreground">
                <Inbox className="h-5 w-5" aria-hidden />
              </span>
              <div>
                <p className="font-medium">
                  {pendientesRRHH.data ? i.pendientes(pendientesRRHH.data.total) : i.solicitudesEquipo}
                </p>
                <p className="text-sm text-muted-foreground">{i.esperanDecision}</p>
              </div>
            </div>
            <Button asChild className="gap-2">
              <Link to="/rrhh/descansos">
                {i.revisar}
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
            </Button>
          </section>
        )}

        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <h2 className="text-base font-semibold">{i.misDescansos}</h2>
            {!sinFicha && (
              <Button asChild size="sm" className="gap-2">
                <Link to="/descansos/nuevo">
                  <Plus className="h-4 w-4" aria-hidden />
                  {i.registrar}
                </Link>
              </Button>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <Cifra valor={cuenta("Pendiente")} etiqueta={i.cifras.Pendiente} />
            <Cifra valor={cuenta("Aprobado")} etiqueta={i.cifras.Aprobado} />
            <Cifra valor={cuenta("Rechazado")} etiqueta={i.cifras.Rechazado} />
          </div>

          {mios.isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : items.length === 0 ? (
            <EmptyState
              icono={Inbox}
              titulo={i.vacio}
              descripcion={sinFicha ? i.sinFicha : i.primerCertificado}
            />
          ) : (
            <>
              <ListaDescansos descansos={items.slice(0, RECIENTES)} vista="propia" desde="/" />
              {items.length > RECIENTES && (
                <Link to="/descansos" className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
                  {i.verTodos(items.length)}
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                </Link>
              )}
            </>
          )}
        </section>

        <section className="grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={abrir}
            className="flex items-start gap-3 rounded-lg border p-4 text-left transition-colors hover:bg-muted/50 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring"
          >
            <KeyRound className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" aria-hidden />
            <span className="space-y-0.5">
              <span className="block text-sm font-medium">
                {i.claveIA(Boolean(credencial))}
              </span>
              <span className="block text-xs leading-5 text-muted-foreground">
                {credencial ? i.claveLista : i.claveOpcional}
              </span>
            </span>
          </button>
          <Link
            to="/como-funciona"
            className="flex items-start gap-3 rounded-lg border p-4 transition-colors hover:bg-muted/50 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring"
          >
            <BookOpen className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" aria-hidden />
            <span className="space-y-0.5">
              <span className="block text-sm font-medium">{i.comoFunciona}</span>
              <span className="block text-xs leading-5 text-muted-foreground">
                {i.comoFuncionaDetalle}
              </span>
            </span>
          </Link>
        </section>
      </div>
    </AppShell>
  );
}
