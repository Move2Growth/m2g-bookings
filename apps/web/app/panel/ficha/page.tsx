'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto } from '@/componentes/estados'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * La ficha pública: lo que ve una clienta que no conoce el salón.
 *
 * Se edita con una **vista previa del enlace** siempre a la vista, porque esta es la única
 * pantalla del panel cuyo resultado no está en el panel: está fuera, en el marketplace y en la
 * bio de Instagram.
 *
 * Y lleva el estado de publicación arriba del todo. Un salón en borrador no lo ve nadie, y esa
 * es la confusión número uno de quien acaba de darse de alta: cree que está fuera y no lo está.
 */

type Foto = {
  id: string
  url: string
  clase: string
  texto_alternativo: string | null
  orden: number
  moderacion: string
}

type Ficha = {
  id: string
  slug: string
  nombre: string
  descripcion: string | null
  estado: string
  zona_horaria: string
  moneda: string
  direccion: string | null
  detalle_direccion: string | null
  longitud: number | null
  latitud: number | null
  zona_id: string | null
  zona_nombre: string | null
  categorias: string[]
  atributos: string[]
  instagram: string | null
  web: string | null
  tiene_whatsapp: boolean
  fotos: Foto[]
}

type GrupoDeAtributos = {
  slug: string
  nombre: string
  grupo: string
  seleccion: string
  valores: { slug: string; nombre: string }[]
}

type Checklist = {
  tiene_servicio_activo: boolean
  tiene_horario: boolean
  tiene_ubicacion: boolean
  tiene_foto: boolean
  listo_para_publicar: boolean
  completitud: number
}

