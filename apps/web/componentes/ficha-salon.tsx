'use client'

import Image from 'next/image'
import Link from 'next/link'
import { useState } from 'react'
import { API, leerSesion } from '@/lib/sesion'

/**
 * Un salón en una lista.
 *
 * La misma pieza en el buscador y en los guardados: si fueran dos, la del buscador acabaría
 * con el precio y la otra no, sin que nadie lo decidiera.
 *
 * Qué lleva y por qué: **foto, nombre, nota, precio desde y próxima hora libre**. Son los
 * cuatro datos con los que se descarta un salón sin abrirlo, y descartar rápido es lo que hace
 * que una lista se recorra entera en vez de abandonarse en el tercero.
 */

export type SalonEnLista = {
  /** El identificador con el que se guarda en favoritos. El slug identifica la página; el id
   *  identifica el negocio, y son cosas distintas: un slug puede cambiar. */
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

export function FichaSalon({
  salon,
  guardado,
  onGuardar,
}: {
  salon: SalonEnLista
  guardado?: boolean
  onGuardar?: (negocioId: string, ahora: boolean) => void
}) {
  return (
    <li className="salon">
      <Link href={`/${salon.slug}`} className="salon__enlace">
        <span className="salon__foto">
          {salon.foto_portada ? (
            <Image
              src={salon.foto_portada}
              alt=""
              width={480}
              height={480}
              sizes="(min-width: 900px) 220px, 40vw"
            />
          ) : (
            /* Sin foto no se pone una imagen de relleno: se pone la inicial del salón sobre
               color plano. Una foto genérica de banco engaña sobre cómo es el sitio. */
            <span className="salon__inicial" aria-hidden="true">
              {salon.nombre.trim().charAt(0)}
            </span>
          )}
        </span>

        <span className="salon__cuerpo">
          {salon.patrocinado && (
            /* Un patrocinado va etiquetado siempre y encima del nombre, donde se lee antes de
               decidir. Es la regla MKT-4 y no admite matices. */
            <span className="etiqueta">Patrocinado</span>
          )}
          <span className="salon__nombre">{salon.nombre}</span>

          <span className="salon__meta">
            {typeof salon.rating === 'number' && (
              <span className="salon__nota cifras">
                <span aria-hidden="true">★</span> {salon.rating.toFixed(1)}
                {salon.numero_reviews ? (
                  <span className="tenue"> ({salon.numero_reviews})</span>
                ) : null}
                <span className="oculto-visualmente">
                  de nota, sobre 5{salon.numero_reviews ? `, con ${salon.numero_reviews} reseñas` : ''}
                </span>
              </span>
            )}
            {salon.zona && <span className="tenue">{salon.zona}</span>}
            {typeof salon.distancia_metros === 'number' && (
              <span className="tenue cifras">a {(salon.distancia_metros / 1000).toFixed(1)} km</span>
            )}
          </span>

          {salon.categorias && salon.categorias.length > 0 && (
            <span className="salon__categorias">{salon.categorias.slice(0, 3).join(' · ')}</span>
          )}

          <span className="salon__pie">
            {typeof salon.servicios_desde_centavos === 'number' && (
              <span className="salon__precio cifras">
                Desde ${(salon.servicios_desde_centavos / 100).toFixed(2)}
              </span>
            )}
            {salon.proxima_hora ? (
              <span className="salon__hora cifras">
                Libre hoy a las{' '}
                {new Intl.DateTimeFormat('es-PA', {
                  hour: '2-digit',
                  minute: '2-digit',
                  hour12: false,
                  timeZone: 'America/Panama',
                }).format(new Date(salon.proxima_hora))}
              </span>
            ) : salon.abierto_ahora === false ? (
              <span className="tenue">Cerrado ahora</span>
            ) : null}
          </span>
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
      className="salon__guardar"
      onClick={alternar}
      disabled={ocupado}
      aria-pressed={activo}
      aria-label={activo ? 'Quitar de guardados' : 'Guardar este salón'}
    >
      <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
        <path
          d="M12 20s-7.5-4.6-7.5-9.6A4.4 4.4 0 0 1 12 7.6a4.4 4.4 0 0 1 7.5 2.8C19.5 15.4 12 20 12 20Z"
          fill={activo ? 'currentColor' : 'none'}
          stroke="currentColor"
          strokeWidth={1.75}
          strokeLinejoin="round"
        />
      </svg>
    </button>
  )
}
