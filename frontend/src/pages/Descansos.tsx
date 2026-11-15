import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/hooks/useAuth";
import { useWebhook } from "@/hooks/useWebhook";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Plus, Calendar, FileText } from "lucide-react";

interface DescansoMedico {
  id: string;
  fecha_inicio: string;
  fecha_fin: string;
  estado: string;
  comentario_rrhh: string | null;
  imagen_url: string | null;
  created_at: string;
  sede: string;
}

export default function Descansos() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { sendWebhook } = useWebhook();
  const [descansos, setDescansos] = useState<DescansoMedico[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  
  const [formData, setFormData] = useState({
    sede: "",
    imagen: null as File | null,
  });

  useEffect(() => {
    if (!loading && !user) {
      navigate("/auth");
    } else if (user) {
      fetchDescansos();
    }
  }, [user, loading, navigate]);

  const fetchDescansos = async () => {
    const { data, error } = await supabase
      .from("descansos_medicos")
      .select("*")
      .eq("user_id", user?.id)
      .order("created_at", { ascending: false });

    if (error) {
      toast({
        title: "Error",
        description: "No se pudieron cargar los descansos",
        variant: "destructive",
      });
    } else {
      setDescansos(data || []);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploading(true);

    try {
      let imagenUrl = null;

      // Upload image if provided
      if (formData.imagen) {
        const fileExt = formData.imagen.name.split(".").pop();
        const fileName = `${user?.id}/${Date.now()}.${fileExt}`;
        
        const { error: uploadError } = await supabase.storage
          .from("certificados-medicos")
          .upload(fileName, formData.imagen);

        if (uploadError) throw uploadError;

        const { data: { publicUrl } } = supabase.storage
          .from("certificados-medicos")
          .getPublicUrl(fileName);
        
        imagenUrl = publicUrl;
      }

      // Get colaborador_id
      const { data: colaboradorData, error: colaboradorError } = await supabase
        .from("colaboradores")
        .select("id, dni, nombres, apellidos, sede")
        .eq("user_id", user?.id)
        .maybeSingle();

      console.log("Colaborador query result:", { colaboradorData, colaboradorError, userId: user?.id });

      if (colaboradorError) {
        console.error("Error fetching colaborador:", colaboradorError);
        throw new Error(`Error al buscar colaborador: ${colaboradorError.message}`);
      }

      if (!colaboradorData) {
        throw new Error("Tu cuenta aún no está vinculada como colaborador. Por favor contacta con RRHH.");
      }

      // Use colaborador's sede if not provided in form
      const sedeToUse = formData.sede || colaboradorData.sede;

      // Fechas temporales que serán actualizadas por n8n
      const fechaTemporal = new Date().toISOString().split('T')[0];

      const { data: insertData, error } = await supabase.from("descansos_medicos").insert({
        user_id: user?.id,
        colaborador_id: colaboradorData.id,
        fecha_inicio: fechaTemporal,
        fecha_fin: fechaTemporal,
        sede: sedeToUse,
        imagen_url: imagenUrl,
      }).select().single();

      if (error) throw error;

      toast({
        title: "Éxito",
        description: "Descanso médico registrado correctamente",
      });

      // Send webhook to n8n
      if (colaboradorData && insertData) {
        await sendWebhook('descanso_medico_creado', {
          descanso_id: insertData.id,
          colaborador_id: colaboradorData.id,
          dni: colaboradorData.dni,
          nombre_completo: `${colaboradorData.apellidos}, ${colaboradorData.nombres}`,
          sede: sedeToUse,
          imagen_url: imagenUrl,
          estado: 'Pendiente'
        });
      }

      setIsDialogOpen(false);
      setFormData({ sede: "", imagen: null });
      fetchDescansos();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setUploading(false);
    }
  };

  const getEstadoBadge = (estado: string) => {
    switch (estado) {
      case "Aprobado":
        return <Badge className="bg-success">{estado}</Badge>;
      case "Rechazado":
        return <Badge variant="destructive">{estado}</Badge>;
      default:
        return <Badge variant="secondary">{estado}</Badge>;
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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Mis Descansos Médicos</h1>
            <p className="text-muted-foreground mt-1">
              Gestiona tus solicitudes de descanso médico
            </p>
          </div>
          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="h-4 w-4" />
                Nuevo Descanso
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Registrar Descanso Médico</DialogTitle>
                <DialogDescription>
                  Sube tu certificado médico y las fechas se extraerán automáticamente
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="sede">Sede</Label>
                  <Input
                    id="sede"
                    placeholder="Ej: Lima Centro"
                    value={formData.sede}
                    onChange={(e) => setFormData({ ...formData, sede: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="imagen">Certificado Médico (Imagen) *</Label>
                  <Input
                    id="imagen"
                    type="file"
                    accept="image/*"
                    onChange={(e) => setFormData({ ...formData, imagen: e.target.files?.[0] || null })}
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    Las fechas se extraerán automáticamente del certificado médico
                  </p>
                </div>
                <Button type="submit" className="w-full" disabled={uploading}>
                  {uploading ? "Subiendo..." : "Registrar Descanso"}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        <div className="grid gap-4">
          {descansos.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FileText className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground text-center">
                  No tienes descansos médicos registrados
                </p>
              </CardContent>
            </Card>
          ) : (
            descansos.map((descanso) => (
              <Card key={descanso.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <Calendar className="h-5 w-5" />
                      {new Date(descanso.fecha_inicio).toLocaleDateString()} - {new Date(descanso.fecha_fin).toLocaleDateString()}
                    </CardTitle>
                    {getEstadoBadge(descanso.estado)}
                  </div>
                  <CardDescription>Sede: {descanso.sede}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {descanso.comentario_rrhh && (
                    <div className="p-3 bg-muted rounded-lg">
                      <p className="text-sm font-medium">Comentario de RRHH:</p>
                      <p className="text-sm text-muted-foreground">{descanso.comentario_rrhh}</p>
                    </div>
                  )}
                  {descanso.imagen_url && (
                    <div>
                      <p className="text-sm font-medium mb-2">Certificado:</p>
                      <img 
                        src={descanso.imagen_url} 
                        alt="Certificado médico" 
                        className="max-w-sm rounded-lg border"
                      />
                    </div>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </Layout>
  );
}
