import Link from 'next/link';

import { NOMBRE_COMERCIAL } from '@/lib/marca';

export const metadata = {
  title: 'Privacidad',
  description: `Qué datos guarda ${NOMBRE_COMERCIAL}, para qué, cuánto tiempo y cómo ejercer tus derechos según la Ley 81 de 2019 de Panamá.`,
};

/**
 * La política de privacidad.
 *
 * Existe porque **la Ley 81 de 2019 la exige** y porque aquí se piden teléfono y nombre para
 * reservar. Es un borrador honesto: dice lo que el sistema hace hoy de verdad, no lo que sería
 * cómodo decir. Lo que todavía no está decidido —cuánto se guarda la auditoría, qué pasa con una
 * opinión cuando su autor borra la cuenta— **se dice que no está decidido** en vez de inventarse
 * un plazo. Antes de que haya datos reales de personas, esto lo revisa un abogado.
 */
export default function Privacidad() {
  return (
    <div className="contenido" data-superficie="calle">
      <article className="seccion pila aparece">
        <span className="etiqueta">Legal</span>
        <h1 className="rotulo rotulo--grande">Qué hacemos con tus datos</h1>

        <p className="parrafo">
          Para reservar hace falta saber quién eres y cómo avisarte. No pedimos más que eso, y lo
          que pedimos se usa para lo que dice esta página y para nada más.
        </p>

        <h2 className="rotulo rotulo--medio">Qué guardamos</h2>
        <ul className="lista-marcada parrafo">
          <li>Tu nombre y tu teléfono, para que el salón sepa a quién espera y pueda avisarte.</li>
          <li>Tu correo, si entras con correo y contraseña.</li>
          <li>Tus citas: dónde, cuándo, con quién y qué servicio.</li>
          <li>Lo que escribes en una reseña, con tu nombre abreviado —«Yaritza B.»— y nunca completo.</li>
        </ul>

        <h2 className="rotulo rotulo--medio">Qué no hacemos</h2>
        <p className="parrafo">
          <strong>Tu teléfono no sale nunca en la parte pública.</strong> Lo ve el salón donde has
          reservado y la persona que te va a atender, porque pueden necesitarlo si algo cambia.
          Tampoco pedimos datos de tarjeta: aquí no se paga la cita, se paga en el salón.
        </p>

        <h2 className="rotulo rotulo--medio">Con quién se comparte</h2>
        <p className="parrafo">
          Con el salón que reservas, y con nadie más. Ni se vende ni se cede a terceros para
          publicidad. Los avisos de tus citas los manda un proveedor de mensajería por nuestra
          cuenta y solo llevan lo justo para el aviso.
        </p>

        <h2 className="rotulo rotulo--medio">Cuánto tiempo</h2>
        <p className="parrafo">
          Tus citas se conservan mientras tengas cuenta, porque son tu historial y el del salón.{' '}
          <strong>Dos plazos siguen sin decidirse</strong> y no vamos a inventarlos aquí: cuánto se
          guarda el registro interno de auditoría y qué pasa con el texto de una opinión cuando su
          autor borra la cuenta. Hasta que se decidan, la opinión se conserva con el autor
          anonimizado.
        </p>

        <h2 className="rotulo rotulo--medio">Tus derechos</h2>
        <p className="parrafo">
          La Ley 81 de 2019 te da derecho a saber qué tenemos tuyo, a corregirlo, a que lo
          borremos y a llevártelo. Se piden escribiendo, y se contestan.
        </p>

        <p className="menor tenue">
          Este texto es un borrador de producto y no ha pasado por un abogado. Antes de que haya
          datos reales de personas, lo revisa uno.
        </p>

        <p className="parrafo">
          <Link href="/legal/terminos">Los términos de uso</Link> ·{' '}
          <Link href="/">Volver a la portada</Link>
        </p>
      </article>
    </div>
  );
}
