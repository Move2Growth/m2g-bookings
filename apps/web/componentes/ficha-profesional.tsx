import Link from 'next/link'
import { FotoDeSalon } from '@/componentes/foto'
import { Rotulo } from '@/componentes/rotulo'
import type { ProfesionalEnLista } from '@/lib/api'

/**
 * Una persona en una lista de resultados.
 *
 * Misma pieza que la fila de salón —`.resultado`, fila y no tarjeta— pero con lo que decide
 * cuando eliges persona y no local: **su oficio, su nota, en qué salón está y su próxima hora
 * libre**. La dirección del local no cabe aquí; el nombre del local sí, porque es a donde hay
 * que ir.
 *
 * Se renderiza en el servidor entera, sin nada de cliente: es lo que ve el rastreador y lo que
 * se pinta primero en 3G. El corazón de guardar no está a propósito: hoy solo se guardan
 * salones, y un corazón que no guarda nada es peor que ninguno.
 */

const HORA = new Intl.DateTimeFormat('es-PA', {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  timeZone: 'America/Panama',
})

const DIA = new Intl.DateTimeFormat('es-PA', {
  weekday: 'short',
  timeZone: 'America/Panama',
})

/** «17:15 libre hoy» o «17:15 el mié»: sin el día, una hora de pasado mañana engaña. */
function cuando(instante: string): { hora: string; cuando: string } {
  const fecha = new Date(instante)
  const hoy = new Date()
  const mismoDia =
    fecha.toLocaleDateString('es-PA', { timeZone: 'America/Panama' }) ===
    hoy.toLocaleDateString('es-PA', { timeZone: 'America/Panama' })
  return { hora: HORA.format(fecha), cuando: mismoDia ? 'libre hoy' : `el ${DIA.format(fecha)}` }
}

export function FichaProfesional({
  persona,
  indice = 0,
}: {
  persona: ProfesionalEnLista
  indice?: number
}) {
  // Sin salón publicado no hay a dónde enlazar. No debería pasar —la API solo devuelve fichas
  // visibles— pero un `undefined` en una URL manda a la gente a una página que no existe.
  if (!persona.negocio_slug) return null

  const destino = `/${persona.negocio_slug}/${persona.slug ?? persona.id}`
  const libre = persona.proxima_hora ? cuando(persona.proxima_hora) : null

  return (
    <li className="resultado-fila">
      <Link href={destino} className="resultado">
        <span className="resultado__sello">
          {persona.foto ? (
            <FotoDeSalon src={persona.foto} ancho={128} alto={128} sizes="64px" />
          ) : (
            <Rotulo nombre={persona.nombre} indice={indice} talla="sello" />
          )}
        </span>

        <span className="resultado__cuerpo">
          <span className="resultado__nombre">{persona.nombre}</span>

          <span className="resultado__meta">
            {typeof persona.nota === 'number' && (
              <>
                <span aria-hidden="true">★</span> {persona.nota.toFixed(1)}
                {persona.numero_resenas ? ` (${persona.numero_resenas})` : ''}
                <span className="oculto-visualmente">
                  de nota sobre 5
                  {persona.numero_resenas ? `, con ${persona.numero_resenas} reseñas` : ''}
                </span>
                {' · '}
              </>
            )}
            {persona.negocio}
            {persona.anos_de_experiencia ? ` · ${persona.anos_de_experiencia} años` : ''}
          </span>

          {persona.titular && <span className="resultado__meta tenue">{persona.titular}</span>}

          {libre ? (
            <span className="resultado__hora">
              <b className="cifras">{libre.hora}</b>
              <small>{libre.cuando}</small>
            </span>
          ) : (
            <span className="resultado__hora resultado__hora--sin">
              <small>{persona.servicios.length === 0 ? 'sin servicios' : 'ver horas'}</small>
            </span>
          )}
        </span>
      </Link>
    </li>
  )
}
