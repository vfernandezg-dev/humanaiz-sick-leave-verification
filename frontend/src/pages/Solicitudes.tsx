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
import { useI18n } from "@/i18n/context";
import type { EstadoDescanso } from "@/lib/types";
import { cn } from "@/lib/utils";

const POR_PAGINA = 20;
type Filtro = EstadoDescanso | "todos";

export default function Solicitudes() {
  const { t } = useI18n();
  const ts = t.rrhh.solicitudes;
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
        titulo={ts.titulo}
        descripcion={ts.descripcion}
      />

      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <Segmentado
          etiqueta={ts.filtrarPorEstado}
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
                  {ts.pendientes}
                  {totalPendientes !== undefined && totalPendientes > 0 && (
                    <span className="rounded-full bg-amber-100 px-1.5 text-xs font-medium text-amber-900">
                      {totalPendientes}
                    </span>
                  )}
                </>
              ),
            },
            { valor: "Aprobado", texto: ts.aprobadas },
            { valor: "Rechazado", texto: ts.rechazadas },
            { valor: "todos", texto: ts.todas },
          ]}
        />
        <div className="grid grid-cols-2 gap-2 lg:w-96">
          <div className="relative">
            <Label htmlFor="filtro-dni" className="sr-only">
              {ts.buscarPorDni}
            </Label>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
            <Input
              id="filtro-dni"
              inputMode="numeric"
              maxLength={8}
              placeholder={ts.placeholderDni}
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
              {ts.buscarPorSede}
            </Label>
            <Input
              id="filtro-sede"
              maxLength={100}
              placeholder={ts.placeholderSede}
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
          <AlertDescription>{ts.errorCarga}</AlertDescription>
        </Alert>
      ) : descansos.length === 0 ? (
        <EmptyState
          icono={Inbox}
          titulo={buscando ? ts.sinResultados : ts.vacio[estado]}
          descripcion={buscando ? ts.sinCoincidencias : undefined}
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
              etiqueta={ts.plural}
            />
          )}
        </div>
      )}
    </AppShell>
  );
}
