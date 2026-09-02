'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import { CATEGORIAS, ZONAS } from '@/lib/taxonomia'

/**
 * La barra del marketplace: campo de búsqueda, pestañas de modo y filtros.
 *
 * Todo lo que se toca aquí **acaba en la URL**. Así una búsqueda se comparte por WhatsApp, se
 * guarda en marcadores, sobrevive al botón de atrás y la puede seguir un rastreador. Un
 * buscador cuyo estado vive en memoria es un buscador del que no se puede enlazar nada, y de
 * Google llega media clientela.
 */


/** Los cinco modos de mirar la misma lista. Cada uno es una combinación de orden y filtro. */
const MODOS: { clave: string; texto: string; parametros: Record<string, string | null> }[] = [
  { clave: 'todos', texto: 'Todos', parametros: { orden: null, disponibilidad: null, abierto_ahora: null } },
  { clave: 'hoy', texto: 'Libres hoy', parametros: { orden: null, disponibilidad: 'hoy', abierto_ahora: null } },
  { clave: 'ahora', texto: 'Abiertos ahora', parametros: { orden: null, disponibilidad: null, abierto_ahora: 'true' } },
  { clave: 'nota', texto: 'Mejor valorados', parametros: { orden: 'rating', disponibilidad: null, abierto_ahora: null } },
  { clave: 'precio', texto: 'Más baratos', parametros: { orden: 'precio', disponibilidad: null, abierto_ahora: null } },
  { clave: 'nuevos', texto: 'Nuevos', parametros: { orden: 'nuevos', disponibilidad: null, abierto_ahora: null } },
]

function modoActivo(p: URLSearchParams) {
  if (p.get('abierto_ahora') === 'true') return 'ahora'
  if (p.get('disponibilidad') === 'hoy') return 'hoy'
  const orden = p.get('orden')
  if (orden === 'rating') return 'nota'
  if (orden === 'precio') return 'precio'
  if (orden === 'nuevos') return 'nuevos'
  return 'todos'
}

export function Buscador() {
  const router = useRouter()
  const parametros = useSearchParams()
  const [texto, setTexto] = useState(parametros.get('texto') ?? '')
  const [abiertoFiltros, setAbiertoFiltros] = useState(false)

  // Si se llega por un enlace con otra búsqueda, el campo tiene que decir lo mismo que la URL.
  useEffect(() => setTexto(parametros.get('texto') ?? ''), [parametros])

  function irCon(cambios: Record<string, string | null>) {
    const p = new URLSearchParams(parametros.toString())
    for (const [clave, valor] of Object.entries(cambios)) {
      if (valor === null || valor === '') p.delete(clave)
      else p.set(clave, valor)
    }
    const cadena = p.toString()
    router.push(cadena ? `/buscar?${cadena}` : '/buscar')
  }

  const modo = modoActivo(parametros)
  const cuantosFiltros = ['zona', 'categoria', 'precio_max', 'rating_min'].filter((c) =>
    parametros.get(c),
  ).length

  return (
    <div className="buscador">
      <form
        className="buscador__fila"
        onSubmit={(e) => {
          e.preventDefault()
          irCon({ texto: texto.trim() || null })
        }}
      >
        <label htmlFor="q" className="oculto-visualmente">
          Qué buscas
        </label>
        <input
          id="q"
          name="texto"
          type="search"
          className="entrada"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Corte, balayage, uñas…"
        />
        <button type="submit" className="boton boton--primario">
          Buscar
        </button>
      </form>

      <div className="buscador__modos">
        <div className="tira" role="tablist" aria-label="Cómo ordenar los salones">
          {MODOS.map((m) => (
            <button
              key={m.clave}
              type="button"
              role="tab"
              aria-selected={modo === m.clave}
              className="ficha ficha--modo"
              onClick={() => irCon(m.parametros)}
            >
              {m.texto}
            </button>
          ))}
        </div>

        <button
          type="button"
          className="boton boton--secundario buscador__filtros"
          onClick={() => setAbiertoFiltros(true)}
          aria-haspopup="dialog"
        >
          Filtros
          {cuantosFiltros > 0 && <span className="buscador__cuenta">{cuantosFiltros}</span>}
        </button>
      </div>

      {abiertoFiltros && (
        <HojaDeFiltros
          parametros={parametros}
          onCerrar={() => setAbiertoFiltros(false)}
          onAplicar={(cambios) => {
            setAbiertoFiltros(false)
            irCon(cambios)
          }}
        />
      )}
    </div>
  )
}

