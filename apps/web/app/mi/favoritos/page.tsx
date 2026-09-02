'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto, Vacio } from '@/componentes/estados'
import { FichaSalon, type SalonEnLista } from '@/componentes/ficha-salon'
import { Iconos } from '@/componentes/pestanas'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * Los salones guardados.
 *
 * Es la lista corta de sitios a los que se vuelve, y por eso el gesto principal aquí no es
 * descubrir sino **reservar otra vez**: la ficha es la misma del buscador y lleva ya el precio
 * y la próxima hora libre.
 *
 * Quitar un guardado no recarga la lista entera: se saca de la pantalla en el momento. Volver a
 * pedir todo para borrar una fila hace que el gesto se sienta pesado en 3G.
 */
export default function Favoritos() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [salones, setSalones] = useState<SalonEnLista[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    try {
      setSalones(await conSesion<SalonEnLista[]>('/api/v1/mi/favoritos', { token: actual.acceso }))
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron cargar tus guardados.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  return (
    <div className="contenedor seccion">
      <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>Guardados</h1>

      {error && (
        <div style={{ marginTop: 'var(--espacio-4)' }}>
          <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
        </div>
      )}

      {salones === null && !error && (
        <div style={{ marginTop: 'var(--espacio-5)' }}>
          <Esqueleto filas={3} alto={120} etiqueta="Cargando tus guardados" />
        </div>
      )}

      {salones !== null && salones.length === 0 && (
        <div style={{ marginTop: 'var(--espacio-5)' }}>
          <Vacio
            icono={Iconos.corazon}
            titulo="Todavía no has guardado ningún salón"
            texto="Toca el corazón en cualquier salón y lo tendrás aquí para volver sin buscarlo otra vez."
            accion={{ href: '/buscar', texto: 'Buscar salones' }}
          />
        </div>
      )}

      {salones && salones.length > 0 && (
        <ul className="resultados escalona" style={{ marginTop: 'var(--espacio-5)' }}>
          {salones.map((s, i) => (
            <FichaSalon
              key={s.slug}
              salon={s}
              indice={i}
              guardado
              onGuardar={(negocioId, ahora) => {
                if (!ahora)
                  setSalones((previos) => (previos ?? []).filter((x) => x.negocio_id !== negocioId))
              }}
            />
          ))}
        </ul>
      )}
    </div>
  )
}
