import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/hooks/useAuth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText, Users, ClipboardCheck } from "lucide-react";

export default function Index() {
  const { user, role, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && !user) {
      navigate("/auth");
    }
  }, [user, loading, navigate]);

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
          <h1 className="text-3xl font-bold text-foreground">
            Bienvenido al Sistema de RRHH
          </h1>
          <p className="text-muted-foreground mt-2">
            {role === "analista_rrhh" 
              ? "Panel de administración de Recursos Humanos"
              : "Gestiona tus descansos médicos"}
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card 
            className="cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => navigate("/descansos")}
          >
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <FileText className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Mis Descansos</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Registra y consulta tus descansos médicos
              </CardDescription>
            </CardContent>
          </Card>

          {role === "analista_rrhh" && (
            <>
              <Card 
                className="cursor-pointer hover:shadow-lg transition-shadow"
                onClick={() => navigate("/rrhh/descansos")}
              >
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg">
                      <ClipboardCheck className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle>Gestión Descansos</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription>
                    Aprueba o rechaza solicitudes de descanso médico
                  </CardDescription>
                </CardContent>
              </Card>

              <Card 
                className="cursor-pointer hover:shadow-lg transition-shadow"
                onClick={() => navigate("/rrhh/colaboradores")}
              >
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-primary/10 rounded-lg">
                      <Users className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle>Colaboradores</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription>
                    Consulta el maestro de colaboradores
                  </CardDescription>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </Layout>
  );
}
