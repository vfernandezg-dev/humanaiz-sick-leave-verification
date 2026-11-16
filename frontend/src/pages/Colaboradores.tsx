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
import { useI18n } from "@/i18n/context";
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
  const { t } = useI18n();
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
          <SelectItem value={TODOS}>{t.rrhh.colaboradores.todas(etiqueta)}</SelectItem>
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
  const { t } = useI18n();
  const tc = t.rrhh.colaboradores;
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
        titulo={tc.titulo}
        descripcion={tc.descripcion}
      />

      <div className="mb-6 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <div className="relative sm:col-span-2 lg:col-span-1">
          <Label htmlFor="busqueda" className="sr-only">
            {tc.buscar}
          </Label>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input
            id="busqueda"
            maxLength={100}
            placeholder={tc.placeholderBuscar}
            className="pl-9"
            value={filtros.busqueda}
            onChange={(e) => cambiar("busqueda")(e.target.value)}
          />
        </div>
        <Filtro id="area" etiqueta={tc.filtroArea} valor={filtros.area} onCambio={cambiar("area")} opciones={opciones(facetas?.areas_operacion)} />
        <Filtro id="contrato" etiqueta={tc.filtroContrato} valor={filtros.contrato} onCambio={cambiar("contrato")} opciones={opciones(facetas?.tipos_contrato)} />
        <Filtro id="categoria" etiqueta={tc.filtroCategoria} valor={filtros.categoria} onCambio={cambiar("categoria")} opciones={opciones(["A", "B", "C", "D"])} />
        <Filtro
          id="activo"
          etiqueta={tc.filtroEstado}
          valor={filtros.activo}
          onCambio={cambiar("activo")}
          opciones={[
            { valor: "si", texto: tc.activos },
            { valor: "no", texto: tc.inactivos },
          ]}
        />
      </div>

      {isError ? (
        <Alert variant="destructive">
          <AlertDescription>{tc.errorCarga}</AlertDescription>
        </Alert>
      ) : isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : colaboradores.length === 0 ? (
        <EmptyState icono={Users} titulo={tc.sinResultados} descripcion={tc.sinCoincidencias} />
      ) : (
        <div className={cn("space-y-4 transition-opacity", isFetching && "opacity-70")}>
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>{tc.columnas.colaborador}</TableHead>
                  <TableHead>{tc.columnas.area}</TableHead>
                  <TableHead className="hidden md:table-cell">{tc.columnas.contrato}</TableHead>
                  <TableHead>{tc.columnas.sede}</TableHead>
                  <TableHead className="hidden sm:table-cell">{tc.columnas.categoria}</TableHead>
                  <TableHead className="text-right">{tc.columnas.estado}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {colaboradores.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell>
                      <p className="font-medium">
                        {c.apellidos}, {c.nombres}
                      </p>
                      <p className="text-xs text-muted-foreground">{tc.dni(c.dni)}</p>
                    </TableCell>
                    <TableCell>{c.area_operacion}</TableCell>
                    <TableCell className="hidden md:table-cell">{c.tipo_contrato}</TableCell>
                    <TableCell>{c.sede}</TableCell>
                    <TableCell className="hidden sm:table-cell">{c.categoria}</TableCell>
                    <TableCell className="text-right">
                      <Indicador tono={c.activo ? "ok" : "neutro"}>{c.activo ? tc.activo : tc.inactivo}</Indicador>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {data && (
            <Paginacion total={data.total} limit={data.limit} offset={data.offset} onCambio={setOffset} etiqueta={tc.plural} />
          )}
        </div>
      )}
    </AppShell>
  );
}
