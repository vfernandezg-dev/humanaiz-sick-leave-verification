import { Link } from "react-router-dom";
import { useConcurso, useConfig } from "@/hooks/queries";
import { Clausula, Contacto, DocumentoLegal } from "./DocumentoLegal";

// Si cambias este texto de forma sustancial, sube TERMINOS_VERSION en
// backend/src/humanaiz/legal.py: se pedirá aceptarlo de nuevo al ingresar.
export default function Privacidad() {
  const { data } = useConfig();
  const concurso = useConcurso();
  const horas = data?.demo.retencion_horas ?? 24;
  const dias = data?.proyecto.retencion_registros_dias ?? 30;

  return (
    <DocumentoLegal
      titulo="Política de privacidad"
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
            <strong>Lo que subes y escribes:</strong> documentos, sede, comentarios y decisiones.
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
          <li>Registros de seguridad (IP y acciones): {dias} días.</li>
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
      </Clausula>

      <Clausula numero={8} titulo="Seguridad">
        <p>
          Usamos conexiones cifradas, contraseñas protegidas con Argon2, documentos privados que solo
          se entregan con sesión iniciada, imágenes recodificadas sin metadatos (se elimina, por
          ejemplo, la ubicación de las fotos) y límites de uso. Ningún sistema es infalible: por eso
          te pedimos usar solo datos ficticios.
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
