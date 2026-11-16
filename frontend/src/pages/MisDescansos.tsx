import { Link } from "react-router-dom";
import { Inbox, Plus } from "lucide-react";
import { useAuth } from "@/auth/context";
import { ListaDescansos } from "@/components/descanso/ListaDescansos";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { AppShell } from "@/components/shell/AppShell";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useMisDescansos } from "@/hooks/queries";
import { useI18n } from "@/i18n/context";

export default function MisDescansos() {
  const { usuario } = useAuth();
  const { t } = useI18n();
  const m = t.inicio.mis;
  const { data, isLoading, isError } = useMisDescansos({ limit: 100 });
  const sinFicha = !usuario?.colaborador;
  const descansos = data?.items ?? [];

  const registrar = (
    <Button asChild className="gap-2">
      <Link to="/descansos/nuevo">
        <Plus className="h-4 w-4" aria-hidden />
        {m.registrar}
      </Link>
    </Button>
  );

  return (
    <AppShell>
      <PageHeader
        titulo={m.titulo}
        descripcion={m.descripcion}
        accion={!sinFicha && descansos.length > 0 ? registrar : undefined}
      />

      {sinFicha && (
        <Alert className="mb-6">
          <AlertDescription>{m.sinFicha}</AlertDescription>
        </Alert>
      )}

      {isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : isError ? (
        <Alert variant="destructive">
          <AlertDescription>{m.error}</AlertDescription>
        </Alert>
      ) : descansos.length === 0 ? (
        <EmptyState
          icono={Inbox}
          titulo={m.vacio}
          descripcion={m.vacioDetalle}
          accion={!sinFicha ? registrar : undefined}
        />
      ) : (
        <ListaDescansos descansos={descansos} vista="propia" desde="/descansos" />
      )}
    </AppShell>
  );
}
