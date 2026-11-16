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

export default function MisDescansos() {
  const { usuario } = useAuth();
  const { data, isLoading, isError } = useMisDescansos({ limit: 100 });
  const sinFicha = !usuario?.colaborador;
  const descansos = data?.items ?? [];

  const registrar = (
    <Button asChild className="gap-2">
      <Link to="/descansos/nuevo">
        <Plus className="h-4 w-4" aria-hidden />
        Registrar descanso
      </Link>
    </Button>
  );

  return (
    <AppShell>
      <PageHeader
        titulo="Mis descansos"
        descripcion="Tus certificados registrados. Abre uno para ver el documento, la lectura con IA y la decisión de RRHH."
        accion={!sinFicha && descansos.length > 0 ? registrar : undefined}
      />

      {sinFicha && (
        <Alert className="mb-6">
          <AlertDescription>
            Tu cuenta no está vinculada a una ficha de colaborador, así que no puedes registrar
            descansos.
          </AlertDescription>
        </Alert>
      )}

      {isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : isError ? (
        <Alert variant="destructive">
          <AlertDescription>No se pudieron cargar tus descansos. Recarga la página.</AlertDescription>
        </Alert>
      ) : descansos.length === 0 ? (
        <EmptyState
          icono={Inbox}
          titulo="Aún no registras descansos"
          descripcion="Sube una foto o un PDF de tu certificado. Recuerda: es una demo, usa solo documentos de prueba."
          accion={!sinFicha ? registrar : undefined}
        />
      ) : (
        <ListaDescansos descansos={descansos} vista="propia" desde="/descansos" />
      )}
    </AppShell>
  );
}
