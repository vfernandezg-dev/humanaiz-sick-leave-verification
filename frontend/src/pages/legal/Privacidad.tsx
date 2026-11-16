import { Link } from "react-router-dom";
import { useConfig } from "@/hooks/queries";
import { useI18n } from "@/i18n/context";
import { Clausula, Contacto, DocumentoLegal } from "./DocumentoLegal";

// Si cambias este texto de forma sustancial, sube TERMINOS_VERSION en
// backend/src/humanaiz/legal.py: se pedirá aceptarlo de nuevo al ingresar.
// La versión en español es la de referencia; la inglesa es una traducción y
// debe mantenerse con las mismas cláusulas y numeración.

interface Datos {
  concurso: string;
  horas: number;
  dias: number;
}

export default function Privacidad() {
  const { data } = useConfig();
  const { t, idioma } = useI18n();
  const datos: Datos = {
    concurso: data?.proyecto.concurso ?? t.legal.unConcurso,
    horas: data?.demo.retencion_horas ?? 24,
    dias: data?.proyecto.retencion_registros_dias ?? 30,
  };
  return idioma === "en" ? <PrivacidadEn {...datos} /> : <PrivacidadEs {...datos} />;
}

function PrivacidadEs({ concurso, horas, dias }: Datos) {
  const { t } = useI18n();
  return (
    <DocumentoLegal
      titulo={t.legal.privacidad.titulo}
      resumen={
        <p>
          Tratamos lo mínimo para que la demostración funcione. No guardamos tu clave de IA, no
          usamos cookies de seguimiento ni publicidad y borramos lo que subes a las {horas} horas. Aun
          así, no subas datos reales: es un proyecto de concurso.
        </p>
      }
    >
      <Clausula numero={1} titulo="Responsable">
        <p>
          Los datos los trata el equipo que presenta HumanAIz a {concurso}, con fines exclusivamente
          demostrativos. Para contactarnos, <Contacto con="escribe a " />.
        </p>
      </Clausula>

      <Clausula numero={2} titulo="Qué datos tratamos">
        <ul>
          <li>
            <strong>Lo que subes y escribes:</strong> la imagen del certificado (solo la copia
            re-codificada por el servidor, sin metadatos), sede, comentarios y decisiones. Del archivo
            original solo guardamos su huella digital, para detectar duplicados.
          </li>
          <li>
            <strong>Datos de las cuentas:</strong> DNI, nombres y ficha de colaborador. En la
            demostración son ficticios.
          </li>
          <li>
            <strong>Datos técnicos:</strong> dirección IP, fecha y hora, navegador y las acciones que
            realizas (inicio de sesión, subida, lectura con IA, decisión), por seguridad y auditoría.
          </li>
          <li>
            <strong>Resultados de las lecturas con IA:</strong> datos extraídos, comprobaciones,
            proveedor y modelo usados, y consumo.
          </li>
        </ul>
      </Clausula>

      <Clausula numero={3} titulo="Qué no tratamos">
        <ul>
          <li>
            <strong>Tu clave de IA.</strong> Viaja cifrada (HTTPS) solo en la petición de lectura, se
            usa una vez y se descarta. No se guarda en la base de datos, en los registros ni en
            archivos. En tu navegador vive en memoria (o en la pestaña, si eliges recordarla) y se
            borra al cerrar sesión.
          </li>
          <li>No usamos analítica, cookies de terceros, publicidad ni perfiles.</li>
          <li>No vendemos ni cedemos datos.</li>
          <li>
            Pedimos expresamente que no subas datos de salud reales. Si alguien lo hace, ese contenido
            se elimina en cuanto lo detectemos y, en cualquier caso, al vencer el plazo de
            conservación.
          </li>
        </ul>
      </Clausula>

      <Clausula numero={4} titulo="Para qué los usamos">
        <ul>
          <li>Hacer funcionar la demostración: tu sesión y mostrarte lo que subes.</li>
          <li>Separar lo que sube cada navegador en las cuentas de prueba compartidas.</li>
          <li>Seguridad: limitar abusos y registrar accesos.</li>
          <li>Presentar el proyecto en el concurso.</li>
        </ul>
        <p>La base es tu consentimiento, que das al aceptar estos textos al ingresar.</p>
      </Clausula>

      <Clausula numero={5} titulo="Con quién se comparten">
        <ul>
          <li>
            <strong>El proveedor de IA que elijas</strong>, solo si pides una lectura: recibe las
            imágenes del documento y las instrucciones de lectura, a través de tu clave y bajo tus
            condiciones con él. Puede tratar los datos fuera del Perú.
          </li>
          <li>
            <strong>El proveedor de infraestructura</strong> donde se aloja la demostración, como
            encargado del tratamiento.
          </li>
          <li>Nadie más, salvo obligación legal.</li>
        </ul>
      </Clausula>

      <Clausula numero={6} titulo="Cuánto tiempo los conservamos">
        <ul>
          <li>Documentos y descansos subidos en la demostración: {horas} horas.</li>
          <li>Sesiones de las cuentas de prueba: unas horas como máximo.</li>
          <li>
            Registros de seguridad (IP y acciones): {dias} días, salvo que un incidente o el
            requerimiento de una autoridad obligue a conservarlos más tiempo.
          </li>
          <li>Registros técnicos del servidor: rotan y se sobrescriben de forma periódica.</li>
          <li>Cuando la demostración se retire, se eliminará todo.</li>
        </ul>
      </Clausula>

      <Clausula numero={7} titulo="Cookies y almacenamiento en tu navegador">
        <p>Solo usamos dos cookies esenciales, inaccesibles para scripts y sin fines de seguimiento:</p>
        <ul>
          <li>
            <code className="text-xs">__Host-hz_session</code>: mantiene tu sesión iniciada.
          </li>
          <li>
            <code className="text-xs">__Host-hz_visitor</code>: identifica a tu navegador en las
            cuentas de prueba para que solo veas lo que subes tú ({horas} horas).
          </li>
        </ul>
        <p>
          Si marcas «Recordar en esta pestaña» al configurar tu clave de IA, se guarda en el
          almacenamiento de sesión de la pestaña, que el navegador borra al cerrarla.
        </p>
        <p>
          El idioma que eliges se guarda en el almacenamiento local del navegador (localStorage), con
          la clave <code className="text-xs">hz_idioma</code>, para recordarlo en tu próxima visita. No
          es un dato personal ni se usa para seguimiento; puedes borrarlo desde la configuración de tu
          navegador.
        </p>
      </Clausula>

      <Clausula numero={8} titulo="Seguridad">
        <p>
          Usamos conexiones cifradas, contraseñas protegidas con Argon2, imágenes privadas que solo
          se entregan con sesión iniciada y que nadie más ve en las cuentas de prueba, imágenes
          recodificadas sin metadatos (se elimina, por ejemplo, la ubicación de las fotos) y límites
          de uso por persona y para todo el servicio. Ningún sistema es infalible: por eso te pedimos
          usar solo datos ficticios.
        </p>
      </Clausula>

      <Clausula numero={9} titulo="Tus derechos">
        <p>
          Conforme a la Ley N.º 29733, Ley de Protección de Datos Personales, y su reglamento, puedes
          ejercer tus derechos de acceso, rectificación, cancelación y oposición: para ello,{" "}
          <Contacto con="escribe a " />. También puedes acudir a la Autoridad Nacional de Protección
          de Datos Personales.
        </p>
        <p>
          En la demostración, además, puedes eliminar tú mismo un descanso pendiente desde su página
          de detalle.
        </p>
      </Clausula>

      <Clausula numero={10} titulo="Menores de edad">
        <p>
          Si tienes menos de 14 años, necesitas la autorización de tus padres o tutores para usar la
          demostración.
        </p>
      </Clausula>

      <Clausula numero={11} titulo="Cambios">
        <p>
          Podemos actualizar esta política junto con los{" "}
          <Link to="/terminos" className="text-primary underline underline-offset-2">
            términos y condiciones
          </Link>
          . Si cambian, se te pedirá aceptarlos de nuevo al ingresar.
        </p>
      </Clausula>
    </DocumentoLegal>
  );
}

