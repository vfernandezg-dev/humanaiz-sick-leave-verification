import { useState } from "react";
import { Inbox, Search } from "lucide-react";
import { ListaDescansos } from "@/components/descanso/ListaDescansos";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { Paginacion } from "@/components/Paginacion";
import { Segmentado } from "@/components/Segmentado";
import { AppShell } from "@/components/shell/AppShell";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useDescansos } from "@/hooks/queries";
import { useDebounce } from "@/hooks/useDebounce";
import type { EstadoDescanso } from "@/lib/types";
import { cn } from "@/lib/utils";

const POR_PAGINA = 20;
type Filtro = EstadoDescanso | "todos";

const VACIO: Record<Filtro, string> = {
  Pendiente: "No hay solicitudes pendientes. Todo al día.",
  Aprobado: "Todavía no hay descansos aprobados.",
  Rechazado: "Todavía no hay descansos rechazados.",
  todos: "Aún no hay solicitudes registradas.",
};

export default function Solicitudes() {
  const [estado, setEstado] = useState<Filtro>("Pendiente");
  const [dni, setDni] = useState("");
  const [sede, setSede] = useState("");
  const [offset, setOffset] = useState(0);
  const dniFiltro = useDebounce(dni);
  const sedeFiltro = useDebounce(sede.trim());
  const buscando = Boolean(dniFiltro || sedeFiltro);

  const { data, isLoading, isError, isFetching } = useDescansos({
    estado: estado === "todos" ? undefined : estado,
    dni: dniFiltro || undefined,
    sede: sedeFiltro || undefined,
    limit: POR_PAGINA,
    offset,
  });
  const pendientes = useDescansos({ estado: "Pendiente", limit: 1, offset: 0 });
  const totalPendientes = pendientes.data?.total;
  const descansos = data?.items ?? [];

  return (
    <AppShell>
      <PageHeader
        titulo="Solicitudes"
        descripcion="Certificados de todo el equipo. Abre uno para ver el documento, pedir una lectura con IA y decidir."
      />

      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <Segmentado
          etiqueta="Filtrar por estado"
          valor={estado}
          onCambio={(valor) => {
            setEstado(valor);
            setOffset(0);
          }}
          opciones={[
            {
              valor: "Pendiente",
              texto: (
                <>
                  Pendientes
                  {totalPendientes !== undefined && totalPendientes > 0 && (
                    <span className="rounded-full bg-amber-100 px-1.5 text-xs font-medium text-amber-900">
                      {totalPendientes}
                    </span>
                  )}
                </>
              ),
            },
            { valor: "Aprobado", texto: "Aprobadas" },
            { valor: "Rechazado", texto: "Rechazadas" },
            { valor: "todos", texto: "Todas" },
          ]}
        />
        <div className="grid grid-cols-2 gap-2 lg:w-96">
          <div className="relative">
            <Label htmlFor="filtro-dni" className="sr-only">
              Buscar por DNI
            </Label>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
            <Input
              id="filtro-dni"
              inputMode="numeric"
              maxLength={8}
              placeholder="DNI"
              className="pl-9"
              value={dni}
              onChange={(e) => {
                setDni(e.target.value.replace(/\D/g, ""));
                setOffset(0);
              }}
            />
          </div>
          <div>
            <Label htmlFor="filtro-sede" className="sr-only">
              Buscar por sede
            </Label>
            <Input
              id="filtro-sede"
              maxLength={100}
              placeholder="Sede"
              value={sede}
              onChange={(e) => {
                setSede(e.target.value);
                setOffset(0);
              }}
            />
          </div>
        </div>
      </div>

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : isError ? (
        <Alert variant="destructive">
          <AlertDescription>No se pudieron cargar las solicitudes. Recarga la página.</AlertDescription>
        </Alert>
      ) : descansos.length === 0 ? (
        <EmptyState
          icono={Inbox}
          titulo={buscando ? "Sin resultados" : VACIO[estado]}
          descripcion={buscando ? "Ninguna solicitud coincide con la búsqueda." : undefined}
        />
      ) : (
        <div className={cn("space-y-4 transition-opacity", isFetching && "opacity-70")}>
          <ListaDescansos descansos={descansos} vista="rrhh" desde="/rrhh/descansos" />
          {data && (
            <Paginacion
              total={data.total}
              limit={data.limit}
              offset={data.offset}
              onCambio={setOffset}
              etiqueta="solicitudes"
            />
          )}
        </div>
      )}
    </AppShell>
  );
}
