import { describe, expect, it } from "vitest";
import { enlaceContacto } from "./contacto";

describe("enlaceContacto", () => {
  it("acepta correos y URLs http(s)", () => {
    expect(enlaceContacto("equipo@example.com")).toBe("mailto:equipo@example.com");
    expect(enlaceContacto(" https://example.com/contacto ")).toBe("https://example.com/contacto");
  });

  it("rechaza cualquier otro esquema o texto", () => {
    expect(enlaceContacto("javascript:alert(1)")).toBeNull();
    expect(enlaceContacto("data:text/html,hola")).toBeNull();
    expect(enlaceContacto("Mesa de partes, piso 3")).toBeNull();
    expect(enlaceContacto("")).toBeNull();
    expect(enlaceContacto(null)).toBeNull();
  });
});