function PrivacidadEn({ concurso, horas, dias }: Datos) {
  const { t } = useI18n();
  return (
    <DocumentoLegal
      titulo={t.legal.privacidad.titulo}
      resumen={
        <p>
          We process the minimum needed for the demo to work. We don't store your AI key, we don't use
          tracking or advertising cookies, and we delete what you upload after {horas} hours. Even so,
          don't upload real data: this is a contest project.
        </p>
      }
    >
      <Clausula numero={1} titulo="Data controller">
        <p>
          The data is processed by the team presenting HumanAIz to {concurso}, for demonstration
          purposes only. To contact us, <Contacto con="write to " />.
        </p>
      </Clausula>

      <Clausula numero={2} titulo="What data we process">
        <ul>
          <li>
            <strong>What you upload and write:</strong> the medical certificate image (only the copy
            re-encoded by the server, without metadata), work location, comments and decisions. From
            the original file we only keep its digital fingerprint, to detect duplicates.
          </li>
          <li>
            <strong>Account data:</strong> ID number (DNI), names and employee record. In the demo they
            are fictitious.
          </li>
          <li>
            <strong>Technical data:</strong> IP address, date and time, browser and the actions you take
            (sign-in, upload, AI reading, decision), for security and auditing.
          </li>
          <li>
            <strong>AI reading results:</strong> extracted data, checks, the provider and model used,
            and usage.
          </li>
        </ul>
      </Clausula>

      <Clausula numero={3} titulo="What we don't process">
        <ul>
          <li>
            <strong>Your AI key.</strong> It travels encrypted (HTTPS) only in the reading request, is
            used once and is then discarded. It is not stored in the database, in logs or in files. In
            your browser it lives in memory (or in the tab, if you choose to remember it) and is
            deleted when you sign out.
          </li>
          <li>We don't use analytics, third-party cookies, advertising or profiling.</li>
          <li>We don't sell or share data.</li>
          <li>
            We expressly ask you not to upload real health data. If someone does, that content is
            deleted as soon as we detect it and, in any case, when the retention period expires.
          </li>
        </ul>
      </Clausula>

      <Clausula numero={4} titulo="What we use it for">
        <ul>
          <li>Running the demo: your session and showing you what you upload.</li>
          <li>Keeping what each browser uploads separate in the shared demo accounts.</li>
          <li>Security: limiting abuse and logging access.</li>
          <li>Presenting the project in the contest.</li>
        </ul>
        <p>The legal basis is your consent, which you give by accepting these texts when signing in.</p>
      </Clausula>

      <Clausula numero={5} titulo="Who we share it with">
        <ul>
          <li>
            <strong>The AI provider you choose</strong>, only if you request a reading: it receives the
            document images and the reading instructions, through your key and under your own terms
            with that provider. It may process the data outside Peru.
          </li>
          <li>
            <strong>The infrastructure provider</strong> that hosts the demo, as data processor.
          </li>
          <li>No one else, unless required by law.</li>
        </ul>
      </Clausula>

      <Clausula numero={6} titulo="How long we keep it">
        <ul>
          <li>Documents and sick leaves uploaded in the demo: {horas} hours.</li>
          <li>Demo account sessions: a few hours at most.</li>
          <li>
            Security logs (IP and actions): {dias} days, unless an incident or a request from an
            authority requires keeping them longer.
          </li>
          <li>Server technical logs: rotated and overwritten periodically.</li>
          <li>When the demo is withdrawn, everything will be deleted.</li>
        </ul>
      </Clausula>

      <Clausula numero={7} titulo="Cookies and storage in your browser">
        <p>We only use two essential cookies, inaccessible to scripts and not used for tracking:</p>
        <ul>
          <li>
            <code className="text-xs">__Host-hz_session</code>: keeps you signed in.
          </li>
          <li>
            <code className="text-xs">__Host-hz_visitor</code>: identifies your browser in the demo
            accounts so that you only see what you upload ({horas} hours).
          </li>
        </ul>
        <p>
          If you tick “Remember in this tab” when setting up your AI key, it is stored in the tab's
          session storage, which the browser clears when you close the tab.
        </p>
        <p>
          The language you choose is stored in your browser's local storage (localStorage), under the{" "}
          <code className="text-xs">hz_idioma</code> key, so it's remembered on your next visit. It is
          not personal data and is not used for tracking; you can delete it from your browser
          settings.
        </p>
      </Clausula>

      <Clausula numero={8} titulo="Security">
        <p>
          We use encrypted connections, passwords protected with Argon2, private images that are only
          delivered to signed-in users and that no one else sees in the demo accounts, re-encoded
          images without metadata (for example, the location of photos is removed) and usage limits
          per person and for the whole service. No system is infallible: that's why we ask you to use
          only fictitious data.
        </p>
      </Clausula>

      <Clausula numero={9} titulo="Your rights">
        <p>
          Under Law No. 29733, Ley de Protección de Datos Personales (Personal Data Protection Law),
          and its regulations, you can exercise your rights of access, rectification, cancellation and
          objection: to do so, <Contacto con="write to " />. You can also contact the Autoridad
          Nacional de Protección de Datos Personales (National Personal Data Protection Authority).
        </p>
        <p>In the demo, you can also delete a pending sick leave yourself from its detail page.</p>
      </Clausula>

      <Clausula numero={10} titulo="Minors">
        <p>
          If you are under 14, you need your parents' or guardians' permission to use the demo.
        </p>
      </Clausula>

      <Clausula numero={11} titulo="Changes">
        <p>
          We may update this policy together with the{" "}
          <Link to="/terminos" className="text-primary underline underline-offset-2">
            terms and conditions
          </Link>
          . If they change, you'll be asked to accept them again when you sign in.
        </p>
      </Clausula>
    </DocumentoLegal>
  );
}
