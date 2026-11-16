// Clave de IA del usuario (BYOK).
//
// Dónde vive:
//  - Por defecto, solo en memoria de esta pestaña: se pierde al recargar.
//  - Si el usuario marca "recordar en esta pestaña", además en sessionStorage,
//    que el navegador borra al cerrar la pestaña.
//  - Nunca en localStorage ni en el servidor.
// Se borra siempre al cerrar sesión, también desde otra pestaña.

export interface CredencialLlm {
  proveedor: string;
  modelo: string;
  clave: string;
  recordar: boolean;
}

const CLAVE_SESION = "humanaiz.llm";

function leerGuardada(): CredencialLlm | null {
  try {
    const texto = sessionStorage.getItem(CLAVE_SESION);
    if (!texto) return null;
    const valor = JSON.parse(texto) as Partial<CredencialLlm>;
    if (
      typeof valor.proveedor === "string" &&
      typeof valor.modelo === "string" &&
      typeof valor.clave === "string" &&
      valor.clave
    ) {
      return { proveedor: valor.proveedor, modelo: valor.modelo, clave: valor.clave, recordar: true };
    }
  } catch {
    // sessionStorage no disponible o contenido dañado: se ignora.
  }
  return null;
}

function borrarGuardada(): void {
  try {
    sessionStorage.removeItem(CLAVE_SESION);
  } catch {
    // Sin sessionStorage no hay nada que borrar.
  }
}

let actual: CredencialLlm | null = leerGuardada();
const suscriptores = new Set<() => void>();

function avisar(): void {
  for (const suscriptor of suscriptores) suscriptor();
}

export const llmStore = {
  get: (): CredencialLlm | null => actual,

  subscribe(suscriptor: () => void): () => void {
    suscriptores.add(suscriptor);
    return () => suscriptores.delete(suscriptor);
  },

  guardar(credencial: CredencialLlm): void {
    actual = { ...credencial, clave: credencial.clave.trim() };
    if (actual.recordar) {
      try {
        sessionStorage.setItem(CLAVE_SESION, JSON.stringify(actual));
      } catch {
        actual = { ...actual, recordar: false };
      }
    } else {
      borrarGuardada();
    }
    avisar();
  },

  olvidar(): void {
    actual = null;
    borrarGuardada();
    avisar();
  },
};
