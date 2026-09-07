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
 *
 * Debajo van **las fotos de trabajo de los profesionales**, que no son una cola: se publican
 * solas —pre-moderarlas dejaría todas las galerías vacías el primer día— y esto es la manera de
 * retirar una. Van en la misma pantalla porque quien modera reseñas es quien modera fotos, y
 * repartirlo en dos sitios significa que uno de los dos no se mira nunca.
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

type FotoDeTrabajo = {
  foto_id: string
  profesional_id: string
  profesional: string
  negocio: string
  negocio_slug: string
  url: string | null
  descripcion: string | null
  servicio: string | null
  estado: string
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
  const [fotos, setFotos] = useState<FotoDeTrabajo[] | null>(null)
  const [decidiendo, setDecidiendo] = useState<string | null>(null)

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

  const cargarFotos = useCallback(async (actual: SesionDeConsola) => {
    try {
      setFotos(
        await conConsola<FotoDeTrabajo[]>('/api/v1/consola/moderacion/fotos', {
          token: actual.acceso,
        }),
      )
    } catch {
      // Un fallo aquí no puede tapar la cola de reseñas, que es lo urgente de esta pantalla.
      setFotos([])
    }
  }, [])

  useEffect(() => {
    if (sesion) {
      void cargar(sesion)
      void cargarFotos(sesion)
    }
  }, [sesion, cargar, cargarFotos])

  async function decidirFoto(foto: FotoDeTrabajo, accion: 'aprobar' | 'rechazar') {
    if (!sesion) return
    setDecidiendo(foto.foto_id)
    try {
      const actualizada = await conConsola<FotoDeTrabajo>(
        `/api/v1/consola/moderacion/fotos/${foto.foto_id}`,
        { metodo: 'POST', token: sesion.acceso, cuerpo: { accion } },
      )
      // Aquí **no** se saca de la lista: a diferencia de un reporte, una foto rechazada se puede
      // querer devolver, y hacerla desaparecer obligaría a buscarla otra vez para deshacerlo.
      setFotos((previas) =>
        (previas ?? []).map((f) => (f.foto_id === foto.foto_id ? actualizada : f)),
      )
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cambiar el estado de la foto.')
    } finally {
      setDecidiendo(null)
    }
  }

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

      <section style={{ marginTop: 'var(--espacio-7)' }}>
        <div className="cabeza-seccion">
          <h2 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Fotos de trabajo</h2>
          {fotos && fotos.length > 0 && (
            <span className="tenue cifras">{fotos.length} recientes</span>
          )}
        </div>

        <p className="tenue" style={{ marginBottom: 'var(--espacio-4)' }}>
          Se publican solas: aprobarlas una a una dejaría todas las galerías vacías el primer día.
          Esto es para <strong>bajar una</strong>, y la retira de la ficha pública en el acto.
        </p>

        {fotos === null && <Esqueleto filas={2} alto={110} etiqueta="Cargando las fotos" />}

        {fotos !== null && fotos.length === 0 && (
          <Vacio
            icono={Iconos.ficha}
            titulo="Ninguna foto todavía"
            texto="Cuando un profesional suba una foto de su trabajo, aparecerá aquí."
          />
        )}

        {fotos && fotos.length > 0 && (
          <ul className="reportes escalona">
            {fotos.map((f) => (
              <li key={f.foto_id} className="reporte">
                <p className="reporte__cabeza">
                  <span className="etiqueta">
                    {f.estado === 'rechazada' ? 'Retirada' : 'Publicada'}
                  </span>
                  <span className="tenue">
                    {f.profesional} · {f.negocio}
                    {f.servicio ? ` · ${f.servicio}` : ' · de su galería'}
                  </span>
                </p>

                {/* La foto, del tamaño en el que se decide. Sin verla, moderar es adivinar. */}
                {f.url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={f.url}
                    alt={f.descripcion ?? ''}
                    style={{
                      width: '100%',
                      maxWidth: '260px',
                      aspectRatio: '4 / 3',
                      objectFit: 'cover',
                      border: '1px solid var(--color-borde-fuerte)',
                    }}
                  />
                )}
                {f.descripcion && <p>{f.descripcion}</p>}

                <div className="acciones">
                  {f.estado === 'rechazada' ? (
                    <button
                      type="button"
                      className="boton boton--secundario"
                      disabled={decidiendo === f.foto_id}
                      onClick={() => decidirFoto(f, 'aprobar')}
                    >
                      Devolverla
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="boton boton--secundario"
                      disabled={decidiendo === f.foto_id}
                      onClick={() => decidirFoto(f, 'rechazar')}
                    >
                      Retirarla
                    </button>
                  )}
                  <a
                    className="boton boton--llano"
                    href={`/${f.negocio_slug}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Ver el salón
                  </a>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
