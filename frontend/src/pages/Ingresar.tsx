import { useMemo, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import {
  ArrowRight,
  ChevronDown,
  ClipboardCheck,
  FileUp,
  ShieldCheck,
  Sparkles,
  Trophy,
  UserRound,
  UsersRound,
} from "lucide-react";
import { useAuth } from "@/auth/context";
import { PublicShell } from "@/components/shell/PublicShell";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { VistaProducto } from "@/components/VistaProducto";
import { useConfig } from "@/hooks/queries";
import { useI18n, type Textos } from "@/i18n/context";
import { ApiError } from "@/lib/api";
import type { Role } from "@/lib/types";
import { cn } from "@/lib/utils";

function crearEsquema(errores: Textos["ingreso"]["errores"]) {
  return z.object({
    dni: z.string().regex(/^\d{8}$/, errores.dni),
    password: z.string().min(1, errores.password).max(200),
  });
}
type Formulario = z.infer<ReturnType<typeof crearEsquema>>;

// En el mismo orden que `t.ingreso.caracteristicas`.
const ICONOS_CARACTERISTICAS = [FileUp, Sparkles, ClipboardCheck];

const ICONO_CUENTA: Record<Role, typeof UserRound> = {
  colaborador: UserRound,
  analista_rrhh: UsersRound,
};

function mensajeDeError(errores: Textos["ingreso"]["errores"], error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "rate_limit" && error.retryAfter) return errores.demasiados(error.retryAfter);
    return error.message;
  }
  return errores.generico;
}

