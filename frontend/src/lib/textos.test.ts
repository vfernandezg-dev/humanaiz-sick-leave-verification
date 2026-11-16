import { describe, expect, it } from "vitest";
import { explicacion, periodo } from "./textos";
import type { Descanso } from "./types";

function descanso(cambios: Partial<Descanso> = {}): Descanso {
  return {
    id: "d1",
    estado: "Pendiente",
    sede: "Lima",
    fecha_inicio: null,
    fecha_fin: null,
    comentario_rrhh: null,
    created_at: "2026-11-15T15:00:00Z",
    updated_at: "2026-11-15T15:00:00Z",
    decidido_at: null,
    colaborador: { id: "c1", dni: "40000001", nombres: "Ana", apellidos: "Pérez" },
    archivo: { mime: "image/jpeg", size_bytes: 1000, paginas: 1 },
    ultimo_analisis: null,
    analisis_en_curso: false,
    es_muestra: false,
    es_propio: true,
    permisos: { puede_analizar: true, puede_decidir: false, puede_eliminar: true },
    ...cambios,
  };
}

describe("periodo", () => {
  it("muestra fechas y duración, o nada si faltan", () => {
    expect(periodo({ fecha_inicio: "2026-11-10", fecha_fin: "2026-11-12" })).toBe(
      "10/11/2026 – 12/11/2026 · 3 días",
    );
    expect(periodo({ fecha_inicio: "2026-11-10", fecha_fin: "2026-11-10" })).toBe(
      "10/11/2026 – 10/11/2026 · 1 día",
    );
    expect(periodo({ fecha_inicio: null, fecha_fin: "2026-11-10" })).toBeNull();
  });
});

describe("explicacion", () => {
  it("adapta el mensaje al estado y a quién lo mira", () => {
    expect(explicacion(descanso(), false)).toMatch(/RRHH lo revisará/);
    expect(
      explicacion(
        descanso({
          es_propio: false,
          permisos: { puede_analizar: true, puede_decidir: true, puede_eliminar: false },
        }),
        true,
      ),
    ).toMatch(/^Revisa el certificado y decide/);
    expect(explicacion(descanso(), true)).toMatch(/otra persona de RRHH/);
    expect(
      explicacion(
        descanso({ estado: "Aprobado", fecha_inicio: "2026-11-10", fecha_fin: "2026-11-12" }),
        false,
      ),
    ).toBe("RRHH aprobó el descanso (10/11/2026 – 12/11/2026 · 3 días).");
    expect(explicacion(descanso({ estado: "Rechazado" }), false)).toMatch(/rechazó/);
    expect(explicacion(descanso({ es_muestra: true }), true)).toMatch(/ejemplo/);
  });
});
