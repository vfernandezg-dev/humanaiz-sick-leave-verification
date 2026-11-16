import { definir } from "../definir";

// Vocabulario común. "Estado" es la decisión de RRHH; "lectura con IA" es la
// sugerencia automática: usan palabras distintas a propósito para no confundirlas.
export const comun = definir({
  es: {
    tituloDocumento: "HumanAIz · Prototipo de concurso",
    rol: { colaborador: "Colaborador", analista_rrhh: "Analista de RRHH" },
    estado: { Pendiente: "Pendiente", Aprobado: "Aprobado", Rechazado: "Rechazado" },
    lectura: {
      Aprobado: {
        etiqueta: "Sin observaciones",
        descripcion: "Los datos del certificado coinciden con la ficha del colaborador.",
      },
      Observado: {
        etiqueta: "Para revisar",
        descripcion: "Hay datos que la IA no pudo confirmar o que no cuadran del todo.",
      },
      Rechazado: {
        etiqueta: "Con problemas",
        descripcion: "Hay datos que no coinciden con la ficha o el documento no parece válido.",
      },
    },
    tipoDocumento: {
      citt: "CITT (EsSalud)",
      certificado_particular: "Certificado particular",
      otro: "Otro documento",
    },
    dias: (n: number) => `${n} ${n === 1 ? "día" : "días"}`,
    explicacion: {
      muestra: "Es un ejemplo incluido en la demostración: puedes verlo, pero no modificarlo.",
      aprobado: (periodo: string | null) =>
        periodo ? `RRHH aprobó el descanso (${periodo}).` : "RRHH aprobó el descanso.",
      rechazado: "RRHH rechazó el descanso. El motivo está en la sección «Decisión de RRHH».",
      decidir:
        "Revisa el certificado y decide. Si quieres una segunda opinión, pide antes una lectura con IA (es opcional).",
      propioRRHH: "Es tu propio descanso: lo revisará otra persona de RRHH.",
      pendiente:
        "Tu certificado está registrado. RRHH lo revisará y confirmará las fechas; vuelve a esta página para ver la decisión.",
    },
    acciones: {
      cancelar: "Cancelar",
      guardar: "Guardar",
      cerrar: "Cerrar",
      reintentar: "Reintentar",
      anterior: "Anterior",
      siguiente: "Siguiente",
    },
    paginacion: (desde: number, hasta: number, total: number, cosa: string) =>
      `Mostrando ${desde}–${hasta} de ${total} ${cosa}`,
    sinDato: "—",
  },
  en: {
    tituloDocumento: "HumanAIz · Contest prototype",
    rol: { colaborador: "Employee", analista_rrhh: "HR analyst" },
    estado: { Pendiente: "Pending", Aprobado: "Approved", Rechazado: "Rejected" },
    lectura: {
      Aprobado: {
        etiqueta: "No issues found",
        descripcion: "The certificate details match the employee's record.",
      },
      Observado: {
        etiqueta: "Needs review",
        descripcion: "Some details couldn't be confirmed by the AI or don't quite add up.",
      },
      Rechazado: {
        etiqueta: "Problems found",
        descripcion: "Some details don't match the record, or the document doesn't look valid.",
      },
    },
    tipoDocumento: {
      citt: "CITT (EsSalud)",
      certificado_particular: "Private medical certificate",
      otro: "Other document",
    },
    dias: (n: number) => `${n} ${n === 1 ? "day" : "days"}`,
    explicacion: {
      muestra: "This is a sample included in the demo: you can view it, but not change it.",
      aprobado: (periodo: string | null) =>
        periodo ? `HR approved the sick leave (${periodo}).` : "HR approved the sick leave.",
      rechazado: "HR rejected the sick leave. The reason is in the “HR decision” section.",
      decidir:
        "Review the certificate and decide. If you'd like a second opinion, request an AI reading first (optional).",
      propioRRHH: "This is your own sick leave: another HR analyst will review it.",
      pendiente:
        "Your certificate has been submitted. HR will review it and confirm the dates; come back to this page to see the decision.",
    },
    acciones: {
      cancelar: "Cancel",
      guardar: "Save",
      cerrar: "Close",
      reintentar: "Try again",
      anterior: "Previous",
      siguiente: "Next",
    },
    paginacion: (desde: number, hasta: number, total: number, cosa: string) =>
      `Showing ${desde}–${hasta} of ${total} ${cosa}`,
    sinDato: "—",
  },
});
