'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto, Vacio } from '@/componentes/estados'
import { Iconos } from '@/componentes/pestanas'
import { conConsola, leerSesionDeConsola, type SesionDeConsola } from '@/lib/consola'

/**
 * La cola de reseñas reportadas.
 *
 * Se decide una por una y con el texto entero delante: una cola de moderación con el texto
 * recortado se resuelve a ojo, y lo que se está decidiendo es si la opinión de una persona sobre
 * un negocio real se queda o se va.
 *
 * Las dos salidas están al mismo nivel. Poner «ocultar» como acción principal empuja a ocultar,
 * y la mayoría de los reportes son de un negocio al que no le gustó una nota de tres.
 */

type Reporte = {
  reporte_id: string
  resena_id: string
  negocio: string
  negocio_slug: string
  nota: number
  texto: string | null
  motivo: string
  reportado_por: string
  estado_resena: string
  estado_reporte: string
  fecha: string
}

const MOTIVOS: Record<string, string> = {
  ofensiva: 'Ofensiva',
  falsa: 'Dice que es falsa',
  spam: 'Spam',
  datos_personales: 'Tiene datos personales',
  otra: 'Otra razón',
}

export default function Moderacion() {
  const [sesion, setSesion] = useState<SesionDeConsola | null>(null)
  const [cola, setCola] = useState<Reporte[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [resolviendo, setResolviendo] = useState<string | null>(null)

  useEffect(() => setSesion(leerSesionDeConsola()), [])

  const cargar = useCallback(async (actual: SesionDeConsola) => {
    setError(null)
    try {
      setCola(
        await conConsola<Reporte[]>('/api/v1/consola/moderacion/resenas', { token: actual.acceso }),
      )
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar la cola.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  async function resolver(reporte: Reporte, accion: 'ocultar' | 'mantener') {
    if (!sesion) return
    setResolviendo(reporte.reporte_id)
    try {
      await conConsola(`/api/v1/consola/moderacion/resenas/${reporte.reporte_id}`, {
        metodo: 'POST',
        token: sesion.acceso,
        cuerpo: { accion },
      })
      // Se saca de la cola en el momento en vez de recargarla entera: moderar es una ráfaga de
      // decisiones seguidas y esperar a la red entre cada una la hace inutilizable.
      setCola((previos) => (previos ?? []).filter((r) => r.reporte_id !== reporte.reporte_id))
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo resolver el reporte.')
    } finally {
      setResolviendo(null)
    }
  }

  return (
    <div className="contenedor">
      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Moderación</h1>
        {cola && cola.length > 0 && <span className="tenue cifras">{cola.length} sin resolver</span>}
      </div>

      {error && (
        <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
      )}

      {cola === null && !error && <Esqueleto filas={3} alto={140} etiqueta="Cargando la cola" />}

      {cola !== null && cola.length === 0 && (
        <Vacio
          icono={Iconos.moderacion}
          titulo="No hay nada que moderar"
          texto="Aquí aparecen las reseñas que alguien ha reportado, con el motivo y el texto entero."
        />
      )}

      {cola && cola.length > 0 && (
        <ul className="reportes escalona">
          {cola.map((r) => (
            <li key={r.reporte_id} className="reporte">
              <p className="reporte__cabeza">
                <span className="etiqueta">{MOTIVOS[r.motivo] ?? r.motivo}</span>
                <span className="tenue">
                  {r.negocio} · reportado por {r.reportado_por}
                </span>
              </p>

              <p className="resena__cabeza" style={{ marginTop: 'var(--espacio-3)' }}>
                <span className="cifras" aria-label={`${r.nota} de 5`}>
                  {'★'.repeat(r.nota)}
                  <span className="tenue">{'★'.repeat(5 - r.nota)}</span>
                </span>
              </p>
              {r.texto ? (
                <p className="reporte__texto medida">{r.texto}</p>
              ) : (
                <p className="tenue">La reseña no tiene texto: solo la nota.</p>
              )}

              <div className="acciones" style={{ marginTop: 'var(--espacio-4)' }}>
                <button
                  type="button"
                  className="boton boton--secundario"
                  disabled={resolviendo === r.reporte_id}
                  onClick={() => resolver(r, 'mantener')}
                >
                  Mantenerla
                </button>
                <button
                  type="button"
                  className="boton boton--secundario"
                  disabled={resolviendo === r.reporte_id}
                  onClick={() => resolver(r, 'ocultar')}
                >
                  Ocultarla
                </button>
                <a
                  className="boton boton--llano"
                  href={`/${r.negocio_slug}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Ver la ficha
                </a>
              </div>
              <p className="tenue" style={{ marginTop: 'var(--espacio-2)', fontSize: 'var(--tipografia-tamano-menor)' }}>
                Ocultarla la retira del perfil y recalcula la nota del negocio.
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