export default function FichaPublica() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [ficha, setFicha] = useState<Ficha | null>(null)
  const [atributos, setAtributos] = useState<GrupoDeAtributos[]>([])
  const [checklist, setChecklist] = useState<Checklist | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [guardado, setGuardado] = useState(false)
  const [guardando, setGuardando] = useState(false)

  const [nombre, setNombre] = useState('')
  const [descripcion, setDescripcion] = useState('')
  const [direccion, setDireccion] = useState('')
  const [detalle, setDetalle] = useState('')
  const [instagram, setInstagram] = useState('')
  const [web, setWeb] = useState('')
  const [elegidos, setElegidos] = useState<Set<string>>(new Set())

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    try {
      const [f, a, c] = await Promise.all([
        conSesion<Ficha>('/api/v1/negocio/ficha', { token: actual.acceso }),
        conSesion<GrupoDeAtributos[]>('/api/v1/negocio/atributos', { token: actual.acceso }),
        conSesion<Checklist>('/api/v1/negocio/checklist', { token: actual.acceso }),
      ])
      setFicha(f)
      setAtributos(a)
      setChecklist(c)
      setNombre(f.nombre)
      setDescripcion(f.descripcion ?? '')
      setDireccion(f.direccion ?? '')
      setDetalle(f.detalle_direccion ?? '')
      setInstagram(f.instagram ?? '')
      setWeb(f.web ?? '')
      setElegidos(new Set(f.atributos))
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar tu ficha.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault()
    if (!sesion) return
    setGuardando(true)
    setGuardado(false)
    setError(null)
    try {
      await conSesion('/api/v1/negocio/ficha', {
        metodo: 'PATCH',
        token: sesion.acceso,
        cuerpo: {
          nombre: nombre.trim(),
          descripcion: descripcion.trim() || null,
          direccion: direccion.trim() || null,
          detalle_direccion: detalle.trim() || null,
          instagram: instagram.trim().replace(/^@/, '') || null,
          web: web.trim() || null,
          atributos: [...elegidos],
        },
      })
      setGuardado(true)
      void cargar(sesion)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron guardar los cambios.')
    } finally {
      setGuardando(false)
    }
  }

  async function publicar() {
    if (!sesion) return
    setError(null)
    try {
      await conSesion('/api/v1/negocio/publicar', { metodo: 'POST', token: sesion.acceso })
      void cargar(sesion)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo publicar.')
    }
  }

  if (error && !ficha) {
    return (
      <div className="contenedor" style={{ paddingTop: 'var(--espacio-5)' }}>
        <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
      </div>
    )
  }

  return (
    <div className="contenedor">
      <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)', marginBlock: 'var(--espacio-5) var(--espacio-4)' }}>
        Tu ficha pública
      </h1>

      {ficha === null && <Esqueleto filas={4} alto={72} etiqueta="Cargando tu ficha" />}

      {ficha && (
        <>
          <section className={`estado-ficha estado-ficha--${ficha.estado}`}>
            {ficha.estado === 'publicado' ? (
              <>
                <p className="estado-ficha__titulo">Tu salón está publicado</p>
                <p className="estado-ficha__texto">
                  Se puede encontrar y reservar en{' '}
                  <Link href={`/${ficha.slug}`} target="_blank">
                    bukeo.com/{ficha.slug}
                  </Link>
                  . Ese enlace es el que va en tu bio de Instagram.
                </p>
              </>
            ) : ficha.estado === 'suspendido' ? (
              <>
                <p className="estado-ficha__titulo">Tu salón está suspendido</p>
                <p className="estado-ficha__texto">
                  No sale en las búsquedas. Escríbenos y lo revisamos.
                </p>
              </>
            ) : (
              <>
                <p className="estado-ficha__titulo">Tu salón está en borrador</p>
                <p className="estado-ficha__texto">
                  Todavía no lo ve nadie ni se puede reservar. Te falta esto:
                </p>
                {checklist && (
                  <ul className="lista-checklist">
                    {[
                      ['Un servicio activo', checklist.tiene_servicio_activo, '/panel/servicios'],
                      ['El horario del salón', checklist.tiene_horario, '/panel/horario'],
                      ['Dónde estás', checklist.tiene_ubicacion, null],
                      ['Una foto', checklist.tiene_foto, null],
                    ].map(([texto, hecho, adonde]) => (
                      <li key={texto as string} className={hecho ? 'hecho' : ''}>
                        <span aria-hidden="true">{hecho ? '✓' : '○'}</span>
                        {adonde && !hecho ? (
                          <Link href={adonde as string}>{texto as string}</Link>
                        ) : (
                          (texto as string)
                        )}
                        <span className="oculto-visualmente">{hecho ? ' — hecho' : ' — pendiente'}</span>
                      </li>
                    ))}
                  </ul>
                )}
                <button
                  type="button"
                  className="boton boton--primario"
                  onClick={publicar}
                  disabled={!checklist?.listo_para_publicar}
                  style={{ marginTop: 'var(--espacio-4)' }}
                >
                  Publicar mi salón
                </button>
              </>
            )}
          </section>

          <form onSubmit={guardar} className="formulario" style={{ marginTop: 'var(--espacio-6)' }}>
            <label className="campo">
              <span>Nombre del salón</span>
              <input
                className="entrada"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                required
              />
            </label>

            <label className="campo">
              <span>De qué va tu salón</span>
              <textarea
                className="entrada"
                rows={4}
                value={descripcion}
                onChange={(e) => setDescripcion(e.target.value)}
                placeholder="Lo que dirías a alguien que entra por primera vez. Dos o tres frases."
                maxLength={2000}
              />
              <span className="tenue cifras" style={{ fontSize: 'var(--tipografia-tamano-menor)' }}>
                {descripcion.length}/2000
              </span>
            </label>

            <label className="campo">
              <span>Dirección</span>
              <input
                className="entrada"
                value={direccion}
                onChange={(e) => setDireccion(e.target.value)}
                placeholder="Calle 47 con Vía Argentina"
              />
            </label>

            <label className="campo">
              <span>Cómo llegar (opcional)</span>
              <input
                className="entrada"
                value={detalle}
                onChange={(e) => setDetalle(e.target.value)}
                placeholder="Segundo piso, al lado de la farmacia"
              />
            </label>

            <div className="pareja">
              <label className="campo">
                <span>Instagram (opcional)</span>
                <input
                  className="entrada"
                  value={instagram}
                  onChange={(e) => setInstagram(e.target.value)}
                  placeholder="tusalon"
                />
              </label>
              <label className="campo">
                <span>Web (opcional)</span>
                <input
                  className="entrada"
                  type="url"
                  value={web}
                  onChange={(e) => setWeb(e.target.value)}
                  placeholder="https://"
                />
              </label>
            </div>

            {atributos.map((grupo) => (
              <fieldset key={grupo.slug} className="grupo">
                <legend className="campo-etiqueta">{grupo.nombre}</legend>
                <div className="tira tira--envuelve">
                  {grupo.valores.map((v) => (
                    <button
                      key={v.slug}
                      type="button"
                      className="ficha"
                      aria-pressed={elegidos.has(v.slug)}
                      onClick={() =>
                        setElegidos((previos) => {
                          const siguiente = new Set(previos)
                          if (siguiente.has(v.slug)) siguiente.delete(v.slug)
                          else {
                            // En un grupo de selección única, elegir uno quita el anterior:
                            // «solo efectivo» y «acepta tarjeta» a la vez no significan nada.
                            if (grupo.seleccion === 'unico') {
                              for (const otro of grupo.valores) siguiente.delete(otro.slug)
                            }
                            siguiente.add(v.slug)
                          }
                          return siguiente
                        })
                      }
                    >
                      {v.nombre}
                    </button>
                  ))}
                </div>
              </fieldset>
            ))}

            {error && (
              <p role="alert" className="aviso aviso--error">
                {error}
              </p>
            )}

            <div className="acciones">
              <button type="submit" className="boton boton--cierra" disabled={guardando}>
                {guardando ? 'Guardando…' : 'Guardar ficha'}
              </button>
              {guardado && (
                <p role="status" className="aviso aviso--exito">
                  Guardado.
                </p>
              )}
            </div>
          </form>
        </>
      )}
    </div>
  )
}
