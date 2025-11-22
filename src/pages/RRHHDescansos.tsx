import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/hooks/useAuth";
import { useWebhook } from "@/hooks/useWebhook";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Check, X, Filter } from "lucide-react";

type EstadoDescanso = "Pendiente" | "Aprobado" | "Rechazado";

interface DescansoMedico {
  id: string;
  fecha_inicio: string;
  fecha_fin: string;
  estado: EstadoDescanso;
  comentario_rrhh: string | null;
  imagen_url: string | null;
  created_at: string;
  sede: string;
  colaboradores: {
    dni: string;
    nombres: string;
    apellidos: string;
  };
}

export default function RRHHDescansos() {
  const { user, role, loading } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { sendWebhook } = useWebhook();
  const [descansos, setDescansos] = useState<DescansoMedico[]>([]);
  const [selectedDescanso, setSelectedDescanso] = useState<DescansoMedico | null>(null);
  const [comentario, setComentario] = useState("");
  const [filters, setFilters] = useState({
    estado: "all",
    dni: "",
    sede: "",
  });

  useEffect(() => {
    if (!loading && (!user || role !== "analista_rrhh")) {
      navigate("/");
    } else if (user && role === "analista_rrhh") {
      fetchDescansos();
    }
  }, [user, role, loading, navigate]);

  const fetchDescansos = async () => {
    let query = supabase
      .from("descansos_medicos")
      .select(`
        *,
        colaboradores (
          dni,
          nombres,
          apellidos
        )
      `)
      .order("created_at", { ascending: false });

    if (filters.estado !== "all") {
      query = query.eq("estado", filters.estado as EstadoDescanso);
    }

    const { data, error } = await query;

    if (error) {
      toast({
        title: "Error",
        description: "No se pudieron cargar los descansos",
        variant: "destructive",
      });
    } else {
      let filteredData = data || [];
      
      if (filters.dni) {
        filteredData = filteredData.filter((d: any) => 
          d.colaboradores?.dni.includes(filters.dni)
        );
      }
      
      if (filters.sede) {
        filteredData = filteredData.filter((d: any) => 
          d.sede.toLowerCase().includes(filters.sede.toLowerCase())
        );
      }
      
      setDescansos(filteredData);
    }
  };

  useEffect(() => {
    if (role === "analista_rrhh") {
      fetchDescansos();
    }
  }, [filters]);

  const handleUpdateEstado = async (id: string, nuevoEstado: EstadoDescanso) => {
    const { error } = await supabase
      .from("descansos_medicos")
      .update({
        estado: nuevoEstado,
        comentario_rrhh: comentario || null,
      })
      .eq("id", id);

    if (error) {
      toast({
        title: "Error",
        description: "No se pudo actualizar el descanso",
        variant: "destructive",
      });
    } else {
      toast({
        title: "Éxito",
        description: `Descanso ${nuevoEstado.toLowerCase()} correctamente`,
      });

      // Send webhook to n8n
      if (selectedDescanso) {
        await sendWebhook('descanso_medico_actualizado', {
          descanso_id: selectedDescanso.id,
          colaborador_id: selectedDescanso.colaboradores.dni,
          dni: selectedDescanso.colaboradores.dni,
          nombre_completo: `${selectedDescanso.colaboradores.apellidos}, ${selectedDescanso.colaboradores.nombres}`,
          fecha_inicio: selectedDescanso.fecha_inicio,
          fecha_fin: selectedDescanso.fecha_fin,
          sede: selectedDescanso.sede,
          estado_anterior: selectedDescanso.estado,
          estado_nuevo: nuevoEstado,
          comentario_rrhh: comentario || null
        });
      }

      setSelectedDescanso(null);
      setComentario("");
      fetchDescansos();
    }
  };

  const getEstadoBadge = (estado: EstadoDescanso) => {
    switch (estado) {
      case "Aprobado":
        return <Badge className="bg-success">Aprobado</Badge>;
      case "Rechazado":
        return <Badge variant="destructive">Rechazado</Badge>;
      default:
        return <Badge variant="secondary">Pendiente</Badge>;
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
          <h1 className="text-3xl font-bold">Gestión de Descansos Médicos</h1>
          <p className="text-muted-foreground mt-1">
            Aprueba o rechaza las solicitudes de descanso médico
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Filtros
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label>Estado</Label>
              <Select value={filters.estado} onValueChange={(v) => setFilters({ ...filters, estado: v })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="Pendiente">Pendiente</SelectItem>
                  <SelectItem value="Aprobado">Aprobado</SelectItem>
                  <SelectItem value="Rechazado">Rechazado</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>DNI</Label>
              <Input
                placeholder="Buscar por DNI"
                value={filters.dni}
                onChange={(e) => setFilters({ ...filters, dni: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Sede</Label>
              <Input
                placeholder="Buscar por sede"
                value={filters.sede}
                onChange={(e) => setFilters({ ...filters, sede: e.target.value })}
              />
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-4">
          {descansos.map((descanso) => (
            <Card key={descanso.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>
                      {descanso.colaboradores?.nombres} {descanso.colaboradores?.apellidos}
                    </CardTitle>
                    <CardDescription>DNI: {descanso.colaboradores?.dni}</CardDescription>
                  </div>
                  {getEstadoBadge(descanso.estado)}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-2 text-sm">
                  <p><strong>Fecha Inicio:</strong> {new Date(descanso.fecha_inicio).toLocaleDateString()}</p>
                  <p><strong>Fecha Fin:</strong> {new Date(descanso.fecha_fin).toLocaleDateString()}</p>
                  <p><strong>Sede:</strong> {descanso.sede}</p>
                  <p><strong>Registrado:</strong> {new Date(descanso.created_at).toLocaleString()}</p>
                </div>

                {descanso.imagen_url && (
                  <div>
                    <p className="text-sm font-medium mb-2">Certificado Médico:</p>
                    <img 
                      src={descanso.imagen_url} 
                      alt="Certificado médico" 
                      className="max-w-md rounded-lg border"
                    />
                  </div>
                )}

                {descanso.comentario_rrhh && (
                  <div className="p-3 bg-muted rounded-lg">
                    <p className="text-sm font-medium">Comentario:</p>
                    <p className="text-sm text-muted-foreground">{descanso.comentario_rrhh}</p>
                  </div>
                )}

                {descanso.estado === "Pendiente" && (
                  <div className="flex gap-2 pt-2">
                    <Button
                      variant="default"
                      className="gap-2 bg-success hover:bg-success/90"
                      onClick={() => setSelectedDescanso(descanso)}
                    >
                      <Check className="h-4 w-4" />
                      Aprobar
                    </Button>
                    <Button
                      variant="destructive"
                      className="gap-2"
                      onClick={() => setSelectedDescanso(descanso)}
                    >
                      <X className="h-4 w-4" />
                      Rechazar
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

        <Dialog open={!!selectedDescanso} onOpenChange={() => setSelectedDescanso(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Actualizar Descanso Médico</DialogTitle>
              <DialogDescription>
                Agrega un comentario (opcional) y confirma la acción
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="comentario">Comentario</Label>
                <Textarea
                  id="comentario"
                  placeholder="Agregar comentario..."
                  value={comentario}
                  onChange={(e) => setComentario(e.target.value)}
                  rows={4}
                />
              </div>
              <div className="flex gap-2">
                <Button
                  variant="default"
                  className="flex-1 bg-success hover:bg-success/90"
                  onClick={() => handleUpdateEstado(selectedDescanso!.id, "Aprobado")}
                >
                  Aprobar
                </Button>
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={() => handleUpdateEstado(selectedDescanso!.id, "Rechazado")}
                >
                  Rechazar
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
