'use client'

import Link from 'next/link'
import { useState } from 'react'
import { FotoDeSalon } from '@/componentes/foto'
import { Rotulo } from '@/componentes/rotulo'
import { API, leerSesion } from '@/lib/sesion'

/**
 * Un salón en una lista.
 *
 * **Es una fila, no una tarjeta.** En un lenguaje de bloques de color, una caja con filete de
 * 1 px es lo contrario de lo que dice el brandbook, y el filete que se usaba se quedaba en
 * 1,44:1 sobre lienzo: exactamente el defecto por el que se descartó la dirección A.
 *
 * La fila entera es el objetivo táctil, y al tocarla aparece un filo de 6 px que empuja el
 * contenido. Cero relleno de color al pasar por encima.
 *
 * Termina en lo único que de verdad decide: **la próxima hora libre**. Es el dato que convierte
 * una lista en algo que se puede tocar, y por eso ocupa una chapa con su canto y no una línea
 * de texto más.
 */

export type SalonEnLista = {
  negocio_id?: string
  slug: string
  nombre: string
  direccion: string | null
  zona: string | null
  distancia_metros: number | null
  rating: number | null
  numero_reviews?: number
  servicios_desde_centavos: number | null
  foto_portada?: string | null
  categorias?: string[]
  abierto_ahora?: boolean | null
  proxima_hora?: string | null
  patrocinado: boolean
}

const HORA = new Intl.DateTimeFormat('es-PA', {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  timeZone: 'America/Panama',
})

export function FichaSalon({
  salon,
  indice = 0,
  guardado,
  onGuardar,
}: {
  salon: SalonEnLista
  indice?: number
  guardado?: boolean
  onGuardar?: (negocioId: string, ahora: boolean) => void
}) {
  const cerrado = salon.abierto_ahora === false && !salon.proxima_hora
  const clases = [
    'resultado',
    salon.patrocinado ? 'resultado--destacado' : '',
    cerrado ? 'resultado--cerrado' : '',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <li className="resultado-fila">
      <Link href={`/${salon.slug}`} className={clases}>
        <span className="resultado__sello">
          {salon.foto_portada ? (
            <FotoDeSalon src={salon.foto_portada} ancho={128} alto={128} sizes="64px" />
          ) : (
            <Rotulo
              nombre={salon.nombre}
              categoria={salon.categorias?.[0]}
              indice={indice}
              talla="sello"
            />
          )}
        </span>

        <span className="resultado__cuerpo">
        <span className="resultado__nombre">
          {salon.patrocinado && (
            /* Un patrocinado va etiquetado siempre y encima del nombre, donde se lee antes de
               decidir. Es la regla MKT-4 y no admite matices. */
            <span className="etiqueta">Patrocinado</span>
          )}
          {salon.nombre}
        </span>

        <span className="resultado__meta">
          {typeof salon.rating === 'number' && (
            <>
              <span aria-hidden="true">★</span> {salon.rating.toFixed(1)}
              {salon.numero_reviews ? ` (${salon.numero_reviews})` : ''}
              <span className="oculto-visualmente">
                de nota sobre 5{salon.numero_reviews ? `, con ${salon.numero_reviews} reseñas` : ''}
              </span>
              {' · '}
            </>
          )}
          {[salon.zona, salon.categorias?.[0]].filter(Boolean).join(' · ')}
          {typeof salon.servicios_desde_centavos === 'number' && (
            <> {' · '}desde ${(salon.servicios_desde_centavos / 100).toFixed(2)}</>
          )}
        </span>

        {salon.proxima_hora ? (
          <span className="resultado__hora">
            <b>{HORA.format(new Date(salon.proxima_hora))}</b>
            <small>libre hoy</small>
          </span>
        ) : (
          <span className="resultado__hora resultado__hora--sin">
            <small>{cerrado ? 'cerrado' : 'ver horas'}</small>
          </span>
        )}
        </span>
      </Link>

      {onGuardar && salon.negocio_id && (
        <BotonGuardar
          negocioId={salon.negocio_id}
          guardado={Boolean(guardado)}
          onGuardar={onGuardar}
        />
      )}
    </li>
  )
}

/**
 * El corazón de guardar.
 *
 * Pinta el cambio antes de que responda el servidor y lo deshace si falla. En 3G, esperar
 * 800 ms a que un corazón se llene se siente como que el botón no funciona, y la gente lo pulsa
 * otra vez, que es justo lo que hay que evitar.
 */
function BotonGuardar({
  negocioId,
  guardado,
  onGuardar,
}: {
  negocioId: string
  guardado: boolean
  onGuardar: (negocioId: string, ahora: boolean) => void
}) {
  const [activo, setActivo] = useState(guardado)
  const [ocupado, setOcupado] = useState(false)

  async function alternar() {
    const sesion = leerSesion()
    if (!sesion) {
      window.location.href = `/entrar?volver=${encodeURIComponent(window.location.pathname + window.location.search)}`
      return
    }
    const siguiente = !activo
    setActivo(siguiente)
    setOcupado(true)
    try {
      const respuesta = await fetch(
        `${API}/api/v1/mi/favoritos${siguiente ? '' : `/${negocioId}`}`,
        {
          method: siguiente ? 'POST' : 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${sesion.acceso}`,
          },
          body: siguiente ? JSON.stringify({ negocio_id: negocioId }) : undefined,
        },
      )
      if (!respuesta.ok) throw new Error('no')
      onGuardar(negocioId, siguiente)
    } catch {
      setActivo(!siguiente)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <button
      type="button"
      className="resultado__guardar"
      onClick={alternar}
      disabled={ocupado}
      aria-pressed={activo}
      aria-label={activo ? 'Quitar de guardados' : 'Guardar este salón'}
    >
      <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
        <path
          d="M12 20 4 12.4A4.6 4.6 0 0 1 12 7.4a4.6 4.6 0 0 1 8 5z"
          fill={activo ? 'currentColor' : 'none'}
          stroke="currentColor"
          strokeWidth={2}
          strokeLinejoin="miter"
        />
      </svg>
    </button>
  )
}
