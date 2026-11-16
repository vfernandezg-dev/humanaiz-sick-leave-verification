import { definir } from "../definir";

/** Mensaje de una comprobación según su resultado. `falla` puede depender de los datos leídos. */
interface TextoRegla {
  ok: string;
  falla: string;
  no_evaluada: string;
}

// Las comprobaciones las calcula el backend (scanning/rules.py) y guarda su
// mensaje en español. Aquí se reescriben desde el código de cada regla para
// mostrarlas en el idioma activo; si aparece un código nuevo, se usa el
// mensaje del servidor.
const NO_EVALUADA_FECHAS_ES = "No se evaluó: faltan fechas.";
const NO_EVALUADA_FECHAS_EN = "Not checked: dates are missing.";

export const detalle = definir({
  es: {
    titulo: "Descanso médico",
    volver: { solicitudes: "Solicitudes", inicio: "Inicio", misDescansos: "Mis descansos" },
    noEncontrado: "No encontramos este descanso",
    noEncontradoDetalle:
      "Puede que se haya eliminado (en la demo todo se borra pasado un tiempo) o que no tengas acceso.",
    errorCarga: "No se pudo cargar el descanso",
    errorCargaDetalle: "Recarga la página para intentarlo de nuevo.",
    dni: (dni: string) => `DNI ${dni}`,
    sede: (sede: string) => `Sede ${sede}`,
    fechasPorConfirmar: "Fechas por confirmar",
    eliminado: "Descanso eliminado",
    eliminadoDetalle: "También se borró su documento.",
    noSeEliminó: "No se pudo eliminar",
    intentaDeNuevo: "Inténtalo de nuevo.",
    lectura: {
      titulo: "Lectura con IA",
      descripcion:
        "Una segunda opinión automática: la IA lee el certificado y lo compara con la ficha del colaborador.",
      volverALeer: "Volver a leer",
      leyendo: "Leyendo el certificado. Puede tardar hasta un par de minutos; puedes seguir navegando.",
      sinLeer: (conClave: boolean) =>
        `Aún no se ha leído. Es opcional y usa ${conClave ? "tu clave configurada" : "tu propia clave de IA"}.`,
      leer: "Leer con IA",
      noSePidio: "No se pidió una lectura con IA para este descanso.",
    },
    decision: {
      titulo: "Tu decisión",
      descripcion: "Es la que cuenta: la lectura con IA solo es una ayuda.",
      seccionRRHH: "Decisión de RRHH",
      resultado: "Resultado",
      periodo: "Periodo confirmado",
      fecha: "Fecha",
      comentario: "Comentario",
    },
    eliminar: {
      boton: "Eliminar este descanso",
      pregunta: "¿Eliminar este descanso?",
      detalle: "Se borrarán la solicitud, el documento y sus lecturas con IA. No se puede deshacer.",
      confirmar: "Eliminar",
      eliminando: "Eliminando…",
    },
    progreso: {
      etiqueta: "Progreso de la solicitud",
      registrado: "Registrado",
      lectura: "Lectura con IA",
      enCurso: "En curso…",
      opcional: "Opcional",
      noSeUso: "No se usó",
      decision: "Decisión de RRHH",
      enEspera: "En espera",
    },
    visor: {
      alt: (pagina: number, total: number) => `Certificado médico, página ${pagina} de ${total}`,
      noCargo: "No se pudo cargar el documento.",
      paginaAnterior: "Página anterior",
      paginaSiguiente: "Página siguiente",
      pagina: (pagina: number, total: number) => `Página ${pagina} de ${total}`,
      optimizada: "Vista optimizada, sin metadatos",
      descargar: "Descargar imagen",
      descargando: "Descargando…",
      noSeDescargo: "No se pudo descargar",
    },
    formulario: {
      etiqueta: "Decisión",
      aprobar: "Aprobar",
      rechazar: "Rechazar",
      elige: "Elige si apruebas o rechazas el descanso.",
      inicio: "Inicio del descanso",
      fin: "Fin del descanso",
      fechasDeLaIA:
        "Fechas propuestas por la lectura con IA: compáralas con el certificado antes de confirmar.",
      obligatorias: "Obligatorias para aprobar.",
      opcionales: "Opcionales al rechazar.",
      comentario: "Comentario para el colaborador",
      obligatorio: " (obligatorio)",
      opcional: " (opcional)",
      ejemploRechazo: "Por ejemplo: el certificado está a nombre de otra persona.",
      faltanFechas: "Indica la fecha de inicio y la de fin para aprobar.",
      finAntesDeInicio: "La fecha de fin no puede ser anterior a la de inicio.",
      faltaComentario: "Explica el motivo del rechazo: el colaborador lo verá.",
      noSeRegistro: "No se pudo registrar la decisión.",
      guardando: "Guardando…",
      confirmarAprobacion: "Confirmar aprobación",
      confirmarRechazo: "Confirmar rechazo",
      aprobado: "Descanso aprobado",
      rechazado: "Descanso rechazado",
    },
    analisis: {
      verComprobaciones: (total: number, conObservaciones: number) =>
        `Ver las ${total} comprobaciones${conObservaciones > 0 ? ` (${conObservaciones} con observaciones)` : ""} y los datos leídos`,
      importante: "(importante)",
      noSePudo: "No se pudo comprobar.",
      loQueLeyo: "Lo que leyó la IA en el documento",
      datos: {
        tipo: "Tipo",
        dni: "DNI",
        nombre: "Nombre",
        inicio: "Inicio",
        fin: "Fin",
        dias: "Días indicados",
        citt: "N.º de CITT",
        medico: "Médico (CMP)",
        contingencia: "Contingencia",
      },
      ejemplo: "Lectura de ejemplo incluida en la demo",
      pie: (cuando: string, quien: string) =>
        `${cuando} · pedida por ${quien}. La IA puede equivocarse: es una ayuda, la decisión la toma RRHH.`,
      comentario: {
        Aprobado: () => "El documento supera todas las validaciones automáticas.",
        Observado: (n: number) =>
          `El documento parece válido, pero hay ${n} punto(s) que conviene revisar a mano.`,
        Rechazado: (n: number) =>
          `Se detectaron ${n} problema(s) que impiden validar el documento automáticamente.`,
      },
      reglas: {
        es_certificado_medico: {
          ok: "El documento es un certificado de descanso médico.",
          falla: "El documento no parece un certificado de descanso médico.",
          no_evaluada: "",
        },
        documento_legible: {
          ok: "El documento es legible.",
          falla: "El documento no se puede leer con claridad.",
          no_evaluada: "",
        },
        dni_coincide: {
          ok: "El DNI del documento coincide con el del colaborador.",
          falla: "El DNI del documento no coincide con el del colaborador.",
          no_evaluada: "El documento no muestra un DNI legible.",
        },
        nombre_coincide: {
          ok: "El nombre del documento coincide con el del colaborador.",
          falla: "El nombre del documento no coincide con el del colaborador.",
          no_evaluada: "El documento no muestra un nombre legible.",
        },
        fechas_presentes: {
          ok: "El documento indica las fechas de inicio y fin.",
          falla: "No se pudieron leer las fechas de inicio y fin del descanso.",
          no_evaluada: "",
        },
        fechas_coherentes: {
          ok: "La fecha de fin no es anterior a la de inicio.",
          falla: "La fecha de fin es anterior a la de inicio.",
          no_evaluada: NO_EVALUADA_FECHAS_ES,
        },
        citt_presente: {
          ok: "El CITT tiene número.",
          falla: "El documento es un CITT pero no se lee su número.",
          no_evaluada: "",
        },
        dias_coinciden: {
          ok: "Los días indicados coinciden con las fechas.",
          falla: "Los días indicados no coinciden con las fechas.",
          no_evaluada: "No se evaluó: faltan los días o las fechas.",
        },
        codigo_medico_presente: {
          ok: "Figura el número de colegiatura del médico.",
          falla: "No se lee el número de colegiatura (CMP) del médico.",
          no_evaluada: "",
        },
        contingencia_reconocida: {
          ok: "La contingencia indicada es de un tipo conocido.",
          falla: "La contingencia indicada no es de un tipo conocido.",
          no_evaluada: "El documento no indica la contingencia.",
        },
        duracion_razonable: {
          ok: "La duración está dentro de lo habitual.",
          falla: "El descanso dura más de lo habitual.",
          no_evaluada: NO_EVALUADA_FECHAS_ES,
        },
        vigencia: {
          ok: "Las fechas son recientes.",
          falla: "Las fechas del descanso son muy antiguas o muy futuras.",
          no_evaluada: NO_EVALUADA_FECHAS_ES,
        },
        sin_solapamiento: {
          ok: "No se cruza con otros descansos aprobados.",
          falla: "Las fechas se cruzan con otro descanso ya aprobado.",
          no_evaluada: NO_EVALUADA_FECHAS_ES,
        },
        documento_no_duplicado: {
          ok: "El documento no se había presentado antes.",
          falla: "Este documento (o su número de CITT) ya se presentó antes.",
          no_evaluada: "",
        },
      } satisfies Record<string, TextoRegla>,
    },
    avisos: {
      configuraClave: "Configura tu clave de IA",
      configuraClaveDetalle: "La lectura con IA es opcional y usa tu propia clave.",
      lista: (etiqueta: string) => `Lectura con IA: ${etiqueta.toLowerCase()}`,
      enCurso: "Lectura en curso",
      enCursoDetalle: "Este documento ya se está leyendo con IA. El resultado aparecerá aquí.",
      fallo: "No se pudo completar la lectura",
      falloGenerico: "No se pudo completar el análisis.",
    },
  },
  en: {
    titulo: "Sick leave",
    volver: { solicitudes: "Requests", inicio: "Home", misDescansos: "My sick leaves" },
    noEncontrado: "We couldn't find this sick leave",
    noEncontradoDetalle:
      "It may have been deleted (in the demo everything is erased after a while), or you may not have access.",
    errorCarga: "The sick leave couldn't be loaded",
    errorCargaDetalle: "Reload the page to try again.",
    dni: (dni: string) => `ID ${dni}`,
    sede: (sede: string) => `Location: ${sede}`,
    fechasPorConfirmar: "Dates to be confirmed",
    eliminado: "Sick leave deleted",
    eliminadoDetalle: "Its document was deleted too.",
    noSeEliminó: "It couldn't be deleted",
    intentaDeNuevo: "Please try again.",
    lectura: {
      titulo: "AI reading",
      descripcion:
        "An automatic second opinion: the AI reads the certificate and compares it with the employee's record.",
      volverALeer: "Read again",
      leyendo: "Reading the certificate. It can take up to a couple of minutes; you can keep browsing.",
      sinLeer: (conClave: boolean) =>
        `It hasn't been read yet. It's optional and uses ${conClave ? "the key you set up" : "your own AI key"}.`,
      leer: "Read with AI",
      noSePidio: "No AI reading was requested for this sick leave.",
    },
    decision: {
      titulo: "Your decision",
      descripcion: "This is what counts: the AI reading is only an aid.",
      seccionRRHH: "HR decision",
      resultado: "Outcome",
      periodo: "Confirmed period",
      fecha: "Date",
      comentario: "Comment",
    },
    eliminar: {
      boton: "Delete this sick leave",
      pregunta: "Delete this sick leave?",
      detalle: "The request, the document and its AI readings will be deleted. This can't be undone.",
      confirmar: "Delete",
      eliminando: "Deleting…",
    },
    progreso: {
      etiqueta: "Request progress",
      registrado: "Submitted",
      lectura: "AI reading",
      enCurso: "In progress…",
      opcional: "Optional",
      noSeUso: "Not used",
      decision: "HR decision",
      enEspera: "Waiting",
    },
    visor: {
      alt: (pagina: number, total: number) => `Medical certificate, page ${pagina} of ${total}`,
      noCargo: "The document couldn't be loaded.",
      paginaAnterior: "Previous page",
      paginaSiguiente: "Next page",
      pagina: (pagina: number, total: number) => `Page ${pagina} of ${total}`,
      optimizada: "Optimized view, no metadata",
      descargar: "Download image",
      descargando: "Downloading…",
      noSeDescargo: "The download failed",
    },
    formulario: {
      etiqueta: "Decision",
      aprobar: "Approve",
      rechazar: "Reject",
      elige: "Choose whether to approve or reject the sick leave.",
      inicio: "Leave start date",
      fin: "Leave end date",
      fechasDeLaIA: "Dates suggested by the AI reading: compare them with the certificate before confirming.",
      obligatorias: "Required to approve.",
      opcionales: "Optional when rejecting.",
      comentario: "Comment for the employee",
      obligatorio: " (required)",
      opcional: " (optional)",
      ejemploRechazo: "For example: the certificate is issued to someone else.",
      faltanFechas: "Enter the start and end dates to approve.",
      finAntesDeInicio: "The end date can't be earlier than the start date.",
      faltaComentario: "Explain why it's being rejected: the employee will see it.",
      noSeRegistro: "The decision couldn't be saved.",
      guardando: "Saving…",
      confirmarAprobacion: "Confirm approval",
      confirmarRechazo: "Confirm rejection",
      aprobado: "Sick leave approved",
      rechazado: "Sick leave rejected",
    },
    analisis: {
      verComprobaciones: (total: number, conObservaciones: number) =>
        `See the ${total} checks${conObservaciones > 0 ? ` (${conObservaciones} flagged)` : ""} and the data read`,
      importante: "(important)",
      noSePudo: "Couldn't be checked.",
      loQueLeyo: "What the AI read in the document",
      datos: {
        tipo: "Type",
        dni: "ID number (DNI)",
        nombre: "Name",
        inicio: "Start",
        fin: "End",
        dias: "Days stated",
        citt: "CITT no.",
        medico: "Doctor (CMP)",
        contingencia: "Contingency",
      },
      ejemplo: "Sample reading included in the demo",
      pie: (cuando: string, quien: string) =>
        `${cuando} · requested by ${quien}. The AI can make mistakes: it's an aid, HR makes the decision.`,
      comentario: {
        Aprobado: () => "The document passes all automatic checks.",
        Observado: (n: number) =>
          `The document looks valid, but ${n === 1 ? "1 point is" : `${n} points are`} worth reviewing manually.`,
        Rechazado: (n: number) =>
          `${n === 1 ? "1 problem was" : `${n} problems were`} found that prevent validating the document automatically.`,
      },
      reglas: {
        es_certificado_medico: {
          ok: "The document is a sick leave medical certificate.",
          falla: "The document doesn't look like a sick leave medical certificate.",
          no_evaluada: "",
        },
        documento_legible: {
          ok: "The document is legible.",
          falla: "The document can't be read clearly.",
          no_evaluada: "",
        },
        dni_coincide: {
          ok: "The ID number on the document matches the employee's.",
          falla: "The ID number on the document doesn't match the employee's.",
          no_evaluada: "The document doesn't show a legible ID number.",
        },
        nombre_coincide: {
          ok: "The name on the document matches the employee's.",
          falla: "The name on the document doesn't match the employee's.",
          no_evaluada: "The document doesn't show a legible name.",
        },
        fechas_presentes: {
          ok: "The document states the start and end dates.",
          falla: "The start and end dates of the leave couldn't be read.",
          no_evaluada: "",
        },
        fechas_coherentes: {
          ok: "The end date isn't earlier than the start date.",
          falla: "The end date is earlier than the start date.",
          no_evaluada: NO_EVALUADA_FECHAS_EN,
        },
        citt_presente: {
          ok: "The CITT has a number.",
          falla: "The document is a CITT, but its number can't be read.",
          no_evaluada: "",
        },
        dias_coinciden: {
          ok: "The days stated match the dates.",
          falla: "The days stated don't match the dates.",
          no_evaluada: "Not checked: the days or the dates are missing.",
        },
        codigo_medico_presente: {
          ok: "The doctor's license number is shown.",
          falla: "The doctor's license number (CMP) can't be read.",
          no_evaluada: "",
        },
        contingencia_reconocida: {
          ok: "The stated contingency is a known type.",
          falla: "The stated contingency isn't a known type.",
          no_evaluada: "The document doesn't state the contingency.",
        },
        duracion_razonable: {
          ok: "The duration is within the usual range.",
          falla: "The leave is longer than usual.",
          no_evaluada: NO_EVALUADA_FECHAS_EN,
        },
        vigencia: {
          ok: "The dates are recent.",
          falla: "The leave dates are too old or too far in the future.",
          no_evaluada: NO_EVALUADA_FECHAS_EN,
        },
        sin_solapamiento: {
          ok: "It doesn't overlap with other approved sick leaves.",
          falla: "The dates overlap with another sick leave that was already approved.",
          no_evaluada: NO_EVALUADA_FECHAS_EN,
        },
        documento_no_duplicado: {
          ok: "The document hadn't been submitted before.",
          falla: "This document (or its CITT number) was already submitted.",
          no_evaluada: "",
        },
      } satisfies Record<string, TextoRegla>,
    },
    avisos: {
      configuraClave: "Set up your AI key",
      configuraClaveDetalle: "The AI reading is optional and uses your own key.",
      lista: (etiqueta: string) => `AI reading: ${etiqueta.toLowerCase()}`,
      enCurso: "Reading in progress",
      enCursoDetalle: "This document is already being read by the AI. The result will appear here.",
      fallo: "The reading couldn't be completed",
      falloGenerico: "The analysis couldn't be completed.",
    },
  },
});
