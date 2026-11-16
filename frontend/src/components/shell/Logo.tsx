import { Link } from "react-router-dom";
import { NOMBRE_APP } from "@/lib/textos";

export function Logo() {
  return (
    <Link
      to="/"
      className="flex items-center gap-2 rounded-md font-semibold tracking-tight focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <img src="/favicon.svg" alt="" className="h-6 w-6" />
      {NOMBRE_APP}
      <span className="rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        Demo
      </span>
    </Link>
  );
}
