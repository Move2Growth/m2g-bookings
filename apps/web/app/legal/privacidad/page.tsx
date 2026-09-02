import type { Metadata } from 'next'
import Link from 'next/link'
import { Cabecera } from '@/componentes/cabecera'
import { Pie } from '@/componentes/pie'

export const metadata: Metadata = {
  title: 'Política de privacidad',
  description:
    'Qué datos guarda Bukeo, para qué, cuánto tiempo y cómo ejercer tus derechos según la Ley 81 de 2019 de Panamá.',
}

/**
 * Política de privacidad.
 *
 * No es un trámite: la Ley 81 de 2019 la exige, y Apple no publica una app sin ella ni sin el
 * borrado de cuenta desde dentro. Está escrita para leerse, no para cubrirse: si una clienta no
 * entiende qué guardamos, la política no sirve aunque sea válida.
 *
 * **Este texto necesita revisión legal antes de salir a producción.** Está marcado como
 * pendiente en el tablero: aquí se describe lo que el sistema hace de verdad, que es la parte
 * que sí puede escribir el equipo.
 */
export default function Privacidad() {
  return (
    <>
      <Cabecera />
      <main className="contenedor seccion" style={{ maxWidth: '46rem' }}>
        <h1>Política de privacidad</h1>
        <p className="apagado" style={{ marginTop: 'var(--espacio-3)' }}>
          Última actualización: 1 de septiembre de 2026. Aplica la Ley 81 de 2019 de protección
          de datos personales de la República de Panamá.
        </p>

        <div className="prosa">
          <h2>Qué guardamos y por qué</h2>
          <table className="tabla-plan">
            <tbody>
              <tr>
                <th scope="row">Tu teléfono</th>
                <td>Es tu forma de entrar y lo que el salón necesita para saber que la cita es real.</td>
              </tr>
              <tr>
                <th scope="row">Tu nombre</th>
                <td>Para que el salón sepa a quién saluda. Lo pides tú la primera vez que reservas.</td>
              </tr>
              <tr>
                <th scope="row">Tus citas</th>
                <td>Qué reservaste, cuándo y en qué salón. Es el servicio.</td>
              </tr>
              <tr>
                <th scope="row">Tu ubicación aproximada</th>
                <td>Solo si la das, y solo para ordenar los resultados por cercanía. No se guarda.</td>
              </tr>
            </tbody>
          </table>

          <h2>Quién ve tus datos</h2>
          <p>
            El salón donde reservas ve tu nombre, tu teléfono y tus citas <strong>en ese salón</strong>.
            Ningún salón ve lo que haces en otro: el aislamiento no es una promesa de este texto,
            es una regla de la base de datos.
          </p>
          <p>
            No vendemos tus datos a nadie ni los cedemos con fines publicitarios. Los
            proveedores que usamos para funcionar (mensajería, alojamiento) tratan datos por
            cuenta nuestra y bajo contrato.
          </p>

          <h2>Cuánto tiempo</h2>
          <p>
            Tus citas se conservan mientras tengas cuenta, porque son el historial que el salón
            necesita. Si borras tu cuenta, tus datos personales se eliminan o se anonimizan: la
            cita queda en la contabilidad del salón, pero sin tu nombre ni tu teléfono.
          </p>

          <h2>Tus derechos</h2>
          <p>
            Puedes acceder a tus datos, corregirlos, oponerte a su tratamiento, pedir que se
            porten y <strong>borrar tu cuenta</strong>. El borrado se hace desde la propia
            aplicación, sin escribir a nadie y sin dar explicaciones.
          </p>
          <p>
            Para cualquier cosa relacionada con esto, escríbenos y te contestamos. Si crees que
            no cumplimos, puedes acudir a la Autoridad Nacional de Transparencia y Acceso a la
            Información.
          </p>

          <h2>Qué falta en este texto</h2>
          <p className="apagado">
            Los datos de contacto del responsable, el detalle de los encargados de tratamiento y
            los plazos exactos de conservación se completan antes del lanzamiento, con revisión
            legal. Lo que sí describe esta página con exactitud es lo que el sistema hace hoy.
          </p>
        </div>

        <p style={{ marginTop: 'var(--espacio-6)' }}>
          <Link href="/legal/terminos">Términos de uso</Link>
        </p>
      </main>
      <Pie />
    </>
  )
}
