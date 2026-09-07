'use client'

import 'leaflet/dist/leaflet.css'
import Link from 'next/link'
import { useCallback, useEffect, useRef, useState } from 'react'
import { API } from '@/lib/sesion'

/**
 * El mapa de salones.
 *
 * Pide **lo que se ve**, no todo: el servidor recibe el rectángulo de la pantalla y devuelve los
 * salones de dentro con su nota y su número de reseñas. Un mapa alejado que devolviera el país
 * entero son varios megabytes en datos móviles, que es exactamente donde vive esto.
 *
 * **Las baldosas son de OpenStreetMap y no piden clave.** Eso no es la decisión definitiva: es lo
 * que permite construir la pantalla hoy en vez de esperar a que se elija proveedor. Su política de
 * uso pide no cargarles tráfico serio, así que para publicar hay que pasar a un proveedor de pago
 * o a baldosas propias — y ese cambio es **una URL**, no otra pantalla.
 *
 * Leaflet se carga a mano dentro de un efecto y no con un `import` de arriba, porque toca `window`
 * al evaluarse: importado normalmente, el renderizado en servidor de Next revienta antes de pintar.
 */

type SalonDelMapa = {
  negocio_id: string
  slug: string
  nombre: string
  longitud: number
  latitud: number
  rating: number | null
  numero_reviews: number
}

/** Ciudad de Panamá. Es donde está el producto; no hay geolocalización de por medio para arrancar. */
const CENTRO: [number, number] = [8.9824, -79.5199]
const ZOOM = 14

export default function Mapa() {
  const contenedor = useRef<HTMLDivElement>(null)
  const mapa = useRef<any>(null)
  const capa = useRef<any>(null)
  const [salones, setSalones] = useState<SalonDelMapa[]>([])
  const [elegido, setElegido] = useState<SalonDelMapa | null>(null)
  const [truncado, setTruncado] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /** Pide los salones del rectángulo visible. Se llama al arrancar y cada vez que se mueve. */
  const cargar = useCallback(async (L: any) => {
    if (!mapa.current) return
    const b = mapa.current.getBounds()
    const parametros = new URLSearchParams({
      oeste: String(b.getWest()),
      sur: String(b.getSouth()),
      este: String(b.getEast()),
      norte: String(b.getNorth()),
    })
    try {
      const respuesta = await fetch(`${API}/api/v1/publico/mapa?${parametros}`)
      if (!respuesta.ok) throw new Error('No se pudieron cargar los salones de esta zona.')
      const datos = await respuesta.json()
      setError(null)
      setSalones(datos.salones)
      setTruncado(Boolean(datos.truncado))

      capa.current?.clearLayers()
      // **El nombre solo cuando cabe.** En Obarrio hay seis salones en tres manzanas: a poco zoom
      // sus nombres se pisan unos a otros y no se lee ninguno, que es peor que no ponerlos. Por
      // debajo de la distancia de barrio la chincheta se queda con la nota, que es lo que de
      // verdad se compara de un vistazo, y el nombre vuelve al acercarse.
      const conNombre = mapa.current.getZoom() >= 15

      for (const salon of datos.salones as SalonDelMapa[]) {
        const nota = typeof salon.rating === 'number' ? salon.rating.toFixed(1) : '·'
        const marca = L.marker([salon.latitud, salon.longitud], {
          icon: L.divIcon({
            className: '',
            html: conNombre
              ? `<span class="mapa__chincheta">${salon.nombre} · ${nota}</span>`
              : `<span class="mapa__chincheta mapa__chincheta--corta">${nota}</span>`,
            iconSize: undefined,
            iconAnchor: [0, 0],
          }),
        })
        marca.on('click', () => setElegido(salon))
        marca.addTo(capa.current)
      }
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron cargar los salones.')
    }
  }, [])

  useEffect(() => {
    let vivo = true
    void (async () => {
      const L = (await import('leaflet')).default
      if (!vivo || !contenedor.current || mapa.current) return

      // El zoom a la derecha: a la izquierda se montaba encima de la barra de «ver en lista».
      mapa.current = L.map(contenedor.current, { zoomControl: false }).setView(CENTRO, ZOOM)
      L.control.zoom({ position: 'topright' }).addTo(mapa.current)
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        // La atribución no es cortesía: es la condición de uso de OpenStreetMap.
        attribution: '&copy; colaboradores de OpenStreetMap',
      }).addTo(mapa.current)
      capa.current = L.layerGroup().addTo(mapa.current)

      // Se pide al soltar, no mientras se arrastra: una petición por fotograma no la aguanta ni
      // el servidor ni una conexión de datos.
      mapa.current.on('moveend', () => void cargar(L))
      await cargar(L)
    })()
    return () => {
      vivo = false
      mapa.current?.remove()
      mapa.current = null
    }
  }, [cargar])

  return (
    <main className="mapa">
      <div className="mapa__lienzo" ref={contenedor} aria-label="Mapa de salones" role="application" />

      <div className="mapa__encima">
        <div className="mapa__barra">
          <Link href="/buscar" className="boton boton--secundario">
            Ver en lista
          </Link>
          <span className="tenue">
            {salones.length} {salones.length === 1 ? 'salón' : 'salones'} a la vista
          </span>
        </div>

        {error && (
          <p role="alert" className="aviso aviso--error">
            {error}
          </p>
        )}

        {truncado && (
          /* El servidor recorta cuando el rectángulo es enorme. Decirlo evita que alguien
             concluya que en media ciudad no hay salones. */
          <p className="aviso">Hay más salones de los que caben. Acerca el mapa para verlos todos.</p>
        )}

        {elegido && (
          <article className="mapa__ficha">
            <button
              type="button"
              className="boton boton--llano mapa__cerrar"
              onClick={() => setElegido(null)}
              aria-label="Cerrar"
            >
              ✕
            </button>
            <h2>{elegido.nombre}</h2>
            <p className="tenue">
              {typeof elegido.rating === 'number' ? (
                <>
                  {elegido.rating.toFixed(1)} de nota
                  {elegido.numero_reviews > 0
                    ? ` · ${elegido.numero_reviews} ${
                        elegido.numero_reviews === 1 ? 'reseña' : 'reseñas'
                      }`
                    : ''}
                </>
              ) : (
                'Todavía sin reseñas'
              )}
            </p>
            <Link href={`/${elegido.slug}`} className="boton boton--cierra boton--ancho">
              Ver horas libres
            </Link>
          </article>
        )}
      </div>
    </main>
  )
}
