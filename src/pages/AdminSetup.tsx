import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/hooks/use-toast";
import { CheckCircle2, Loader2 } from "lucide-react";

export default function AdminSetup() {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const { toast } = useToast();

  const setupAdmin = async () => {
    setLoading(true);
    try {
      const { data, error } = await supabase.functions.invoke('setup-admin');

      if (error) throw error;

      toast({
        title: "Usuario administrador creado",
        description: "DNI: 11111111 / Contraseña: 11111111",
      });

      setSuccess(true);
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl font-bold text-primary">
            Configuración Inicial
          </CardTitle>
          <CardDescription>
            Crea el usuario administrador de RRHH
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {success ? (
            <div className="text-center space-y-4">
              <CheckCircle2 className="w-16 h-16 text-green-600 mx-auto" />
              <div>
                <p className="font-semibold text-lg">¡Usuario creado exitosamente!</p>
                <div className="mt-4 p-4 bg-muted rounded-lg text-left">
                  <p className="text-sm font-mono">
                    <strong>DNI:</strong> 11111111
                  </p>
                  <p className="text-sm font-mono">
                    <strong>Contraseña:</strong> 11111111
                  </p>
                  <p className="text-sm font-mono">
                    <strong>Rol:</strong> Analista RRHH
                  </p>
                </div>
              </div>
              <Button 
                onClick={() => window.location.href = '/auth'} 
                className="w-full"
              >
                Ir a iniciar sesión
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground text-center">
                Este proceso creará un usuario administrador con acceso completo a los paneles de RRHH.
              </p>
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-sm font-mono">
                  <strong>DNI:</strong> 11111111
                </p>
                <p className="text-sm font-mono">
                  <strong>Contraseña:</strong> 11111111
                </p>
              </div>
              <Button 
                onClick={setupAdmin} 
                disabled={loading}
                className="w-full"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creando usuario...
                  </>
                ) : (
                  "Crear usuario administrador"
                )}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