/**
 * Los filtros, en una hoja que sube desde abajo.
 *
 * En hoja y no en una página aparte porque **filtrar es un ajuste, no un viaje**: al cerrarla
 * se vuelve exactamente a la misma lista, con el mismo desplazamiento.
 *
 * Los cambios no se aplican al tocarlos: se aplican al pulsar «Ver resultados». Aplicar en cada
 * toque significa cuatro recargas de lista en 3G para poner un filtro.
 */
function HojaDeFiltros({
  parametros,
  onCerrar,
  onAplicar,
}: {
  parametros: URLSearchParams
  onCerrar: () => void
  onAplicar: (cambios: Record<string, string | null>) => void
}) {
  const [zona, setZona] = useState(parametros.get('zona') ?? '')
  const [categoria, setCategoria] = useState(parametros.get('categoria') ?? '')
  const [precioMax, setPrecioMax] = useState(parametros.get('precio_max') ?? '')
  const [ratingMin, setRatingMin] = useState(parametros.get('rating_min') ?? '')

  // Escape cierra. Es lo que hace todo el mundo con el teclado antes de buscar el botón.
  useEffect(() => {
    const alPulsar = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCerrar()
    }
    document.addEventListener('keydown', alPulsar)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', alPulsar)
      document.body.style.overflow = ''
    }
  }, [onCerrar])

  return (
    <>
      <div className="hoja-fondo" onClick={onCerrar} aria-hidden="true" />
      <div className="hoja" role="dialog" aria-modal="true" aria-label="Filtros">
        <div className="hoja__cabeza">
          <h2 style={{ fontSize: 'var(--tipografia-tamano-titulo-4)' }}>Filtros</h2>
          <button type="button" className="boton boton--llano" onClick={onCerrar}>
            Cerrar
          </button>
        </div>

        <fieldset className="grupo">
          <legend className="campo-etiqueta">Zona</legend>
          <div className="tira tira--envuelve">
            {ZONAS.map(([nombre, slug]) => (
              <button
                key={slug}
                type="button"
                className="ficha"
                aria-pressed={zona === slug}
                onClick={() => setZona(zona === slug ? '' : slug)}
              >
                {nombre}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className="grupo">
          <legend className="campo-etiqueta">Servicio</legend>
          <div className="tira tira--envuelve">
            {CATEGORIAS.map(([nombre, slug]) => (
              <button
                key={slug}
                type="button"
                className="ficha"
                aria-pressed={categoria === slug}
                onClick={() => setCategoria(categoria === slug ? '' : slug)}
              >
                {nombre}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className="grupo">
          <legend className="campo-etiqueta">Precio máximo</legend>
          <div className="tira tira--envuelve">
            {[
              ['Hasta $15', '1500'],
              ['Hasta $25', '2500'],
              ['Hasta $40', '4000'],
              ['Hasta $80', '8000'],
            ].map(([texto, valor]) => (
              <button
                key={valor}
                type="button"
                className="ficha"
                aria-pressed={precioMax === valor}
                onClick={() => setPrecioMax(precioMax === valor ? '' : valor)}
              >
                {texto}
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className="grupo">
          <legend className="campo-etiqueta">Nota mínima</legend>
          <div className="tira tira--envuelve">
            {[
              ['4 o más', '4'],
              ['4,5 o más', '4.5'],
            ].map(([texto, valor]) => (
              <button
                key={valor}
                type="button"
                className="ficha"
                aria-pressed={ratingMin === valor}
                onClick={() => setRatingMin(ratingMin === valor ? '' : valor)}
              >
                {texto}
              </button>
            ))}
          </div>
        </fieldset>

        <div className="hoja__pie">
          <button
            type="button"
            className="boton boton--llano"
            onClick={() =>
              onAplicar({ zona: null, categoria: null, precio_max: null, rating_min: null })
            }
          >
            Quitar filtros
          </button>
          <button
            type="button"
            className="boton boton--cierra"
            onClick={() =>
              onAplicar({
                zona: zona || null,
                categoria: categoria || null,
                precio_max: precioMax || null,
                rating_min: ratingMin || null,
              })
            }
          >
            Ver resultados
          </button>
        </div>
      </div>
    </>
  )
}
