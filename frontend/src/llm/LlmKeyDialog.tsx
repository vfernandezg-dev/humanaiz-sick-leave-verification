import { useEffect, useState } from "react";
import { KeyRound, ShieldCheck } from "lucide-react";
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
import { llmStore } from "./store";

interface Props {
  abierto: boolean;
  onCambio: (abierto: boolean) => void;
}

const CLAVE_MIN = 16;

export function LlmKeyDialog({ abierto, onCambio }: Props) {
  const { data: config } = useConfig();
  const { toast } = useToast();
  const proveedores = config?.llm.proveedores ?? [];

  const [proveedor, setProveedor] = useState("");
  const [modelo, setModelo] = useState("");
  const [clave, setClave] = useState("");
  const [recordar, setRecordar] = useState(false);

  // Al abrir, parte de lo que ya esté configurado. La clave guardada no se
  // vuelve a mostrar: para cambiarla hay que escribir una nueva.
  useEffect(() => {
    if (!abierto) return;
    const actual = llmStore.get();
    const inicial = proveedores.find((p) => p.id === actual?.proveedor) ?? proveedores[0];
    setProveedor(inicial?.id ?? "");
    setModelo(
      inicial?.modelos.find((m) => m.id === actual?.modelo)?.id ??
        inicial?.modelos.find((m) => m.predeterminado)?.id ??
        "",
    );
    setClave("");
    setRecordar(actual?.recordar ?? false);
    // `proveedores` cambia de identidad en cada render; basta reaccionar a `abierto`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abierto, config]);

  const seleccionado = proveedores.find((p) => p.id === proveedor);
  const configurada = llmStore.get();
  const claveFinal = clave.trim() || (configurada?.proveedor === proveedor ? configurada.clave : "");
  const valida = claveFinal.length >= CLAVE_MIN && !/\s/.test(claveFinal);

  const cambiarProveedor = (id: string) => {
    setProveedor(id);
    const nuevo = proveedores.find((p) => p.id === id);
    setModelo(nuevo?.modelos.find((m) => m.predeterminado)?.id ?? "");
    setClave("");
  };

  const guardar = (evento: React.FormEvent) => {
    evento.preventDefault();
    if (!valida || !proveedor || !modelo) return;
    llmStore.guardar({ proveedor, modelo, clave: claveFinal, recordar });
    toast({ title: "Clave de IA lista", description: "Ya puedes analizar documentos." });
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
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5" />
            Tu clave de IA
          </DialogTitle>
          <DialogDescription>
            El análisis de documentos usa tu propia cuenta del proveedor de IA. Tú eliges el
            proveedor y el modelo, y el consumo se factura a tu clave.
          </DialogDescription>
        </DialogHeader>

        {proveedores.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No hay proveedores de IA habilitados en este momento.
          </p>
        ) : (
          // autoComplete="off": no es un formulario de acceso y el navegador no
          // debe ofrecer guardar la clave como si fuera una contraseña.
          <form onSubmit={guardar} className="space-y-4" autoComplete="off">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="llm-proveedor">Proveedor</Label>
                {/* Radix emite un cambio a "" cuando cambian las opciones: se ignora. */}
                <Select value={proveedor} onValueChange={(v) => v && cambiarProveedor(v)}>
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
                <Label htmlFor="llm-modelo">Modelo</Label>
                <Select key={proveedor} value={modelo} onValueChange={(v) => v && setModelo(v)}>
                  <SelectTrigger id="llm-modelo">
                    <SelectValue placeholder="Elige un modelo" />
                  </SelectTrigger>
                  <SelectContent>
                    {seleccionado?.modelos.map((m) => (
                      <SelectItem key={m.id} value={m.id}>
                        {m.nombre}
                        {m.predeterminado ? " (recomendado)" : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="llm-clave">Clave de API</Label>
              <Input
                id="llm-clave"
                name="llm-clave"
                type="password"
                value={clave}
                onChange={(e) => setClave(e.target.value)}
                placeholder={
                  configurada?.proveedor === proveedor
                    ? "Clave configurada. Escribe otra para reemplazarla"
                    : (seleccionado?.formato_clave ?? "")
                }
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="off"
                spellCheck={false}
                data-1p-ignore
                data-lpignore="true"
                data-bwignore
              />
              {clave.trim() !== "" && !valida && (
                <p className="text-xs text-destructive">
                  La clave parece incompleta. Cópiala entera, sin espacios.
                </p>
              )}
            </div>

            <div className="flex items-start gap-3">
              <Checkbox
                id="llm-recordar"
                checked={recordar}
                onCheckedChange={(valor) => setRecordar(valor === true)}
                className="mt-0.5"
              />
              <div className="space-y-1">
                <Label htmlFor="llm-recordar" className="font-normal">
                  Recordar en esta pestaña
                </Label>
                <p className="text-xs text-muted-foreground">
                  Sin marcar, la clave se pierde al recargar la página. Marcada, el navegador la
                  conserva hasta que cierres la pestaña o tu sesión. No la marques en un equipo
                  compartido.
                </p>
              </div>
            </div>

            <div className="flex gap-3 rounded-lg border bg-muted/50 p-3 text-xs text-muted-foreground">
              <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-success" />
              <p>
                Tu clave no se guarda en nuestros servidores. Viaja cifrada en cada análisis, se
                usa una sola vez para esa petición y se descarta. Se borra de este navegador al
                cerrar sesión.
              </p>
            </div>

            <DialogFooter className="gap-2 sm:justify-between">
              <Button type="button" variant="ghost" onClick={olvidar} disabled={!configurada}>
                Olvidar clave
              </Button>
              <Button type="submit" disabled={!valida || !proveedor || !modelo}>
                Guardar
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