export default function Ingresar() {
  const { usuario, cargando, iniciarSesion } = useAuth();
  const { data: config } = useConfig();
  const { t } = useI18n();
  const g = t.ingreso;
  const esquema = useMemo(() => crearEsquema(g.errores), [g.errores]);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const [acepta, setAcepta] = useState(false);
  const [faltaAceptar, setFaltaAceptar] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entrando, setEntrando] = useState<string | null>(null);
  const [formularioAbierto, setFormularioAbierto] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Formulario>({
    resolver: zodResolver(esquema),
    defaultValues: { dni: "", password: "" },
  });

  const destino = (location.state as { desde?: string } | null)?.desde ?? "/";
  if (!cargando && usuario) return <Navigate to={destino} replace />;

  const demo = config?.demo.habilitado ? config.demo : null;
  const concurso = config?.proyecto.concurso;
  const puesto = config?.proyecto.puesto;
  const mostrarFormulario = !demo || formularioAbierto;

  const entrar = async (dni: string, password: string, origen: string) => {
    setError(null);
    if (!acepta) {
      setFaltaAceptar(true);
      return;
    }
    const version = config?.proyecto.version_terminos;
    if (!version) {
      setError(g.errores.sinConfig);
      return;
    }
    setEntrando(origen);
    try {
      await iniciarSesion(dni, password, version);
      navigate(destino, { replace: true });
    } catch (causa) {
      if (causa instanceof ApiError && causa.code === "terminos_desactualizados") {
        setAcepta(false);
        await queryClient.invalidateQueries({ queryKey: ["config"] });
      }
      setError(mensajeDeError(g.errores, causa));
    } finally {
      setEntrando(null);
    }
  };

  return (
    <PublicShell sinAcceso>
      <div className="grid items-center gap-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,25rem)] lg:gap-16">
        <section className="space-y-8">
          <div className="space-y-5">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
              {puesto && <Trophy className="h-4 w-4 shrink-0" aria-hidden />}
              {g.eyebrow(concurso, puesto)}
            </p>
            <h1 className="text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">
              {g.titulo}
            </h1>
            <p className="max-w-xl text-base leading-7 text-muted-foreground">{g.lead}</p>
          </div>

          <div className="space-y-4 rounded-xl border bg-background p-5 shadow-xs sm:p-6">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-base font-semibold">{g.acceder}</h2>
              <Link
                to="/como-funciona"
                className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
              >
                {g.comoFunciona}
                <ArrowRight className="h-3.5 w-3.5" aria-hidden />
              </Link>
            </div>

            <div
              className={cn(
                "flex items-start gap-3 rounded-lg p-3 transition-colors",
                faltaAceptar && !acepta ? "bg-red-50 ring-1 ring-red-200" : "bg-muted/60",
              )}
            >
              <Checkbox
                id="acepta"
                checked={acepta}
                onCheckedChange={(valor) => {
                  setAcepta(valor === true);
                  setFaltaAceptar(false);
                }}
                aria-describedby={faltaAceptar ? "acepta-error" : undefined}
                className="mt-0.5"
              />
              <div className="space-y-1">
                <Label htmlFor="acepta" className="font-normal leading-5">
                  {g.acepto({
                    terminos: (texto) => (
                      <Link to="/terminos" className="font-medium text-primary underline underline-offset-2">
                        {texto}
                      </Link>
                    ),
                    privacidad: (texto) => (
                      <Link to="/privacidad" className="font-medium text-primary underline underline-offset-2">
                        {texto}
                      </Link>
                    ),
                  })}
                </Label>
                {faltaAceptar && !acepta && (
                  <p id="acepta-error" className="text-xs text-red-700" role="alert">
                    {g.marcaCasilla}
                  </p>
                )}
              </div>
            </div>

            {demo && (
              <div className="grid gap-3 sm:grid-cols-2">
                {demo.usuarios.map((cuenta) => {
                  const { titulo, texto } = g.cuentas[cuenta.role];
                  const Icono = ICONO_CUENTA[cuenta.role];
                  return (
                    <button
                      key={cuenta.dni}
                      type="button"
                      onClick={() => entrar(cuenta.dni, cuenta.password, cuenta.role)}
                      disabled={entrando !== null}
                      className="group flex items-start gap-3 rounded-lg border p-3.5 text-left transition-colors hover:border-primary/60 hover:bg-accent/40 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
                    >
                      <Icono className="mt-0.5 h-5 w-5 shrink-0 text-primary" aria-hidden />
                      <span className="space-y-0.5">
                        <span className="block text-sm font-semibold">
                          {entrando === cuenta.role ? g.entrando : titulo}
                        </span>
                        <span className="block text-xs leading-5 text-muted-foreground">{texto}</span>
                      </span>
                    </button>
                  );
                })}
              </div>
            )}

            {error && (
              <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
                {error}
              </p>
            )}

            {demo && (
              <button
                type="button"
                onClick={() => setFormularioAbierto((abierto) => !abierto)}
                aria-expanded={formularioAbierto}
                className="inline-flex items-center gap-1 rounded text-sm text-muted-foreground hover:text-foreground focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring"
              >
                {g.conDni}
                <ChevronDown
                  className={cn("h-4 w-4 transition-transform", formularioAbierto && "rotate-180")}
                  aria-hidden
                />
              </button>
            )}

            {mostrarFormulario && (
              <form
                onSubmit={handleSubmit(({ dni, password }) => entrar(dni, password, "formulario"))}
                className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end"
                noValidate
              >
                <div className="space-y-1.5">
                  <Label htmlFor="dni">{g.dni}</Label>
                  <Input
                    id="dni"
                    inputMode="numeric"
                    autoComplete="username"
                    maxLength={8}
                    placeholder="12345678"
                    aria-invalid={Boolean(errors.dni)}
                    {...register("dni")}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="password">{g.password}</Label>
                  <Input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    aria-invalid={Boolean(errors.password)}
                    {...register("password")}
                  />
                </div>
                <Button type="submit" disabled={entrando !== null}>
                  {entrando === "formulario" ? g.entrando : g.ingresar}
                </Button>
                {(errors.dni || errors.password) && (
                  <p className="text-xs text-red-700 sm:col-span-3">
                    {errors.dni?.message ?? errors.password?.message}
                  </p>
                )}
              </form>
            )}

            <p className="flex items-start gap-2 text-xs leading-5 text-muted-foreground">
              <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
              {demo ? g.notaDemo(demo.retencion_horas) : g.notaReal}
            </p>
          </div>
        </section>

        <div className="hidden sm:block">
          <VistaProducto />
        </div>
      </div>

      <ul className="mt-16 grid gap-8 border-t pt-12 sm:grid-cols-3" aria-label={g.caracteristicasEtiqueta}>
        {g.caracteristicas.map(({ titulo, texto }, indice) => {
          const Icono = ICONOS_CARACTERISTICAS[indice] ?? Sparkles;
          return (
          <li key={titulo} className="space-y-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg border bg-background text-primary shadow-xs">
              <Icono className="h-5 w-5" aria-hidden />
            </span>
            <p className="text-sm font-semibold">{titulo}</p>
            <p className="text-sm leading-6 text-muted-foreground">{texto}</p>
          </li>
          );
        })}
      </ul>
    </PublicShell>
  );
}
