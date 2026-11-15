import { useState } from "react";
import { Filter, Search } from "lucide-react";
import { Layout } from "@/components/Layout";
import { Paginacion } from "@/components/Paginacion";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useColaboradores, useFacetas } from "@/hooks/queries";
import { useDebounce } from "@/hooks/useDebounce";
import { formatoFecha } from "@/lib/fechas";

const POR_PAGINA = 50;
const TODOS = "todos";

const COLOR_CATEGORIA: Record<string, string> = {
  A: "bg-success hover:bg-success",
  B: "bg-primary hover:bg-primary",
  C: "bg-warning hover:bg-warning",
  D: "bg-destructive hover:bg-destructive",
};

interface Filtros {
  busqueda: string;
  categoria: string;
  area: string;
  contrato: string;
  sexo: string;
  activo: string;
}

const SIN_FILTROS: Filtros = {
  busqueda: "",
  categoria: TODOS,
  area: TODOS,
  contrato: TODOS,
  sexo: TODOS,
  activo: TODOS,
};

function opcional(valor: string): string | undefined {
  return valor === TODOS ? undefined : valor;
}

interface SelectorProps {
  id: string;
  etiqueta: string;
  valor: string;
  onCambio: (valor: string) => void;
  opciones: { valor: string; texto: string }[];
  todos: string;
}

function Selector({ id, etiqueta, valor, onCambio, opciones, todos }: SelectorProps) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{etiqueta}</Label>
      <Select value={valor} onValueChange={onCambio}>
        <SelectTrigger id={id}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={TODOS}>{todos}</SelectItem>
          {opciones.map((opcion) => (
            <SelectItem key={opcion.valor} value={opcion.valor}>
              {opcion.texto}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

const comoOpciones = (valores: string[] | undefined) =>
  (valores ?? []).map((valor) => ({ valor, texto: valor }));

export default function RRHHColaboradores() {
  const [filtros, setFiltros] = useState<Filtros>(SIN_FILTROS);
  const [offset, setOffset] = useState(0);
  const busqueda = useDebounce(filtros.busqueda.trim());
  const { data: facetas } = useFacetas();

  const { data, isLoading, isError, isFetching } = useColaboradores({
    q: busqueda || undefined,
    categoria: opcional(filtros.categoria),
    area_operacion: opcional(filtros.area),
    tipo_contrato: opcional(filtros.contrato),
    sexo: opcional(filtros.sexo),
    activo: filtros.activo === TODOS ? undefined : filtros.activo === "si",
    limit: POR_PAGINA,
    offset,
  });

  const cambiar = (campo: keyof Filtros) => (valor: string) => {
    setFiltros((actuales) => ({ ...actuales, [campo]: valor }));
    setOffset(0);
  };

  const colaboradores = data?.items ?? [];

  return (
    <Layout>
      <div>
        <h1 className="text-3xl font-bold">Padrón de colaboradores</h1>
        <p className="mt-1 text-muted-foreground">Consulta y filtra la información del personal.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Filter className="h-5 w-5" aria-hidden />
            Filtros y búsqueda
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="busqueda" className="flex items-center gap-2">
              <Search className="h-4 w-4" aria-hidden />
              Buscar
            </Label>
            <Input
              id="busqueda"
              maxLength={100}
              placeholder="DNI, nombres o apellidos"
              value={filtros.busqueda}
              onChange={(e) => cambiar("busqueda")(e.target.value)}
            />
          </div>
          <Selector
            id="categoria"
            etiqueta="Categoría"
            todos="Todas"
            valor={filtros.categoria}
            onCambio={cambiar("categoria")}
            opciones={comoOpciones(["A", "B", "C", "D"])}
          />
          <Selector
            id="area"
            etiqueta="Área de operación"
            todos="Todas"
            valor={filtros.area}
            onCambio={cambiar("area")}
            opciones={comoOpciones(facetas?.areas_operacion)}
          />
          <Selector
            id="contrato"
            etiqueta="Tipo de contrato"
            todos="Todos"
            valor={filtros.contrato}
            onCambio={cambiar("contrato")}
            opciones={comoOpciones(facetas?.tipos_contrato)}
          />
          <Selector
            id="sexo"
            etiqueta="Sexo"
            todos="Todos"
            valor={filtros.sexo}
            onCambio={cambiar("sexo")}
            opciones={[
              { valor: "M", texto: "Masculino" },
              { valor: "F", texto: "Femenino" },
            ]}
          />
          <Selector
            id="activo"
            etiqueta="Estado"
            todos="Todos"
            valor={filtros.activo}
            onCambio={cambiar("activo")}
            opciones={[
              { valor: "si", texto: "Activos" },
              { valor: "no", texto: "Inactivos" },
            ]}
          />
        </CardContent>
      </Card>

      {isError ? (
        <Alert variant="destructive">
          <AlertDescription>No se pudo cargar el padrón. Recarga la página.</AlertDescription>
        </Alert>
      ) : (
        <Card>
          <CardContent className={isFetching && !isLoading ? "p-0 opacity-70" : "p-0"}>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>DNI</TableHead>
                    <TableHead>Apellidos</TableHead>
                    <TableHead>Nombres</TableHead>
                    <TableHead>F. nacimiento</TableHead>
                    <TableHead>Categoría</TableHead>
                    <TableHead>Sexo</TableHead>
                    <TableHead>Celular</TableHead>
                    <TableHead>Área</TableHead>
                    <TableHead>Contrato</TableHead>
                    <TableHead>Sede</TableHead>
                    <TableHead>Estado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading ? (
                    <TableRow>
                      <TableCell colSpan={11}>
                        <Skeleton className="h-24 w-full" />
                      </TableCell>
                    </TableRow>
                  ) : colaboradores.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={11} className="py-10 text-center text-muted-foreground">
                        Ningún colaborador coincide con los filtros.
                      </TableCell>
                    </TableRow>
                  ) : (
                    colaboradores.map((c) => (
                      <TableRow key={c.id}>
                        <TableCell className="font-medium">{c.dni}</TableCell>
                        <TableCell>{c.apellidos}</TableCell>
                        <TableCell>{c.nombres}</TableCell>
                        <TableCell>{formatoFecha(c.fecha_nacimiento)}</TableCell>
                        <TableCell>
                          <Badge className={COLOR_CATEGORIA[c.categoria] ?? "bg-muted"}>
                            {c.categoria}
                          </Badge>
                        </TableCell>
                        <TableCell>{c.sexo === "M" ? "Masculino" : "Femenino"}</TableCell>
                        <TableCell>{c.celular ?? "—"}</TableCell>
                        <TableCell>{c.area_operacion}</TableCell>
                        <TableCell>{c.tipo_contrato}</TableCell>
                        <TableCell>{c.sede}</TableCell>
                        <TableCell>
                          <Badge variant={c.activo ? "default" : "secondary"}>
                            {c.activo ? "Activo" : "Inactivo"}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {data && (
        <Paginacion
          total={data.total}
          limit={data.limit}
          offset={data.offset}
          onCambio={setOffset}
          etiqueta="colaboradores"
        />
      )}
    </Layout>
  );
}
