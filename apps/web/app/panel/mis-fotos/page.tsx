'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto, Vacio } from '@/componentes/estados'
import { FotoDeSalon } from '@/componentes/foto'
import { Iconos } from '@/componentes/pestanas'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * Las fotos de trabajo de un profesional, y **atarlas a un servicio del salón**.
 *
 * Atarlas es la pieza del encargo (§3): «que se vea quién hizo qué». Una foto suelta en una
 * galería es decoración; la misma foto colgando de «Balayage» convierte el catálogo del salón
 * en una prueba de quién lo hace y cómo le queda.
 *
 * **Todavía no se sube un archivo.** La API recibe una `clave` y no está decidido de dónde sale
 * ni cómo se sirve la URL —es deuda viva del tablero, compartida con Backend—, así que aquí se
 * pega una dirección. Se dice tal cual en la pantalla en vez de enseñar un botón de subir que
 * no sube: prometer un selector de archivos y luego pedir una URL es peor que pedir la URL.
 *
 * Quitar una foto está **separado** de retocarla: es lo único que no se deshace en esta
 * pantalla, y no puede compartir sitio con lo que sí.
 */

type Foto = {
  id: string
  url: string
  descripcion: string | null
  servicio_id: string | null
  posicion: number
  moderacion: string
}

type ServicioDelSalon = { id: string; nombre: string; activo: boolean }

const MODERACION: Record<string, string> = {
  pendiente: 'Esperando revisión',
  aprobada: 'Publicada',
  rechazada: 'No se publicó',
}

