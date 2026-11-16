import { Link } from "react-router-dom";
import { MapPinOff } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { PublicShell } from "@/components/shell/PublicShell";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <PublicShell>
      <div className="mx-auto max-w-md">
        <EmptyState
          icono={MapPinOff}
          titulo="Esta página no existe"
          descripcion="Puede que el enlace esté mal escrito o que el contenido ya no exista."
          accion={
            <Button asChild variant="outline">
              <Link to="/">Volver al inicio</Link>
            </Button>
          }
        />
      </div>
    </PublicShell>
  );
}
