import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/context";
import { Dropzone } from "@/components/Dropzone";
import { PageHeader } from "@/components/PageHeader";
import { AppShell } from "@/components/shell/AppShell";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useConfig, useCrearDescanso } from "@/hooks/queries";
import { useToast } from "@/hooks/use-toast";
import { api, ApiError, type VarianteEjemplo } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useLlm } from "@/llm/context";

const MB = 1024 * 1024;
const EJEMPLOS: { variante: VarianteEjemplo; texto: string }[] = [
  { variante: "valido", texto: "Válido" },
  { variante: "observado", texto: "Con observaciones" },
  { variante: "otra-persona", texto: "De otra persona" },
  { variante: "citt", texto: "Formato CITT" },
];
const TIPOS_POR_DEFECTO = ["image/jpeg", "image/png", "image/webp", "application/pdf"];

function Paso({ numero, titulo, children }: { numero: number; titulo: string; children: React.ReactNode }) {
  return (
    <fieldset className="space-y-3">
      <legend className="flex items-center gap-2 text-sm font-medium">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-foreground text-[11px] text-background">
          {numero}
        </span>
        {titulo}
      </legend>
      {children}
    </fieldset>
  );
}

export default function NuevoDescanso() {
  const { usuario } = useAuth();
  const { credencial, abrir: abrirClave } = useLlm();
  const { data: config } = useConfig();
  const { toast } = useToast();
  const navigate = useNavigate();
  const crear = useCrearDescanso();

  const [archivo, setArchivo] = useState<File | null>(null);
  const [errorArchivo, setErrorArchivo] = useState<string | null>(null);
  const [sede, setSede] = useState(usuario?.colaborador?.sede ?? "");
  const [leerConIA, setLeerConIA] = useState(true);
  const [esDePrueba, setEsDePrueba] = useState(false);
  const [faltaConfirmar, setFaltaConfirmar] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generando, setGenerando] = useState<VarianteEjemplo | null>(null);

  if (!usuario?.colaborador) return <Navigate to="/descansos" replace />;

  const tipos = config?.carga.tipos_mime ?? TIPOS_POR_DEFECTO;
  const maxBytes = config?.carga.max_bytes ?? 10 * MB;
  const maxPaginas = config?.carga.max_paginas_pdf ?? 5;

  // Comprobaciones de cortesía: quien valida de verdad el archivo es el servidor.
  const elegir = (elegido: File | null) => {
    setErrorArchivo(null);
    if (elegido && elegido.size > maxBytes) {
      setErrorArchivo(`El archivo pesa más de ${Math.floor(maxBytes / MB)} MB.`);
      return;
    }
    if (elegido && elegido.type && !tipos.includes(elegido.type)) {
      setErrorArchivo("Formato no admitido. Sube una imagen JPG, PNG o WebP, o un PDF.");
      return;
    }
    setArchivo(elegido);
  };

  // Certificado ficticio generado por el servidor con los datos del propio usuario.
  const usarEjemplo = async (variante: VarianteEjemplo) => {
    setErrorArchivo(null);
    setGenerando(variante);
    try {
      const blob = await api.certificadoEjemplo(variante);
      setArchivo(new File([blob], `certificado-ejemplo-${variante}.jpg`, { type: "image/jpeg" }));
      setEsDePrueba(true);
      setFaltaConfirmar(false);
    } catch (causa) {
      setErrorArchivo(causa instanceof ApiError ? causa.message : "No se pudo generar el ejemplo.");
    } finally {
      setGenerando(null);
    }
  };

  const registrar = async (evento: React.FormEvent) => {
    evento.preventDefault();
    setError(null);
    if (!archivo) {
      setErrorArchivo("Elige el archivo del certificado.");
      return;
    }
    if (!sede.trim()) {
      setError("Indica la sede.");
      return;
    }
    if (!esDePrueba) {
      setFaltaConfirmar(true);
      return;
    }
    try {
      const creado = await crear.mutateAsync({ archivo, sede });
      toast({ title: "Descanso registrado", description: "RRHH lo revisará y confirmará las fechas." });
      navigate(`/descansos/${creado.id}`, {
        replace: true,
        state: { desde: "/descansos", analizar: leerConIA && Boolean(credencial) },
      });
    } catch (causa) {
      const mensaje = causa instanceof ApiError ? causa.message : "No se pudo registrar el descanso.";
      if (causa instanceof ApiError && causa.detalles.some((d) => d.campo === "sede")) {
        setError(mensaje);
      } else {
        setErrorArchivo(mensaje);
      }
    }
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-xl">
        <PageHeader
          volver={{ to: "/descansos", texto: "Mis descansos" }}
          titulo="Registrar descanso médico"
          descripcion="Sube el certificado. RRHH lo revisará y confirmará las fechas: no hace falta que las escribas."
        />

        <form onSubmit={registrar} className="space-y-8" noValidate>
          <Paso numero={1} titulo="Certificado">
            <Dropzone
              id="archivo"
              archivo={archivo}
              onElegir={elegir}
              accept={tipos.join(",")}
              ayuda={`Foto (JPG, PNG, WebP) o PDF de hasta ${maxPaginas} páginas · máximo ${Math.floor(maxBytes / MB)} MB`}
              invalido={Boolean(errorArchivo)}
            />
            {errorArchivo && (
              <p className="text-sm text-red-700" role="alert">
                {errorArchivo}
              </p>
            )}
            {config?.demo.habilitado && !archivo && (
              <div className="space-y-2 rounded-lg bg-muted/60 p-3">
                <p className="text-xs leading-5 text-muted-foreground">
                  ¿No tienes un documento de prueba? Usa un certificado ficticio generado con los
                  datos de tu ficha. Cada variante produce un resultado distinto en la lectura con IA:
                </p>
                <div className="flex flex-wrap gap-2">
                  {EJEMPLOS.map(({ variante, texto }) => (
                    <Button
                      key={variante}
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 bg-background"
                      onClick={() => usarEjemplo(variante)}
                      disabled={generando !== null}
                    >
                      {generando === variante ? "Generando…" : texto}
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </Paso>

          <Paso numero={2} titulo="Sede">
            <div className="space-y-1.5">
              <Label htmlFor="sede" className="sr-only">
                Sede
              </Label>
              <Input
                id="sede"
                value={sede}
                maxLength={100}
                placeholder="Ej.: Lima Centro"
                onChange={(e) => setSede(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">Se completa con la sede de tu ficha. Cámbiala si hace falta.</p>
            </div>
          </Paso>

          <Paso numero={3} titulo="Lectura con IA (opcional)">
            {credencial ? (
              <div className="flex items-start gap-3">
                <Checkbox
                  id="leer-con-ia"
                  checked={leerConIA}
                  onCheckedChange={(valor) => setLeerConIA(valor === true)}
                  className="mt-0.5"
                />
                <Label htmlFor="leer-con-ia" className="font-normal leading-5">
                  Leer el certificado con IA al terminar, usando mi clave.
                  <span className="block text-xs text-muted-foreground">
                    Extrae los datos y los compara con tu ficha. Tarda menos de un minuto.
                  </span>
                </Label>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Si quieres que la IA revise el documento,{" "}
                <button type="button" onClick={abrirClave} className="font-medium text-primary underline underline-offset-2">
                  configura tu clave de IA
                </button>
                . También puedes hacerlo después.
              </p>
            )}
          </Paso>

          <div
            className={cn(
              "flex items-start gap-3 rounded-lg border p-4",
              faltaConfirmar && !esDePrueba ? "border-red-300 bg-red-50" : "bg-amber-50/60",
            )}
          >
            <Checkbox
              id="es-de-prueba"
              checked={esDePrueba}
              onCheckedChange={(valor) => {
                setEsDePrueba(valor === true);
                setFaltaConfirmar(false);
              }}
              className="mt-0.5"
            />
            <div className="space-y-1">
              <Label htmlFor="es-de-prueba" className="font-normal leading-5">
                Confirmo que el documento es ficticio o de prueba y no contiene datos de salud reales
                de ninguna persona.
              </Label>
              {faltaConfirmar && !esDePrueba && (
                <p className="text-xs text-red-700" role="alert">
                  Esta demo no admite documentos reales: confirma para continuar.
                </p>
              )}
            </div>
          </div>

          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
              {error}
            </p>
          )}

          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={crear.isPending}>
              {crear.isPending ? "Subiendo…" : "Registrar descanso"}
            </Button>
            <Button type="button" variant="ghost" onClick={() => navigate("/descansos")}>
              Cancelar
            </Button>
          </div>
        </form>
      </div>
    </AppShell>
  );
}