export default function MisFotos() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [fotos, setFotos] = useState<Foto[] | null>(null)
  const [servicios, setServicios] = useState<ServicioDelSalon[]>([])
  const [error, setError] = useState<string | null>(null)
  const [falloAlAnadir, setFalloAlAnadir] = useState<string | null>(null)

  const [direccion, setDireccion] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [servicio, setServicio] = useState('')
  const [anadiendo, setAnadiendo] = useState(false)
  const [ocupada, setOcupada] = useState<string | null>(null)
  const [confirmandoBorrado, setConfirmandoBorrado] = useState<string | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    try {
      const [mias, delSalon] = await Promise.all([
        conSesion<Foto[]>('/api/v1/mi/perfil-profesional/fotos', { token: actual.acceso }),
        // El catálogo del salón: es a lo que se atan las fotos, y sin él la mitad de la
        // pantalla no tiene sentido. Si falla, se pueden añadir fotos igual, sin servicio.
        conSesion<ServicioDelSalon[]>('/api/v1/negocio/servicios', { token: actual.acceso }).catch(
          () => [] as ServicioDelSalon[],
        ),
      ])
      setFotos(mias)
      setServicios(delSalon.filter((s) => s.activo))
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron cargar tus fotos.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  async function anadir(evento: React.FormEvent) {
    evento.preventDefault()
    if (!sesion) return
    setAnadiendo(true)
    setFalloAlAnadir(null)
    try {
      const creada = await conSesion<Foto>('/api/v1/mi/perfil-profesional/fotos', {
        metodo: 'POST',
        token: sesion.acceso,
        cuerpo: {
          clave: direccion.trim(),
          descripcion: descripcion.trim() || null,
          servicio_id: servicio || null,
          posicion: fotos?.length ?? 0,
        },
      })
      setFotos((previas) => [...(previas ?? []), creada])
      setDireccion('')
      setDescripcion('')
      setServicio('')
    } catch (fallo) {
      setFalloAlAnadir(fallo instanceof Error ? fallo.message : 'No se pudo añadir la foto.')
    } finally {
      setAnadiendo(false)
    }
  }

  /** Cambia a qué servicio cuelga una foto. La cadena vacía es «a ninguno», y eso no es un
   *  `servicio_id: null` —que significa «no lo cambies»— sino `quitar_servicio`. */
  async function atar(foto: Foto, servicioId: string) {
    if (!sesion) return
    setOcupada(foto.id)
    setError(null)
    try {
      const actualizada = await conSesion<Foto>(
        `/api/v1/mi/perfil-profesional/fotos/${foto.id}`,
        {
          metodo: 'PATCH',
          token: sesion.acceso,
          cuerpo: servicioId
            ? { servicio_id: servicioId }
            : { quitar_servicio: true },
        },
      )
      setFotos((previas) => (previas ?? []).map((f) => (f.id === foto.id ? actualizada : f)))
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cambiar el servicio.')
    } finally {
      setOcupada(null)
    }
  }

  async function quitar(foto: Foto) {
    if (!sesion) return
    setOcupada(foto.id)
    setError(null)
    try {
      await conSesion(`/api/v1/mi/perfil-profesional/fotos/${foto.id}`, {
        metodo: 'DELETE',
        token: sesion.acceso,
      })
      setFotos((previas) => (previas ?? []).filter((f) => f.id !== foto.id))
      setConfirmandoBorrado(null)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo quitar la foto.')
    } finally {
      setOcupada(null)
    }
  }

  const nombreDeServicio = (id: string | null) =>
    id ? (servicios.find((s) => s.id === id)?.nombre ?? 'Un servicio del salón') : null

  return (
    <div className="contenedor seccion" style={{ maxWidth: '46rem' }}>
      <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-2)' }}>Mis fotos</h1>
      <p className="apagado medida" style={{ marginTop: 'var(--espacio-2)' }}>
        Las que atas a un servicio salen en el catálogo del salón con tu nombre. Es lo que hace
        que se vea quién hizo qué.
      </p>

      {error && (
        <div style={{ marginTop: 'var(--espacio-4)' }}>
          <BloqueDeError
            mensaje={error}
            reintentar={sesion ? () => void cargar(sesion) : undefined}
          />
        </div>
      )}

      {fotos === null && !error && (
        <div style={{ marginTop: 'var(--espacio-5)' }}>
          <Esqueleto filas={3} alto={112} etiqueta="Cargando tus fotos" />
        </div>
      )}

      {fotos !== null && (
        <>
          <section className="bloque-panel">
            <h2>Añadir una foto</h2>

            {/* Se dice antes de pedir nada, no después de que alguien busque el botón de subir
                y no lo encuentre. */}
            <p className="aviso aviso--info" style={{ marginTop: 'var(--espacio-3)' }}>
              Subir un archivo desde el teléfono todavía no está montado. De momento se pega la
              dirección de una foto que ya esté en internet.
            </p>

            <form onSubmit={anadir} className="formulario" style={{ marginTop: 'var(--espacio-4)', display: 'grid', gap: 'var(--espacio-4)' }}>
              <label className="campo">
                <span>Dirección de la foto</span>
                <input
                  className="entrada"
                  type="url"
                  required
                  value={direccion}
                  onChange={(e) => setDireccion(e.target.value)}
                  placeholder="https://…"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                />
              </label>

              <label className="campo">
                <span>Qué se ve (opcional)</span>
                <input
                  className="entrada"
                  maxLength={200}
                  value={descripcion}
                  onChange={(e) => setDescripcion(e.target.value)}
                  placeholder="Fade medio con perfilado"
                />
              </label>

              <label className="campo">
                <span>De qué servicio es</span>
                <select
                  className="entrada"
                  value={servicio}
                  onChange={(e) => setServicio(e.target.value)}
                >
                  <option value="">Sin servicio, solo en mi galería</option>
                  {servicios.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.nombre}
                    </option>
                  ))}
                </select>
                <span className="campo-ayuda">
                  {servicios.length === 0
                    ? 'Todavía no tienes servicios del salón a la vista. Puedes añadirla sin atar.'
                    : 'Atada a un servicio, sale en su ficha con tu nombre.'}
                </span>
              </label>

              {falloAlAnadir && (
                <p role="alert" className="aviso aviso--error">
                  {falloAlAnadir}
                </p>
              )}

              <div className="acciones">
                <button
                  type="submit"
                  disabled={anadiendo || !direccion.trim()}
                  className="boton boton--cierra"
                >
                  {anadiendo ? 'Añadiendo…' : 'Añadir la foto'}
                </button>
              </div>
            </form>
          </section>

          <section className="bloque-panel">
            <h2>Lo que tienes puesto</h2>

            {fotos.length === 0 ? (
              <div style={{ marginTop: 'var(--espacio-4)' }}>
                <Vacio
                  icono={Iconos.ficha}
                  titulo="Todavía no has puesto ninguna foto"
                  texto={
                    <>
                      Es lo que más mira una clienta antes de elegir persona. Empieza por una de
                      tu último trabajo y átala a su servicio.
                    </>
                  }
                />
              </div>
            ) : (
              <ul className="filas" style={{ marginTop: 'var(--espacio-4)' }}>
                {fotos.map((foto) => (
                  <li key={foto.id} className="fila">
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '96px minmax(0, 1fr)',
                        gap: 'var(--espacio-4)',
                        alignItems: 'start',
                        padding: 'var(--espacio-4) 0',
                      }}
                    >
                      <FotoDeSalon
                        src={foto.url}
                        alt={foto.descripcion ?? ''}
                        ancho={192}
                        alto={144}
                        sizes="96px"
                      />

                      {/* `min-width: 0` en el hijo de la rejilla: sin él una descripción larga
                          o una URL sin espacios estira la fila y desborda a lo ancho. */}
                      <div style={{ minWidth: 0, display: 'grid', gap: 'var(--espacio-3)' }}>
                        <div style={{ minWidth: 0 }}>
                          <p style={{ margin: 0, fontWeight: 'var(--tipografia-pesos-medio)' }}>
                            {foto.descripcion || 'Sin descripción'}
                          </p>
                          <p className="dato" style={{ margin: 0 }}>
                            {nombreDeServicio(foto.servicio_id) ?? 'Solo en tu galería'} ·{' '}
                            {MODERACION[foto.moderacion] ?? foto.moderacion}
                          </p>
                        </div>

                        <label className="campo">
                          <span className="oculto-visualmente">
                            A qué servicio pertenece esta foto
                          </span>
                          <select
                            className="entrada"
                            value={foto.servicio_id ?? ''}
                            disabled={ocupada === foto.id}
                            onChange={(e) => void atar(foto, e.target.value)}
                          >
                            <option value="">Sin servicio, solo en mi galería</option>
                            {servicios.map((s) => (
                              <option key={s.id} value={s.id}>
                                {s.nombre}
                              </option>
                            ))}
                          </select>
                        </label>

                        {/* Quitar va abajo del todo y separado: es lo único de esta pantalla
                            que no se deshace. */}
                        {confirmandoBorrado === foto.id ? (
                          <div className="aviso aviso--error">
                            <p>Esta foto se quita de tu página. ¿Seguro?</p>
                            <div className="acciones-fila" style={{ marginTop: 'var(--espacio-3)' }}>
                              <button
                                type="button"
                                className="boton boton--peligro"
                                disabled={ocupada === foto.id}
                                onClick={() => void quitar(foto)}
                              >
                                Sí, quítala
                              </button>
                              <button
                                type="button"
                                className="boton boton--secundario"
                                onClick={() => setConfirmandoBorrado(null)}
                              >
                                No, dejarla
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div>
                            <button
                              type="button"
                              className="boton boton--llano"
                              onClick={() => setConfirmandoBorrado(foto.id)}
                            >
                              Quitar esta foto
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <p className="apagado medida" style={{ marginTop: 'var(--espacio-5)' }}>
            Tu oficio, tu descripción y tus redes están en{' '}
            <Link href="/panel/mi-perfil">Mi ficha</Link>.
          </p>
        </>
      )}
    </div>
  )
}
