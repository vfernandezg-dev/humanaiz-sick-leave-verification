import { Link } from "react-router-dom";
import { MapPinOff } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { PublicShell } from "@/components/shell/PublicShell";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n/context";

export default function NotFound() {
  const { t } = useI18n();
  return (
    <PublicShell>
      <div className="mx-auto max-w-md">
        <EmptyState
          icono={MapPinOff}
          titulo={t.shell.noEncontrada.titulo}
          descripcion={t.shell.noEncontrada.descripcion}
          accion={
            <Button asChild variant="outline">
              <Link to="/">{t.shell.noEncontrada.volver}</Link>
            </Button>
          }
        />
      </div>
    </PublicShell>
  );
}
