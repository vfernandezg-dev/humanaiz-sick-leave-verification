import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/hooks/useAuth";
import { supabase } from "@/integrations/supabase/client";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Filter, Search } from "lucide-react";

interface Colaborador {
  id: string;
  dni: string;
  apellidos: string;
  nombres: string;
  fecha_nacimiento: string;
  categoria: string;
  sexo: string;
  celular: string | null;
  area_operacion: string;
  tipo_contrato: string;
  sede: string;
  activo: boolean;
}

export default function RRHHColaboradores() {
  const { user, role, loading } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [colaboradores, setColaboradores] = useState<Colaborador[]>([]);
  const [filteredColaboradores, setFilteredColaboradores] = useState<Colaborador[]>([]);
  
  const [filters, setFilters] = useState({
    busqueda: "",
    categoria: "all",
    area: "all",
    contrato: "all",
    sexo: "all",
    activo: "all",
  });

  useEffect(() => {
    if (!loading && (!user || role !== "analista_rrhh")) {
      navigate("/");
    } else if (user && role === "analista_rrhh") {
      fetchColaboradores();
    }
  }, [user, role, loading, navigate]);

  const fetchColaboradores = async () => {
    const { data, error } = await supabase
      .from("colaboradores")
      .select("*")
      .order("apellidos", { ascending: true });

    if (error) {
      toast({
        title: "Error",
        description: "No se pudieron cargar los colaboradores",
        variant: "destructive",
      });
    } else {
      setColaboradores(data || []);
      setFilteredColaboradores(data || []);
    }
  };

  useEffect(() => {
    let filtered = [...colaboradores];

    // Filter by search
    if (filters.busqueda) {
      const searchLower = filters.busqueda.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.dni.includes(filters.busqueda) ||
          c.nombres.toLowerCase().includes(searchLower) ||
          c.apellidos.toLowerCase().includes(searchLower)
      );
    }

    // Filter by category
    if (filters.categoria !== "all") {
      filtered = filtered.filter((c) => c.categoria === filters.categoria);
    }

    // Filter by area
    if (filters.area !== "all") {
      filtered = filtered.filter((c) => c.area_operacion === filters.area);
    }

    // Filter by contract type
    if (filters.contrato !== "all") {
      filtered = filtered.filter((c) => c.tipo_contrato === filters.contrato);
    }

    // Filter by sex
    if (filters.sexo !== "all") {
      filtered = filtered.filter((c) => c.sexo === filters.sexo);
    }

    // Filter by active status
    if (filters.activo !== "all") {
      filtered = filtered.filter((c) => c.activo === (filters.activo === "true"));
    }

    setFilteredColaboradores(filtered);
  }, [filters, colaboradores]);

  const uniqueAreas = Array.from(new Set(colaboradores.map((c) => c.area_operacion)));
  const uniqueContratos = Array.from(new Set(colaboradores.map((c) => c.tipo_contrato)));

  const getCategoriaColor = (categoria: string) => {
    switch (categoria) {
      case "A":
        return "bg-success";
      case "B":
        return "bg-primary";
      case "C":
        return "bg-warning";
      case "D":
        return "bg-destructive";
      default:
        return "bg-muted";
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Cargando...</p>
      </div>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Panel Maestro de Colaboradores</h1>
          <p className="text-muted-foreground mt-1">
            Consulta y filtra información de colaboradores
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Filtros y Búsqueda
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Search className="h-4 w-4" />
                  Buscar
                </Label>
                <Input
                  placeholder="DNI, nombres o apellidos"
                  value={filters.busqueda}
                  onChange={(e) => setFilters({ ...filters, busqueda: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label>Categoría</Label>
                <Select value={filters.categoria} onValueChange={(v) => setFilters({ ...filters, categoria: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas</SelectItem>
                    <SelectItem value="A">A</SelectItem>
                    <SelectItem value="B">B</SelectItem>
                    <SelectItem value="C">C</SelectItem>
                    <SelectItem value="D">D</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Área de Operación</Label>
                <Select value={filters.area} onValueChange={(v) => setFilters({ ...filters, area: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas</SelectItem>
                    {uniqueAreas.map((area) => (
                      <SelectItem key={area} value={area}>
                        {area}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Tipo de Contrato</Label>
                <Select value={filters.contrato} onValueChange={(v) => setFilters({ ...filters, contrato: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    {uniqueContratos.map((contrato) => (
                      <SelectItem key={contrato} value={contrato}>
                        {contrato}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Sexo</Label>
                <Select value={filters.sexo} onValueChange={(v) => setFilters({ ...filters, sexo: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="M">Masculino</SelectItem>
                    <SelectItem value="F">Femenino</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Estado</Label>
                <Select value={filters.activo} onValueChange={(v) => setFilters({ ...filters, activo: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="true">Activos</SelectItem>
                    <SelectItem value="false">Inactivos</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="text-sm text-muted-foreground">
              Mostrando {filteredColaboradores.length} de {colaboradores.length} colaboradores
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>DNI</TableHead>
                    <TableHead>Apellidos</TableHead>
                    <TableHead>Nombres</TableHead>
                    <TableHead>F. Nacimiento</TableHead>
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
                  {filteredColaboradores.map((colaborador) => (
                    <TableRow key={colaborador.id}>
                      <TableCell className="font-medium">{colaborador.dni}</TableCell>
                      <TableCell>{colaborador.apellidos}</TableCell>
                      <TableCell>{colaborador.nombres}</TableCell>
                      <TableCell>{new Date(colaborador.fecha_nacimiento).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <Badge className={getCategoriaColor(colaborador.categoria)}>
                          {colaborador.categoria}
                        </Badge>
                      </TableCell>
                      <TableCell>{colaborador.sexo === "M" ? "Masculino" : "Femenino"}</TableCell>
                      <TableCell>{colaborador.celular || "-"}</TableCell>
                      <TableCell>{colaborador.area_operacion}</TableCell>
                      <TableCell>{colaborador.tipo_contrato}</TableCell>
                      <TableCell>{colaborador.sede}</TableCell>
                      <TableCell>
                        <Badge variant={colaborador.activo ? "default" : "secondary"}>
                          {colaborador.activo ? "Activo" : "Inactivo"}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
