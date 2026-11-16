import { describe, expect, it } from "vitest";
import type { ProveedorLlm } from "@/lib/types";
import { detectarProveedor } from "./detectar";

function proveedor(id: string, prefijos: string[]): ProveedorLlm {
  return {
    id,
    nombre: id,
    formato_clave: "",
    prefijos_clave: prefijos,
    url_claves: "https://example.com",
    max_imagenes: 20,
    modelos: [],
  };
}

const PROVEEDORES = [
  proveedor("anthropic", ["sk-ant-"]),
  proveedor("openai", ["sk-"]),
  proveedor("gemini", ["AIza"]),
  proveedor("openrouter", ["sk-or-"]),
  proveedor("xai", ["xai-"]),
  proveedor("mistral", []),
  proveedor("groq", ["gsk_"]),
];

describe("detectarProveedor", () => {
  it.each([
    ["sk-ant-api03-abcdefghijklmnop", "anthropic"],
    ["sk-or-v1-abcdefghijklmnop", "openrouter"],
    ["sk-proj-abcdefghijklmnop", "openai"],
    ["sk-abcdefghijklmnop", "openai"],
    ["AIzaSyA1234567890abcdef", "gemini"],
    ["xai-abcdefghijklmnop", "xai"],
    ["gsk_abcdefghijklmnop", "groq"],
    ["  sk-ant-con-espacios  ", "anthropic"],
  ])("%s -> %s", (clave, esperado) => {
    expect(detectarProveedor(clave, PROVEEDORES)?.id).toBe(esperado);
  });

  it("no adivina cuando el prefijo no es reconocible", () => {
    expect(detectarProveedor("a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6", PROVEEDORES)).toBeNull();
    expect(detectarProveedor("", PROVEEDORES)).toBeNull();
  });
});
