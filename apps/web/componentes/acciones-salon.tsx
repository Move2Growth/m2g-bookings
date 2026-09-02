'use client'

import { useEffect, useState } from 'react'
import { API, leerSesion } from '@/lib/sesion'

/**
 * Guardar y compartir, en la ficha del salón.
 *
 * Compartir usa el menú del sistema cuando existe —que en un teléfono es WhatsApp, que es por
 * donde se comparte todo aquí— y cae a copiar el enlace cuando no. Nunca abre una ventana de
 * red social: eso obliga a elegir dónde compartir antes de saber si se quiere.
 *
 * Guardar sin sesión no da un error: lleva a entrar y vuelve a esta misma ficha.
 */
export function AccionesDeSalon({
  negocioId,
  slug,
  nombre,
  tieneWhatsapp,
}: {
  negocioId: string
  slug: string
  nombre: string
  tieneWhatsapp?: boolean
}) {
  const [guardado, setGuardado] = useState(false)
  const [ocupado, setOcupado] = useState(false)
  const [copiado, setCopiado] = useState(false)

  useEffect(() => {
    const sesion = leerSesion()
    if (!sesion) return
    fetch(`${API}/api/v1/mi/favoritos`, { headers: { Authorization: `Bearer ${sesion.acceso}` } })
      .then((r) => (r.ok ? r.json() : []))
      .then((lista: { negocio_id: string }[]) =>
        setGuardado(lista.some((f) => f.negocio_id === negocioId)),
      )
      .catch(() => {})
  }, [negocioId])

  async function alternarGuardado() {
    const sesion = leerSesion()
    if (!sesion) {
      window.location.href = `/entrar?volver=${encodeURIComponent(`/${slug}`)}`
      return
    }
    const siguiente = !guardado
    setGuardado(siguiente)
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
    } catch {
      setGuardado(!siguiente)
    } finally {
      setOcupado(false)
    }
  }

  async function compartir() {
    const url = window.location.origin + `/${slug}`
    const datos = { title: nombre, text: `Mira las horas libres de ${nombre}`, url }
    if (navigator.share) {
      try {
        await navigator.share(datos)
        return
      } catch {
        // Cancelar el menú del sistema no es un fallo: no se hace nada más.
        return
      }
    }
    try {
      await navigator.clipboard.writeText(url)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 2400)
    } catch {
      /* Sin portapapeles no hay nada que hacer: el enlace está en la barra del navegador. */
    }
  }

  return (
    <div className="acciones-salon">
      <button
        type="button"
        className="boton boton--secundario"
        onClick={alternarGuardado}
        disabled={ocupado}
        aria-pressed={guardado}
      >
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <path
            d="M12 20 4 12.4A4.6 4.6 0 0 1 12 7.4a4.6 4.6 0 0 1 8 5z"
            fill={guardado ? 'currentColor' : 'none'}
            stroke="currentColor"
            strokeWidth={2}
            strokeLinejoin="miter"
          />
        </svg>
        {guardado ? 'Guardado' : 'Guardar'}
      </button>

      <button type="button" className="boton boton--secundario" onClick={compartir}>
        {copiado ? 'Enlace copiado' : 'Compartir'}
      </button>

      {tieneWhatsapp && (
        /* El enlace apunta a **nuestro** dominio y el servidor redirige. El número del salón
           nunca llega al navegador: si viajara en la ficha, un script se lleva la base entera
           de negocios de Panamá en una tarde. */
        <a
          className="boton boton--secundario"
          href={`${API}/api/v1/publico/negocios/${slug}/chat`}
          rel="nofollow noreferrer"
          target="_blank"
        >
          Escribir por WhatsApp
        </a>
      )}
    </div>
  )
}
