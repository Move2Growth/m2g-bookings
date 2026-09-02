import type { Metadata } from 'next'
import Link from 'next/link'
import { Cabecera } from '@/componentes/cabecera'
import { Pie } from '@/componentes/pie'

export const metadata: Metadata = {
  title: 'Términos de uso',
  description: 'Las reglas de Bukeo para quien reserva y para el salón que publica su agenda.',
}

/**
 * Términos de uso, en dos mitades porque hay dos partes con obligaciones distintas.
 *
 * **Necesita revisión legal antes de producción**, y está anotado en el tablero. Lo que sí es
 * exacto es la descripción del funcionamiento, que es lo que el equipo puede afirmar.
 */
export default function Terminos() {
  return (
    <>
      <Cabecera />
      <main className="contenedor seccion" style={{ maxWidth: '46rem' }}>
        <h1>Términos de uso</h1>
        <p className="apagado" style={{ marginTop: 'var(--espacio-3)' }}>
          Última actualización: 1 de septiembre de 2026.
        </p>

        <div className="prosa">
          <h2>Qué es Bukeo</h2>
          <p>
            Bukeo conecta a quien busca un servicio de belleza o bienestar con el salón que lo
            presta, y le da al salón una agenda para gestionarlo. <strong>El servicio lo presta
            el salón, no Bukeo.</strong> El precio, la calidad y el cumplimiento de la cita son
            responsabilidad suya.
          </p>

          <h2>Si reservas</h2>
          <ul className="lista-puntos">
            <li>Reservar es gratis. Pagas tu servicio en el salón.</li>
            <li>
              Necesitas un teléfono verificado. No hay reservas anónimas: es lo que sostiene que
              las citas sean reales.
            </li>
            <li>
              Puedes cancelar desde la aplicación hasta el plazo que fije cada salón, que ves
              antes de reservar. Pasado ese plazo, hablas con el salón.
            </li>
            <li>
              Faltar sin avisar cuenta. Un salón puede dejar de aceptar reservas de quien falla
              de forma repetida.
            </li>
          </ul>

          <h2>Si tienes un salón</h2>
          <ul className="lista-puntos">
            <li>
              La agenda es gratuita: sin tarjeta, sin mensualidad y sin comisión por reserva.
            </li>
            <li>
              Respondes de la información que publicas: servicios, precios, duraciones y horario.
              Si tu ficha dice una cosa y en el local pasa otra, el problema es tuyo.
            </li>
            <li>
              Puedes comprar visibilidad. Va siempre etiquetada como patrocinada, nunca esconde
              a los salones que no pagan y no altera ninguna valoración.
            </li>
            <li>
              Los datos de tus clientas son tuyos y de ellas. No los usamos para venderte nada ni
              se los pasamos a otro salón.
            </li>
          </ul>

          <h2>Qué no se permite</h2>
          <p>
            Publicar servicios que no prestas, suplantar a otro negocio, raspar el sitio para
            copiar la base de salones, o usar Bukeo para cualquier cosa que sea ilegal en Panamá.
          </p>

          <h2>Qué falta en este texto</h2>
          <p className="apagado">
            La identificación de la sociedad, la ley aplicable, la resolución de conflictos y el
            régimen de responsabilidad se completan antes del lanzamiento, con revisión legal.
          </p>
        </div>

        <p style={{ marginTop: 'var(--espacio-6)' }}>
          <Link href="/legal/privacidad">Política de privacidad</Link>
        </p>
      </main>
      <Pie />
    </>
  )
}
