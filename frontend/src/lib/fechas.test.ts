import { describe, expect, it } from "vitest";
import { diasInclusivos, formatoFecha, formatoFechaHora } from "./fechas";

describe("fechas de calendario", () => {
  it("muestra el mismo día que guarda la API, sin desfase por zona horaria", () => {
    // `new Date("2026-11-10")` es medianoche UTC: en Lima sería el día 9.
    expect(formatoFecha("2026-11-10")).toBe("10/11/2026");
    expect(formatoFecha("2026-01-01")).toBe("01/01/2026");
    expect(formatoFecha("2024-02-29")).toBe("29/02/2024");
  });

  it("devuelve una raya cuando no hay fecha o no es válida", () => {
    expect(formatoFecha(null)).toBe("—");
    expect(formatoFecha(undefined)).toBe("—");
    expect(formatoFecha("")).toBe("—");
    expect(formatoFecha("10/11/2026")).toBe("—");
    expect(formatoFechaHora(null)).toBe("—");
    expect(formatoFechaHora("no es fecha")).toBe("—");
  });

  it("cuenta los días incluyendo ambos extremos", () => {
    expect(diasInclusivos("2026-11-10", "2026-11-12")).toBe(3);
    expect(diasInclusivos("2026-11-10", "2026-11-10")).toBe(1);
    expect(diasInclusivos("2026-02-27", "2026-03-02")).toBe(4);
    expect(diasInclusivos("2026-11-10", "ayer")).toBeNull();
  });
});
