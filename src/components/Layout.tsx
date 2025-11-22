import { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { LogOut, FileText, Users, Home } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { role, signOut } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await signOut();
    navigate("/auth");
  };

  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <h1 className="text-2xl font-bold text-primary">
                Sistema RRHH
              </h1>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate("/")}
                  className="gap-2"
                >
                  <Home className="h-4 w-4" />
                  Inicio
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => navigate("/descansos")}
                  className="gap-2"
                >
                  <FileText className="h-4 w-4" />
                  Mis Descansos
                </Button>
                {role === "analista_rrhh" && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate("/rrhh/descansos")}
                      className="gap-2"
                    >
                      <FileText className="h-4 w-4" />
                      Gestión Descansos
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate("/rrhh/colaboradores")}
                      className="gap-2"
                    >
                      <Users className="h-4 w-4" />
                      Colaboradores
                    </Button>
                  </>
                )}
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleLogout}
              className="gap-2"
            >
              <LogOut className="h-4 w-4" />
              Cerrar Sesión
            </Button>
          </div>
        </div>
      </nav>
      <main className="container mx-auto px-4 py-8">{children}</main>
    </div>
  );
}
