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
import { useI18n, type Textos } from "@/i18n/context";
import { api, ApiError, type VarianteEjemplo } from "@/lib/api";
import { prepararImagen, type MotivoRechazo } from "@/lib/imagen";
import { cn } from "@/lib/utils";
import { useLlm } from "@/llm/context";

const MB = 1024 * 1024;
const EJEMPLOS: { variante: VarianteEjemplo; texto: keyof Textos["registro"]["ejemplos"] }[] = [
  { variante: "valido", texto: "valido" },
  { variante: "observado", texto: "observado" },
  { variante: "otra-persona", texto: "otraPersona" },
  { variante: "citt", texto: "citt" },
];
const TIPOS_POR_DEFECTO = ["image/jpeg", "image/png", "image/webp"];
const EXTENSIONES = ".jpg,.jpeg,.png,.webp";

function mensajeRechazo(
  r: Textos["registro"]["rechazo"],
  motivo: MotivoRechazo,
  maxMb: number,
  minLado: number,
): string {
  switch (motivo) {
    case "pdf":
      return r.pdf;
    case "heic":
      return r.heic;
    case "pesada":
      return r.pesada(maxMb);
    case "pequena":
      return r.pequena(minLado);
    case "ilegible":
      return r.ilegible;
    default:
      return r.formato;
  }
}

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
  const { t } = useI18n();
  const r = t.registro;
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
  const [preparando, setPreparando] = useState(false);
  const [reducida, setReducida] = useState(false);

  if (!usuario?.colaborador) return <Navigate to="/descansos" replace />;

  const tipos = config?.carga.tipos_mime ?? TIPOS_POR_DEFECTO;
  const maxBytes = config?.carga.max_bytes ?? 5 * MB;
  const maxMb = Math.floor(maxBytes / MB);
  const minLado = config?.carga.min_lado_px ?? 400;
  const maxLado = config?.carga.max_lado_px ?? 2400;

  // Comprobaciones de cortesía y reducción de fotos grandes: quien valida de
  // verdad la imagen es el servidor.
  const elegir = async (elegido: File | null) => {
    setErrorArchivo(null);
    setReducida(false);
    if (!elegido) {
      setArchivo(null);
      return;
    }
    setPreparando(true);
    try {
      const resultado = await prepararImagen(elegido, { tipos, maxBytes, minLado, maxLado });
      if (resultado.ok) {
        setArchivo(resultado.archivo);
        setReducida(resultado.reducida);
      } else {
        setArchivo(null);
        setErrorArchivo(mensajeRechazo(r.rechazo, resultado.motivo, maxMb, minLado));
      }
    } finally {
      setPreparando(false);
    }
  };

  // Certificado ficticio generado por el servidor con los datos del propio usuario.
  const usarEjemplo = async (variante: VarianteEjemplo) => {
    setErrorArchivo(null);
    setGenerando(variante);
    try {
      const blob = await api.certificadoEjemplo(variante);
      setArchivo(new File([blob], `certificado-ejemplo-${variante}.jpg`, { type: "image/jpeg" }));
      setReducida(false);
      setEsDePrueba(true);
      setFaltaConfirmar(false);
    } catch (causa) {
      setErrorArchivo(causa instanceof ApiError ? causa.message : r.ejemplos.error);
    } finally {
      setGenerando(null);
    }
  };

  const registrar = async (evento: React.FormEvent) => {
    evento.preventDefault();
    setError(null);
    if (!archivo) {
      setErrorArchivo(r.faltaArchivo);
      return;
    }
    if (!sede.trim()) {
      setError(r.sede.falta);
      return;
    }
    if (!esDePrueba) {
      setFaltaConfirmar(true);
      return;
    }
    try {
      const creado = await crear.mutateAsync({ archivo, sede });
      toast({ title: r.registrado, description: r.registradoDetalle });
      navigate(`/descansos/${creado.id}`, {
        replace: true,
        state: { desde: "/descansos", analizar: leerConIA && Boolean(credencial) },
      });
    } catch (causa) {
      const mensaje = causa instanceof ApiError ? causa.message : r.noSeRegistro;
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
          volver={{ to: "/descansos", texto: r.volver }}
          titulo={r.titulo}
          descripcion={r.descripcion}
        />

        <form onSubmit={registrar} className="space-y-8" noValidate>
          <Paso numero={1} titulo={r.pasos.imagen}>
            <Dropzone
              id="archivo"
              archivo={archivo}
              onElegir={(elegido) => void elegir(elegido)}
              accept={`${tipos.join(",")},${EXTENSIONES}`}
              ayuda={r.ayuda(maxMb)}
              invalido={Boolean(errorArchivo)}
              ocupado={preparando}
            />
            {errorArchivo && (
              <p className="text-sm text-red-700" role="alert">
                {errorArchivo}
              </p>
            )}
            {reducida && (
              <p className="text-xs text-muted-foreground">{r.reducida(maxLado)}</p>
            )}
            {config?.demo.habilitado && !archivo && (
              <div className="space-y-2 rounded-lg bg-muted/60 p-3">
                <p className="text-xs leading-5 text-muted-foreground">{r.ejemplos.intro}</p>
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
                      {generando === variante ? r.ejemplos.generando : r.ejemplos[texto]}
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </Paso>

          <Paso numero={2} titulo={r.pasos.sede}>
            <div className="space-y-1.5">
              <Label htmlFor="sede" className="sr-only">
                {r.pasos.sede}
              </Label>
              <Input
                id="sede"
                value={sede}
                maxLength={100}
                placeholder={r.sede.placeholder}
                onChange={(e) => setSede(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">{r.sede.ayuda}</p>
            </div>
          </Paso>

          <Paso numero={3} titulo={r.pasos.lectura}>
            {credencial ? (
              <div className="flex items-start gap-3">
                <Checkbox
                  id="leer-con-ia"
                  checked={leerConIA}
                  onCheckedChange={(valor) => setLeerConIA(valor === true)}
                  className="mt-0.5"
                />
                <Label htmlFor="leer-con-ia" className="font-normal leading-5">
                  {r.lectura.opcion}
                  <span className="block text-xs text-muted-foreground">{r.lectura.detalle}</span>
                </Label>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                {r.lectura.sinClaveAntes}
                <button type="button" onClick={abrirClave} className="font-medium text-primary underline underline-offset-2">
                  {r.lectura.sinClaveEnlace}
                </button>
                {r.lectura.sinClaveDespues}
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
                {r.confirmacion}
              </Label>
              {faltaConfirmar && !esDePrueba && (
                <p className="text-xs text-red-700" role="alert">
                  {r.faltaConfirmar}
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
            <Button type="submit" disabled={crear.isPending || preparando}>
              {crear.isPending ? r.subiendo : r.registrar}
            </Button>
            <Button type="button" variant="ghost" onClick={() => navigate("/descansos")}>
              {t.comun.acciones.cancelar}
            </Button>
          </div>
        </form>
      </div>
    </AppShell>
  );
}
