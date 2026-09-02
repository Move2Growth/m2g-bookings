'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto } from '@/componentes/estados'
import { Hoja } from '@/componentes/hoja'
import { conConsola, leerSesionDeConsola, type SesionDeConsola } from '@/lib/consola'

/**
 * Todos los negocios de la plataforma.
 *
 * Lo que se hace aquí de verdad es **buscar uno concreto porque alguien ha escrito a soporte**,
 * así que el buscador va arriba y la fila enseña lo que hace falta para saber si es ese: estado,
 * cuántas reservas lleva y su nota.
 *
 * Suspender pide un motivo obligatorio. Una suspensión sin motivo es una decisión que dentro de
 * seis meses nadie sabe explicar, y este es un negocio de una persona real.
 */

type Negocio = {
  id: string
  slug: string
  nombre: string
  estado: string
  direccion: string | null
  creado: string
  publicado: string | null
  suspendido: string | null
  motivo_suspension: string | null
  reservas: number
  clientes: number
  reviews: number
  rating: number | null
}

export default function NegociosEnConsola() {
  const [sesion, setSesion] = useState<SesionDeConsola | null>(null)
  const [negocios, setNegocios] = useState<Negocio[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busqueda, setBusqueda] = useState('')
  const [abierto, setAbierto] = useState<Negocio | null>(null)

  useEffect(() => setSesion(leerSesionDeConsola()), [])

  const cargar = useCallback(async (actual: SesionDeConsola) => {
    setError(null)
    try {
      setNegocios(await conConsola<Negocio[]>('/api/v1/consola/negocios', { token: actual.acceso }))
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron cargar los negocios.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  const termino = busqueda.trim().toLowerCase()
  const visibles = (negocios ?? []).filter(
    (n) =>
      termino === '' ||
      n.nombre.toLowerCase().includes(termino) ||
      n.slug.includes(termino) ||
      (n.direccion ?? '').toLowerCase().includes(termino),
  )

  return (
    <div className="contenedor">
      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Negocios</h1>
        {negocios && (
          <span className="tenue cifras">
            {negocios.filter((n) => n.estado === 'publicado').length} publicados de {negocios.length}
          </span>
        )}
      </div>

      <label className="campo" style={{ marginBottom: 'var(--espacio-4)' }}>
        <span className="oculto-visualmente">Buscar un negocio</span>
        <input
          className="entrada"
          type="search"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Buscar por nombre, dirección o identificador"
        />
      </label>

      {error && (
        <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
      )}

      {negocios === null && !error && <Esqueleto filas={6} alto={64} etiqueta="Cargando los negocios" />}

      {visibles.length > 0 && (
        <ul className="filas">
          {visibles.map((n) => (
            <li key={n.id} className="fila">
              <button type="button" className="fila__boton" onClick={() => setAbierto(n)}>
                <span className="fila__principal">
                  <span className="fila__nombre">
                    {n.nombre}{' '}
                    <span className={`estado estado--consola-${n.estado}`}>{n.estado}</span>
                  </span>
                  <span className="fila__detalle cifras">
                    {n.reservas} reservas · {n.clientes} clientas
                    {n.rating !== null && ` · ★ ${n.rating.toFixed(1)} (${n.reviews})`}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {negocios !== null && visibles.length === 0 && (
        <p className="tenue">Ningún negocio con eso.</p>
      )}

      {abierto && sesion && (
        <FichaEnConsola
          negocio={abierto}
          sesion={sesion}
          onCerrar={() => setAbierto(null)}
          onCambiado={() => {
            setAbierto(null)
            void cargar(sesion)
          }}
        />
      )}
    </div>
  )
}

function FichaEnConsola({
  negocio,
  sesion,
  onCerrar,
  onCambiado,
}: {
  negocio: Negocio
  sesion: SesionDeConsola
  onCerrar: () => void
  onCambiado: () => void
}) {
  const [motivo, setMotivo] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [fallo, setFallo] = useState<string | null>(null)
  const fecha = new Intl.DateTimeFormat('es-PA', { day: 'numeric', month: 'short', year: 'numeric' })

  return (
    <Hoja titulo={negocio.nombre} onCerrar={onCerrar}>
      <dl className="datos">
        <dt>Estado</dt>
        <dd>{negocio.estado}</dd>
        <dt>Dirección</dt>
        <dd>{negocio.direccion ?? '—'}</dd>
        <dt>Alta</dt>
        <dd className="cifras">{fecha.format(new Date(negocio.creado))}</dd>
        {negocio.publicado && (
          <>
            <dt>Publicado</dt>
            <dd className="cifras">{fecha.format(new Date(negocio.publicado))}</dd>
          </>
        )}
        <dt>Reservas</dt>
        <dd className="cifras">{negocio.reservas}</dd>
        <dt>Ficha</dt>
        <dd>
          <a href={`/${negocio.slug}`} target="_blank" rel="noreferrer">
            /{negocio.slug}
          </a>
        </dd>
      </dl>

      {negocio.estado === 'suspendido' ? (
        <>
          {negocio.motivo_suspension && (
            <p className="aviso aviso--error" style={{ marginTop: 'var(--espacio-4)' }}>
              Suspendido por: {negocio.motivo_suspension}
            </p>
          )}
          <div className="hoja__pie">
            <button type="button" className="boton boton--llano" onClick={onCerrar}>
              Cerrar
            </button>
            <button
              type="button"
              className="boton boton--cierra"
              disabled={ocupado}
              onClick={async () => {
                setOcupado(true)
                try {
                  await conConsola(`/api/v1/consola/negocios/${negocio.id}/reactivar`, {
                    metodo: 'POST',
                    token: sesion.acceso,
                  })
                  onCambiado()
                } catch (error) {
                  setFallo(error instanceof Error ? error.message : 'No se pudo reactivar.')
                  setOcupado(false)
                }
              }}
            >
              Reactivar
            </button>
          </div>
        </>
      ) : (
        <>
          <label className="campo" style={{ marginTop: 'var(--espacio-5)' }}>
            <span>Motivo de la suspensión</span>
            <input
              className="entrada"
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Qué pasó, en una frase"
            />
            <span className="tenue" style={{ fontSize: 'var(--tipografia-tamano-menor)' }}>
              Queda registrado. Dentro de seis meses esta frase es lo único que explica la
              decisión.
            </span>
          </label>

          {fallo && (
            <p role="alert" className="aviso aviso--error">
              {fallo}
            </p>
          )}

          <div className="hoja__pie">
            <button type="button" className="boton boton--llano" onClick={onCerrar}>
              Cerrar
            </button>
            <button
              type="button"
              className="boton boton--peligro"
              disabled={ocupado || motivo.trim().length < 4}
              onClick={async () => {
                setOcupado(true)
                setFallo(null)
                try {
                  await conConsola(`/api/v1/consola/negocios/${negocio.id}/suspender`, {
                    metodo: 'POST',
                    token: sesion.acceso,
                    cuerpo: { motivo: motivo.trim() },
                  })
                  onCambiado()
                } catch (error) {
                  setFallo(error instanceof Error ? error.message : 'No se pudo suspender.')
                  setOcupado(false)
                }
              }}
            >
              Suspender
            </button>
          </div>
        </>
      )}
    </Hoja>
  )
}
