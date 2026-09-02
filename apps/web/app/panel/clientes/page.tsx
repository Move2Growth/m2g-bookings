'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto, Vacio } from '@/componentes/estados'
import { Hoja } from '@/componentes/hoja'
import { Iconos } from '@/componentes/pestanas'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * Las clientas del salón.
 *
 * No es un CRM: es la libreta. Lo que se busca aquí es **quién es esta persona que tengo
 * delante**, y para eso hacen falta tres datos: cuántas veces ha venido, cuándo fue la última y
 * cuántas veces no se presentó.
 *
 * Las ausencias son de este salón y solo de este salón (RSV-5). Una nota de «no viene» que
 * viajara entre negocios sería una lista negra compartida, y eso no lo decide una plataforma.
 */

type Cliente = {
  id: string
  nombre: string
  telefono: string | null
  correo: string | null
  completadas: number
  ausencias: number
  canceladas: number
  bloqueado: boolean
  motivo_bloqueo: string | null
  origen: string
  ultima_cita: string | null
  tiene_cuenta: boolean
}

type Cita = {
  id: string
  inicio: string
  fin: string
  estado: string
  profesional: string
  servicios: string[]
  total_centavos: number
}

export default function Clientes() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [clientes, setClientes] = useState<Cliente[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busqueda, setBusqueda] = useState('')
  const [abierto, setAbierto] = useState<Cliente | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    try {
      setClientes(await conSesion<Cliente[]>('/api/v1/negocio/clientes', { token: actual.acceso }))
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudieron cargar tus clientas.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  // El filtro es en el navegador porque la libreta de un salón de barrio son decenas de
  // personas, no miles: pedir al servidor por cada letra tecleada sería peor en 3G.
  const termino = busqueda.trim().toLowerCase()
  const visibles = (clientes ?? []).filter(
    (c) =>
      termino === '' ||
      c.nombre.toLowerCase().includes(termino) ||
      (c.telefono ?? '').includes(termino),
  )

  return (
    <div className="contenedor">
      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Clientas</h1>
        {clientes && clientes.length > 0 && (
          <span className="tenue cifras">{clientes.length} en total</span>
        )}
      </div>

      {clientes && clientes.length > 6 && (
        <label className="campo" style={{ marginBottom: 'var(--espacio-4)' }}>
          <span className="oculto-visualmente">Buscar una clienta</span>
          <input
            className="entrada"
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar por nombre o teléfono"
          />
        </label>
      )}

      {error && (
        <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
      )}

      {clientes === null && !error && <Esqueleto filas={5} alto={64} etiqueta="Cargando tus clientas" />}

      {clientes !== null && clientes.length === 0 && (
        <Vacio
          icono={Iconos.clientes}
          titulo="Todavía no tienes clientas apuntadas"
          texto="Cada persona que reserve aparece aquí con su historial, sin que tengas que apuntar nada."
        />
      )}

      {visibles.length > 0 && (
        <ul className="filas escalona">
          {visibles.map((c) => (
            <li key={c.id} className="fila">
              <button type="button" className="fila__boton" onClick={() => setAbierto(c)}>
                <span className="fila__principal">
                  <span className="fila__nombre">
                    {c.nombre}
                    {c.bloqueado && <span className="fila__alerta"> · bloqueada</span>}
                  </span>
                  <span className="fila__detalle">
                    {c.completadas === 0
                      ? 'sin citas atendidas'
                      : `${c.completadas} ${c.completadas === 1 ? 'cita' : 'citas'}`}
                    {c.ausencias > 0 && (
                      <span className="fila__alerta">
                        {' · '}
                        {c.ausencias} {c.ausencias === 1 ? 'ausencia' : 'ausencias'}
                      </span>
                    )}
                    {c.ultima_cita && ` · última el ${formatearFecha(c.ultima_cita)}`}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {visibles.length === 0 && clientes && clientes.length > 0 && (
        <p className="tenue" style={{ marginTop: 'var(--espacio-4)' }}>
          Ninguna clienta con ese nombre o ese teléfono.
        </p>
      )}

      {abierto && sesion && (
        <FichaDeCliente
          cliente={abierto}
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

function formatearFecha(iso: string) {
  return new Intl.DateTimeFormat('es-PA', { day: 'numeric', month: 'short' }).format(new Date(iso))
}

function FichaDeCliente({
  cliente,
  sesion,
  onCerrar,
  onCambiado,
}: {
  cliente: Cliente
  sesion: Sesion
  onCerrar: () => void
  onCambiado: () => void
}) {
  const [historial, setHistorial] = useState<Cita[] | null>(null)
  const [bloqueando, setBloqueando] = useState(false)

  useEffect(() => {
    conSesion<{ historial: Cita[] }>(`/api/v1/negocio/clientes/${cliente.id}`, {
      token: sesion.acceso,
    })
      .then((d) => setHistorial(d.historial ?? []))
      .catch(() => setHistorial([]))
  }, [cliente.id, sesion.acceso])

  return (
    <Hoja titulo={cliente.nombre} onCerrar={onCerrar}>
      <dl className="datos">
        {cliente.telefono && (
          <>
            <dt>Teléfono</dt>
            <dd className="cifras">
              <a href={`tel:${cliente.telefono}`}>{cliente.telefono}</a>
            </dd>
          </>
        )}
        <dt>Atendidas</dt>
        <dd className="cifras">{cliente.completadas}</dd>
        {cliente.ausencias > 0 && (
          <>
            <dt>No se presentó</dt>
            <dd className="cifras">{cliente.ausencias} veces</dd>
          </>
        )}
        {cliente.canceladas > 0 && (
          <>
            <dt>Canceló</dt>
            <dd className="cifras">{cliente.canceladas} veces</dd>
          </>
        )}
      </dl>

      <h3 className="etiqueta" style={{ marginTop: 'var(--espacio-5)' }}>
        Historial
      </h3>
      {historial === null && <Esqueleto filas={2} alto={52} etiqueta="Cargando el historial" />}
      {historial && historial.length === 0 && <p className="tenue">Todavía no hay citas.</p>}
      {historial && historial.length > 0 && (
        <ul className="filas">
          {historial.map((c) => (
            <li key={c.id} className="fila">
              <div className="fila__boton" style={{ cursor: 'default' }}>
                <span className="fila__principal">
                  <span className="fila__nombre cifras">{formatearFecha(c.inicio)}</span>
                  <span className="fila__detalle">
                    {c.servicios.join(' + ')} · {c.profesional}
                  </span>
                </span>
                <span className={`estado estado--${c.estado}`}>{c.estado.replace('_', ' ')}</span>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="hoja__pie">
        <button type="button" className="boton boton--llano" onClick={onCerrar}>
          Cerrar
        </button>
        <button
          type="button"
          className={cliente.bloqueado ? 'boton boton--secundario' : 'boton boton--peligro'}
          disabled={bloqueando}
          onClick={async () => {
            setBloqueando(true)
            try {
              await conSesion(`/api/v1/negocio/clientes/${cliente.id}`, {
                metodo: 'PATCH',
                token: sesion.acceso,
                cuerpo: { bloqueado: !cliente.bloqueado },
              })
              onCambiado()
            } finally {
              setBloqueando(false)
            }
          }}
        >
          {cliente.bloqueado ? 'Desbloquear' : 'Bloquear'}
        </button>
      </div>
    </Hoja>
  )
}
