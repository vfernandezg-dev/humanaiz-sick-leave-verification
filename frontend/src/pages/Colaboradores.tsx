import { useState } from "react";
import { Search, Users } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { Paginacion } from "@/components/Paginacion";
import { AppShell } from "@/components/shell/AppShell";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Indicador } from "@/components/Indicador";
import { useColaboradores, useFacetas } from "@/hooks/queries";
import { useDebounce } from "@/hooks/useDebounce";
import { cn } from "@/lib/utils";

const POR_PAGINA = 50;
const TODOS = "todos";

interface Filtros {
  busqueda: string;
  area: string;
  contrato: string;
  categoria: string;
  activo: string;
}

const SIN_FILTROS: Filtros = { busqueda: "", area: TODOS, contrato: TODOS, categoria: TODOS, activo: TODOS };

function Filtro({
  id,
  etiqueta,
  valor,
  onCambio,
  opciones,
}: {
  id: string;
  etiqueta: string;
  valor: string;
  onCambio: (valor: string) => void;
  opciones: { valor: string; texto: string }[];
}) {
  return (
    <div>
      <Label htmlFor={id} className="sr-only">
        {etiqueta}
      </Label>
      <Select value={valor} onValueChange={(v) => v && onCambio(v)}>
        <SelectTrigger id={id} className={cn(valor === TODOS && "text-muted-foreground")}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={TODOS}>{etiqueta}: todas</SelectItem>
          {opciones.map((o) => (
            <SelectItem key={o.valor} value={o.valor}>
              {o.texto}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

const opciones = (valores: string[] | undefined) => (valores ?? []).map((v) => ({ valor: v, texto: v }));

export default function Colaboradores() {
  const [filtros, setFiltros] = useState<Filtros>(SIN_FILTROS);
  const [offset, setOffset] = useState(0);
  const busqueda = useDebounce(filtros.busqueda.trim());
  const { data: facetas } = useFacetas();
  const opcional = (valor: string) => (valor === TODOS ? undefined : valor);

  const { data, isLoading, isError, isFetching } = useColaboradores({
    q: busqueda || undefined,
    area_operacion: opcional(filtros.area),
    tipo_contrato: opcional(filtros.contrato),
    categoria: opcional(filtros.categoria),
    activo: filtros.activo === TODOS ? undefined : filtros.activo === "si",
    limit: POR_PAGINA,
    offset,
  });

  const cambiar = (campo: keyof Filtros) => (valor: string) => {
    setFiltros((actual) => ({ ...actual, [campo]: valor }));
    setOffset(0);
  };
  const colaboradores = data?.items ?? [];

  return (
    <AppShell>
      <PageHeader
        titulo="Colaboradores"
        descripcion="Padrón del personal, de solo lectura. En la demo todas las personas son ficticias."
      />

      <div className="mb-6 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <div className="relative sm:col-span-2 lg:col-span-1">
          <Label htmlFor="busqueda" className="sr-only">
            Buscar por DNI o nombre
          </Label>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input
            id="busqueda"
            maxLength={100}
            placeholder="DNI o nombre"
            className="pl-9"
            value={filtros.busqueda}
            onChange={(e) => cambiar("busqueda")(e.target.value)}
          />
        </div>
        <Filtro id="area" etiqueta="Área" valor={filtros.area} onCambio={cambiar("area")} opciones={opciones(facetas?.areas_operacion)} />
        <Filtro id="contrato" etiqueta="Contrato" valor={filtros.contrato} onCambio={cambiar("contrato")} opciones={opciones(facetas?.tipos_contrato)} />
        <Filtro id="categoria" etiqueta="Categoría" valor={filtros.categoria} onCambio={cambiar("categoria")} opciones={opciones(["A", "B", "C", "D"])} />
        <Filtro
          id="activo"
          etiqueta="Estado"
          valor={filtros.activo}
          onCambio={cambiar("activo")}
          opciones={[
            { valor: "si", texto: "Activos" },
            { valor: "no", texto: "Inactivos" },
          ]}
        />
      </div>

      {isError ? (
        <Alert variant="destructive">
          <AlertDescription>No se pudo cargar el padrón. Recarga la página.</AlertDescription>
        </Alert>
      ) : isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : colaboradores.length === 0 ? (
        <EmptyState icono={Users} titulo="Sin resultados" descripcion="Ningún colaborador coincide con los filtros." />
      ) : (
        <div className={cn("space-y-4 transition-opacity", isFetching && "opacity-70")}>
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Colaborador</TableHead>
                  <TableHead>Área</TableHead>
                  <TableHead className="hidden md:table-cell">Contrato</TableHead>
                  <TableHead>Sede</TableHead>
                  <TableHead className="hidden sm:table-cell">Cat.</TableHead>
                  <TableHead className="text-right">Estado</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {colaboradores.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell>
                      <p className="font-medium">
                        {c.apellidos}, {c.nombres}
                      </p>
                      <p className="text-xs text-muted-foreground">DNI {c.dni}</p>
                    </TableCell>
                    <TableCell>{c.area_operacion}</TableCell>
                    <TableCell className="hidden md:table-cell">{c.tipo_contrato}</TableCell>
                    <TableCell>{c.sede}</TableCell>
                    <TableCell className="hidden sm:table-cell">{c.categoria}</TableCell>
                    <TableCell className="text-right">
                      <Indicador tono={c.activo ? "ok" : "neutro"}>{c.activo ? "Activo" : "Inactivo"}</Indicador>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {data && (
            <Paginacion total={data.total} limit={data.limit} offset={data.offset} onCambio={setOffset} etiqueta="colaboradores" />
          )}
        </div>
      )}
    </AppShell>
  );
}
