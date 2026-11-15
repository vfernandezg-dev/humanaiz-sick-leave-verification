import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useAuth } from "@/auth/context";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useConfig } from "@/hooks/queries";
import { ApiError } from "@/lib/api";

const esquema = z.object({
  dni: z.string().regex(/^\d{8}$/, "El DNI tiene 8 dígitos."),
  password: z.string().min(1, "Escribe tu contraseña.").max(200),
});
type Formulario = z.infer<typeof esquema>;

function mensajeDeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "rate_limit" && error.retryAfter) {
      return `Demasiados intentos. Vuelve a probar en ${error.retryAfter} segundos.`;
    }
    return error.message;
  }
  return "No se pudo iniciar sesión. Inténtalo de nuevo.";
}

export default function Auth() {
  const { usuario, cargando, iniciarSesion } = useAuth();
  const { data: config } = useConfig();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Formulario>({ resolver: zodResolver(esquema), defaultValues: { dni: "", password: "" } });

  const destino = (location.state as { desde?: string } | null)?.desde ?? "/";

  if (!cargando && usuario) return <Navigate to={destino} replace />;

  const entrar = async ({ dni, password }: Formulario) => {
    setError(null);
    try {
      await iniciarSesion(dni, password);
      navigate(destino, { replace: true });
    } catch (causa) {
      setError(mensajeDeError(causa));
    }
  };

  const demo = config?.demo.habilitado ? config.demo : null;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md space-y-4">
        <Card>
          <CardHeader className="text-center">
            <CardTitle className="text-3xl font-bold text-primary">HumanAIz</CardTitle>
            <CardDescription>Registro y verificación de descansos médicos</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(entrar)} className="space-y-4" noValidate>
              <div className="space-y-2">
                <Label htmlFor="dni">DNI</Label>
                <Input
                  id="dni"
                  inputMode="numeric"
                  autoComplete="username"
                  maxLength={8}
                  placeholder="12345678"
                  aria-invalid={Boolean(errors.dni)}
                  {...register("dni")}
                />
                {errors.dni && <p className="text-xs text-destructive">{errors.dni.message}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Contraseña</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  aria-invalid={Boolean(errors.password)}
                  {...register("password")}
                />
                {errors.password && (
                  <p className="text-xs text-destructive">{errors.password.message}</p>
                )}
              </div>
              {error && (
                <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive" role="alert">
                  {error}
                </p>
              )}
              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? "Entrando…" : "Iniciar sesión"}
              </Button>
            </form>
            {!demo && (
              <p className="mt-4 text-center text-xs text-muted-foreground">
                ¿No tienes cuenta? Solicítala al área de Recursos Humanos.
              </p>
            )}
          </CardContent>
        </Card>

        {demo && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Cuentas de prueba</CardTitle>
              <CardDescription>{demo.aviso}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {demo.usuarios.map((cuenta) => (
                <div
                  key={cuenta.dni}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3"
                >
                  <div className="text-sm">
                    <p className="font-medium">{cuenta.etiqueta}</p>
                    <p className="text-muted-foreground">
                      DNI <code>{cuenta.dni}</code> · contraseña <code>{cuenta.password}</code>
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={isSubmitting}
                    onClick={() => entrar({ dni: cuenta.dni, password: cuenta.password })}
                  >
                    Entrar
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
