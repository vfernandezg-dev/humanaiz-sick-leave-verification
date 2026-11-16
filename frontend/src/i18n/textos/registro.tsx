import { definir } from "../definir";

export const registro = definir({
  es: {
    volver: "Mis descansos",
    titulo: "Registrar descanso médico",
    descripcion:
      "Sube una foto o captura del certificado. RRHH lo revisará y confirmará las fechas: no hace falta que las escribas.",
    pasos: { imagen: "Imagen del certificado", sede: "Sede", lectura: "Lectura con IA (opcional)" },
    ayuda: (maxMb: number) => `Solo imágenes JPG, PNG o WebP · máximo ${maxMb} MB`,
    rechazo: {
      pdf: "Los PDF no se admiten. Sube una foto o una captura del certificado.",
      heic: "Las fotos HEIC no se admiten. Conviértela a JPG o compártela como «Más compatible».",
      pesada: (maxMb: number) => `La imagen pesa más de ${maxMb} MB y no se pudo reducir.`,
      pequena: (minLado: number) =>
        `La imagen es demasiado pequeña para leer un documento (mínimo ${minLado} px por lado).`,
      ilegible: "No se pudo abrir la imagen. Puede estar dañada.",
      formato: "Solo se aceptan imágenes JPG, PNG o WebP.",
    },
    reducida: (maxLado: number) =>
      `Reducimos la foto a ${maxLado} px de lado para subirla más rápido. Es el tamaño con el que se guarda, así que no se pierde detalle.`,
    ejemplos: {
      intro:
        "¿No tienes un documento de prueba? Usa un certificado ficticio generado con los datos de tu ficha. Cada variante produce un resultado distinto en la lectura con IA:",
      valido: "Válido",
      observado: "Con observaciones",
      otraPersona: "De otra persona",
      citt: "Formato CITT",
      generando: "Generando…",
      error: "No se pudo generar el ejemplo.",
    },
    sede: {
      placeholder: "Ej.: Lima Centro",
      ayuda: "Se completa con la sede de tu ficha. Cámbiala si hace falta.",
      falta: "Indica la sede.",
    },
    lectura: {
      opcion: "Leer el certificado con IA al terminar, usando mi clave.",
      detalle: "Extrae los datos y los compara con tu ficha. Tarda menos de un minuto.",
      sinClaveAntes: "Si quieres que la IA revise el documento, ",
      sinClaveEnlace: "configura tu clave de IA",
      sinClaveDespues: ". También puedes hacerlo después.",
    },
    confirmacion:
      "Confirmo que la imagen es un certificado ficticio o de prueba, sin datos reales de ninguna persona, y que cumple los términos de uso.",
    faltaConfirmar: "Esta demo no admite documentos reales: confirma para continuar.",
    faltaArchivo: "Elige el archivo del certificado.",
    subiendo: "Subiendo…",
    registrar: "Registrar descanso",
    registrado: "Descanso registrado",
    registradoDetalle: "RRHH lo revisará y confirmará las fechas.",
    noSeRegistro: "No se pudo registrar el descanso.",
    zona: {
      arrastra: "Arrastra la imagen aquí o ",
      elige: "elige una",
      preparando: "Preparando la imagen…",
      cambiar: "Cambiar",
      quitar: "Quitar archivo",
    },
  },
  en: {
    volver: "My sick leaves",
    titulo: "Submit a sick leave",
    descripcion:
      "Upload a photo or screenshot of the certificate. HR will review it and confirm the dates: you don't need to type them.",
    pasos: { imagen: "Certificate image", sede: "Location", lectura: "AI reading (optional)" },
    ayuda: (maxMb: number) => `JPG, PNG or WebP images only · up to ${maxMb} MB`,
    rechazo: {
      pdf: "PDFs aren't accepted. Upload a photo or a screenshot of the certificate.",
      heic: "HEIC photos aren't accepted. Convert it to JPG or share it as “Most Compatible”.",
      pesada: (maxMb: number) => `The image is larger than ${maxMb} MB and couldn't be reduced.`,
      pequena: (minLado: number) =>
        `The image is too small to read a document (at least ${minLado} px per side).`,
      ilegible: "The image couldn't be opened. It may be damaged.",
      formato: "Only JPG, PNG or WebP images are accepted.",
    },
    reducida: (maxLado: number) =>
      `We resized the photo to ${maxLado} px per side to upload it faster. That's the size it's stored at, so no detail is lost.`,
    ejemplos: {
      intro:
        "Don't have a test document? Use a fictitious certificate generated with your record's details. Each variant produces a different AI reading result:",
      valido: "Valid",
      observado: "With issues",
      otraPersona: "Someone else's",
      citt: "CITT format",
      generando: "Generating…",
      error: "The sample couldn't be generated.",
    },
    sede: {
      placeholder: "E.g.: Lima Centro",
      ayuda: "Filled in from your record's location. Change it if needed.",
      falta: "Enter the location.",
    },
    lectura: {
      opcion: "Read the certificate with AI when done, using my key.",
      detalle: "It extracts the details and compares them with your record. It takes less than a minute.",
      sinClaveAntes: "If you want the AI to review the document, ",
      sinClaveEnlace: "set up your AI key",
      sinClaveDespues: ". You can also do it later.",
    },
    confirmacion:
      "I confirm the image is a fictitious or test certificate, with no real data about anyone, and that it complies with the terms of use.",
    faltaConfirmar: "This demo doesn't accept real documents: confirm to continue.",
    faltaArchivo: "Choose the certificate file.",
    subiendo: "Uploading…",
    registrar: "Submit sick leave",
    registrado: "Sick leave submitted",
    registradoDetalle: "HR will review it and confirm the dates.",
    noSeRegistro: "The sick leave couldn't be submitted.",
    zona: {
      arrastra: "Drag the image here or ",
      elige: "choose one",
      preparando: "Preparing the image…",
      cambiar: "Change",
      quitar: "Remove file",
    },
  },
});
