import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, ExternalLink, KeyRound, Loader2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useConfig } from "@/hooks/queries";
import { useToast } from "@/hooks/use-toast";
import { api, ApiError } from "@/lib/api";
import type { ModeloDisponible, ProveedorLlm } from "@/lib/types";
import { cn } from "@/lib/utils";
import { detectarProveedor } from "./detectar";
import { llmStore } from "./store";

interface Props {
  abierto: boolean;
  onCambio: (abierto: boolean) => void;
}

type Verificacion =
  | { estado: "inicial" }
  | { estado: "cargando" }
  | { estado: "ok"; modelos: ModeloDisponible[] }
  | { estado: "error"; mensaje: string };

const CLAVE_MIN = 16;

function predeterminado(proveedor: ProveedorLlm | undefined): string {
  return proveedor?.modelos.find((m) => m.predeterminado)?.id ?? proveedor?.modelos[0]?.id ?? "";
}

export function LlmKeyDialog({ abierto, onCambio }: Props) {
  const { data: config } = useConfig();
  const { toast } = useToast();
  const proveedores = useMemo(() => config?.llm.proveedores ?? [], [config]);

  const [clave, setClave] = useState("");
  const [proveedorId, setProveedorId] = useState("");
  const [elegidoAMano, setElegidoAMano] = useState(false);
  const [modelo, setModelo] = useState("");
  const [recordar, setRecordar] = useState(false);
  const [verificacion, setVerificacion] = useState<Verificacion>({ estado: "inicial" });

  const configurada = llmStore.get();

  // Al abrir se parte de lo configurado. La clave guardada no se vuelve a
  // mostrar: para cambiarla hay que escribir una nueva.
  useEffect(() => {
    if (!abierto) return;
    const actual = llmStore.get();
    const inicial = proveedores.find((p) => p.id === actual?.proveedor) ?? proveedores[0];
    setClave("");
    setProveedorId(inicial?.id ?? "");
    setElegidoAMano(Boolean(actual));
    setModelo(actual?.modelo ?? predeterminado(inicial));
    setRecordar(actual?.recordar ?? false);
    setVerificacion({ estado: "inicial" });
  }, [abierto, proveedores]);

  const proveedor = proveedores.find((p) => p.id === proveedorId);
  const detectado = detectarProveedor(clave, proveedores);
  const claveEfectiva =
    clave.trim() || (configurada?.proveedor === proveedorId ? configurada.clave : "");
  const claveValida = claveEfectiva.length >= CLAVE_MIN && !/\s/.test(claveEfectiva);

  const cambiarProveedor = (id: string, aMano: boolean) => {
    if (!id || id === proveedorId) return;
    setProveedorId(id);
    setElegidoAMano(aMano);
    setModelo(predeterminado(proveedores.find((p) => p.id === id)));
    setVerificacion({ estado: "inicial" });
  };

  const escribirClave = (valor: string) => {
    setClave(valor);
    setVerificacion({ estado: "inicial" });
    const reconocido = detectarProveedor(valor, proveedores);
    // Si la clave delata su proveedor, se selecciona solo, salvo que el
    // usuario ya haya elegido otro a mano.
    if (reconocido && !elegidoAMano) cambiarProveedor(reconocido.id, false);
  };

  const cargarModelos = async () => {
    if (!proveedor || !claveValida) return;
    setVerificacion({ estado: "cargando" });
    try {
      const respuesta = await api.modelosDisponibles(proveedor.id, claveEfectiva);
      setVerificacion({ estado: "ok", modelos: respuesta.modelos });
      if (!modelo.trim() && respuesta.modelos[0]) setModelo(respuesta.modelos[0].id);
    } catch (error) {
      setVerificacion({
        estado: "error",
        mensaje: error instanceof ApiError ? error.message : "No se pudo comprobar la clave.",
      });
    }
  };

  const sugeridos = useMemo(() => proveedor?.modelos ?? [], [proveedor]);
  const opciones = useMemo(() => {
    const deLaCuenta = verificacion.estado === "ok" ? verificacion.modelos : [];
    const vistos = new Set<string>();
    return [...sugeridos.map((m) => ({ id: m.id, nombre: m.nombre })), ...deLaCuenta].filter(
      (m) => {
        if (vistos.has(m.id)) return false;
        vistos.add(m.id);
        return true;
      },
    );
  }, [sugeridos, verificacion]);

  const modeloFinal = modelo.trim();
  const listo = Boolean(proveedor) && claveValida && modeloFinal.length > 0;

  const guardar = (evento: React.FormEvent) => {
    evento.preventDefault();
    if (!listo || !proveedor) return;
    llmStore.guardar({ proveedor: proveedor.id, modelo: modeloFinal, clave: claveEfectiva, recordar });
    toast({ title: "Clave de IA lista", description: `${proveedor.nombre} · ${modeloFinal}` });
    onCambio(false);
  };

  const olvidar = () => {
    llmStore.olvidar();
    setClave("");
    toast({ title: "Clave eliminada", description: "Se borró de este navegador." });
    onCambio(false);
  };

  return (
    <Dialog open={abierto} onOpenChange={onCambio}>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5" aria-hidden />
            Tu clave de IA
          </DialogTitle>
          <DialogDescription>
            Opcional. Sirve una clave de cualquiera de los proveedores admitidos; el consumo se
            cobra a tu cuenta y tú eliges el modelo.
          </DialogDescription>
        </DialogHeader>

        {proveedores.length === 0 ? (
          <p className="text-sm text-muted-foreground">No hay proveedores de IA habilitados.</p>
        ) : (
          // autoComplete="off": no es un formulario de acceso; el navegador no
          // debe ofrecer guardar la clave como si fuera una contraseña.
          <form onSubmit={guardar} className="space-y-5" autoComplete="off" noValidate>
            <div className="space-y-1.5">
              <Label htmlFor="llm-clave">Clave de API</Label>
              <Input
                id="llm-clave"
                name="llm-clave"
                type="password"
                value={clave}
                onChange={(e) => escribirClave(e.target.value)}
                placeholder={
                  configurada?.proveedor === proveedorId
                    ? "Clave configurada. Pega otra para reemplazarla"
                    : "Pega aquí tu clave"
                }
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
                data-1p-ignore
                data-lpignore="true"
                data-bwignore
              />
              <p className="text-xs text-muted-foreground" aria-live="polite">
                {detectado ? (
                  <span className="inline-flex items-center gap-1 text-emerald-700">
                    <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                    Parece una clave de {detectado.nombre}.
                  </span>
                ) : clave.trim() && !claveValida ? (
                  <span className="text-red-700">
                    La clave parece incompleta. Cópiala entera, sin espacios.
                  </span>
                ) : (
                  "El proveedor se reconoce al pegarla."
                )}
              </p>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between gap-2">
                <Label htmlFor="llm-proveedor">Proveedor</Label>
                {proveedor && (
                  <a
                    href={proveedor.url_claves}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                  >
                    Obtener una clave
                    <ExternalLink className="h-3 w-3" aria-hidden />
                  </a>
                )}
              </div>
              <Select value={proveedorId} onValueChange={(v) => cambiarProveedor(v, true)}>
                <SelectTrigger id="llm-proveedor">
                  <SelectValue placeholder="Elige un proveedor" />
                </SelectTrigger>
                <SelectContent>
                  {proveedores.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.nombre}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Label htmlFor="llm-modelo">Modelo</Label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1.5 px-2 text-xs text-primary"
                  onClick={cargarModelos}
                  disabled={!claveValida || verificacion.estado === "cargando"}
                >
                  {verificacion.estado === "cargando" && (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                  )}
                  Comprobar clave y cargar modelos
                </Button>
              </div>
              <Input
                id="llm-modelo"
                list="llm-modelos-opciones"
                value={modelo}
                onChange={(e) => setModelo(e.target.value)}
                placeholder="Elige de la lista o escribe cualquier modelo"
                autoComplete="off"
                spellCheck={false}
                maxLength={120}
              />
              <datalist id="llm-modelos-opciones">
                {opciones.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.nombre}
                  </option>
                ))}
              </datalist>
              {sugeridos.length > 0 && (
                <div className="flex flex-wrap gap-1.5" aria-label="Modelos sugeridos">
                  {sugeridos.map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => setModelo(m.id)}
                      aria-pressed={modelo === m.id}
                      className={cn(
                        "rounded-full border px-2.5 py-1 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                        modelo === m.id
                          ? "border-primary bg-accent text-accent-foreground"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {m.nombre}
                      {m.predeterminado && (
                        <span className="ml-1 text-[10px] uppercase tracking-wide">· recomendado</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
              <p className="text-xs" aria-live="polite">
                {verificacion.estado === "ok" ? (
                  <span className="inline-flex items-center gap-1 text-emerald-700">
                    <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                    Clave válida · {verificacion.modelos.length}{" "}
                    {verificacion.modelos.length === 1 ? "modelo disponible" : "modelos disponibles"}
                  </span>
                ) : verificacion.estado === "error" ? (
                  <span className="text-red-700">{verificacion.mensaje}</span>
                ) : (
                  <span className="text-muted-foreground">
                    {sugeridos.length > 0
                      ? "Usa uno sugerido, escribe otro o carga los de tu cuenta."
                      : "Carga los modelos de tu cuenta o escribe el que quieras usar."}
                    {proveedor && proveedor.max_imagenes < 5
                      ? ` Este proveedor lee hasta ${proveedor.max_imagenes} páginas.`
                      : ""}
                  </span>
                )}
              </p>
            </div>

            <div className="flex items-start gap-3">
              <Checkbox
                id="llm-recordar"
                checked={recordar}
                onCheckedChange={(valor) => setRecordar(valor === true)}
                className="mt-0.5"
              />
              <Label htmlFor="llm-recordar" className="font-normal leading-5">
                Recordar en esta pestaña
                <span className="block text-xs text-muted-foreground">
                  Sin marcar, se pierde al recargar. Marcada, dura hasta cerrar la pestaña o tu
                  sesión. No la marques en un equipo compartido.
                </span>
              </Label>
            </div>

            <ul className="space-y-1.5 rounded-lg bg-muted/60 p-3 text-xs text-muted-foreground">
              <li className="flex gap-2">
                <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-700" aria-hidden />
                No la guardamos: viaja cifrada en cada consulta, se usa una vez y se descarta.
              </li>
              <li className="flex gap-2">
                <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-700" aria-hidden />
                Es una demo: usa una clave con límite de gasto y no la compartas.
              </li>
            </ul>

            <DialogFooter className="gap-2 sm:justify-between">
              <Button type="button" variant="ghost" onClick={olvidar} disabled={!configurada}>
                Olvidar clave
              </Button>
              <Button type="submit" disabled={!listo}>
                Guardar
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
