'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto } from '@/componentes/estados'
import { Hoja } from '@/componentes/hoja'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'
import type { InvitacionCreada, MiembroDelLocal } from '@/lib/dueno'

/**
 * Personas del local: **quién trabaja aquí y con qué papel**.
 *
 * La regla que manda en esta pantalla es una sola: **un salón no puede quedarse sin ningún
 * dueño**. La API lo impide con un error propio (`NEGOCIO_SIN_DUENO`), y aquí se dice **antes**,
 * no después: al único dueño activo no se le ofrece «quitar» ni «bajar a profesional», y en su
 * fila está escrito por qué. Dejar el botón puesto y explicar el error al pulsarlo es enseñar una
 * puerta que no abre, y además le hace creer a quien la pulsa que ha roto algo.
 *
 * Lo demás es un matiz que se olvida siempre: **quitar a alguien no borra su historia**. Sus
 * citas siguen ahí y su ficha de equipo también, porque una agenda de hace tres meses sin saber
 * quién atendió no se puede leer. Lo que se corta es el acceso, y en la siguiente llamada.
 */

const PAPELES: Record<string, string> = {
  dueno: 'Dueño',
  profesional: 'Profesional',
}

const ESTADOS: Record<string, string> = {
  invitada: 'Invitación enviada, sin aceptar',
  activa: 'Dentro',
  revocada: 'Fuera del local',
}

export default function Personas() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [miembros, setMiembros] = useState<MiembroDelLocal[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [invitando, setInvitando] = useState(false)
  const [mirando, setMirando] = useState<MiembroDelLocal | null>(null)
  const [ultimaInvitacion, setUltimaInvitacion] = useState<InvitacionCreada | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    try {
      setMiembros(
        await conSesion<MiembroDelLocal[]>('/api/v1/negocio/miembros', { token: actual.acceso }),
      )
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar quién trabaja aquí.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  const dentro = (miembros ?? []).filter((m) => m.estado !== 'revocada')
  const fuera = (miembros ?? []).filter((m) => m.estado === 'revocada')
  const duenos = dentro.filter((m) => m.rol === 'dueno' && m.estado === 'activa')

  return (
    <div className="contenedor">
      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Personas del local</h1>
        <button type="button" className="boton boton--primario" onClick={() => setInvitando(true)}>
          Invitar por correo
        </button>
      </div>

      {error && (
        <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
      )}

      {miembros === null && !error && (
        <Esqueleto filas={3} alto={76} etiqueta="Cargando quién trabaja aquí" />
      )}

      {/* El aviso va arriba y siempre, no solo cuando se intenta quitar al último dueño: es la
          regla del sitio, y saberla antes evita el intento. */}
      {miembros && duenos.length === 1 && (
        <p className="aviso aviso--info">
          {duenos[0].nombre} es <strong>el único dueño</strong> de este local. No se le puede
          quitar ni bajar a profesional: un salón sin ningún dueño no lo arregla nadie desde
          dentro, porque no queda nadie que pueda invitar. Si te vas a ir, invita antes a otro
          dueño.
        </p>
      )}

      {miembros && dentro.length > 0 && (
        <ul className="filas escalona">
          {dentro.map((miembro) => (
            <li key={miembro.id} className="fila">
              <button type="button" className="fila__boton" onClick={() => setMirando(miembro)}>
                <span className="fila__principal">
                  <span className="fila__nombre">{miembro.nombre}</span>
                  <span className="fila__detalle">
                    {PAPELES[miembro.rol] ?? miembro.rol} · {ESTADOS[miembro.estado] ?? miembro.estado}
                    {miembro.correo ? ` · ${miembro.correo}` : ''}
                  </span>
                  {miembro.ultimo_dueno && (
                    <span className="fila__detalle fila__alerta">
                      Único dueño: no se puede quitar
                    </span>
                  )}
                  {miembro.estado === 'invitada' && miembro.invitacion_caduca && (
                    <span className="fila__detalle">
                      La invitación caduca el {soloFecha(miembro.invitacion_caduca)}
                    </span>
                  )}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {miembros && fuera.length > 0 && (
        <section className="bloque-panel">
          <h2 className="etiqueta">Ya no trabajan aquí</h2>
          <ul className="filas filas--apagadas" style={{ marginTop: 'var(--espacio-3)' }}>
            {fuera.map((miembro) => (
              <li key={miembro.id} className="fila">
                <button type="button" className="fila__boton" onClick={() => setMirando(miembro)}>
                  <span className="fila__principal">
                    <span className="fila__nombre">{miembro.nombre}</span>
                    <span className="fila__detalle">
                      Fuera · sus citas y su ficha siguen en el historial
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {invitando && sesion && (
        <FormularioDeInvitacion
          sesion={sesion}
          onCerrar={() => setInvitando(false)}
          onInvitada={(creada) => {
            setInvitando(false)
            setUltimaInvitacion(creada)
            void cargar(sesion)
          }}
        />
      )}

      {mirando && sesion && (
        <FichaDeMiembro
          miembro={mirando}
          sesion={sesion}
          onCerrar={() => setMirando(null)}
          onCambiado={() => {
            setMirando(null)
            void cargar(sesion)
          }}
        />
      )}

      {/* El enlace de desarrollo: mientras no haya canal de correo real, la invitación no llega a
          ninguna parte y el dueño se queda esperando. Se enseña una vez y se dice qué es. */}
      {ultimaInvitacion?.enlace_de_desarrollo && (
        <p className="aviso aviso--info" style={{ marginTop: 'var(--espacio-4)' }}>
          Todavía no hay correo de verdad en este entorno, así que el enlace de la invitación es
          este y hay que pasárselo a mano:{' '}
          <code style={{ wordBreak: 'break-all' }}>{ultimaInvitacion.enlace_de_desarrollo}</code>
        </p>
      )}
    </div>
  )
}

function soloFecha(instante: string): string {
  return new Intl.DateTimeFormat('es-PA', { day: 'numeric', month: 'long' }).format(
    new Date(instante),
  )
}

function FormularioDeInvitacion({
  sesion,
  onCerrar,
  onInvitada,
}: {
  sesion: Sesion
  onCerrar: () => void
  onInvitada: (creada: InvitacionCreada) => void
}) {
  const [correo, setCorreo] = useState('')
  const [nombre, setNombre] = useState('')
  const [rol, setRol] = useState<'dueno' | 'profesional'>('profesional')
  const [enviando, setEnviando] = useState(false)
  const [fallo, setFallo] = useState<string | null>(null)

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault()
    setEnviando(true)
    setFallo(null)
    try {
      onInvitada(
        await conSesion<InvitacionCreada>('/api/v1/negocio/miembros/invitaciones', {
          metodo: 'POST',
          token: sesion.acceso,
          cuerpo: { correo: correo.trim(), rol, nombre: nombre.trim() || null },
        }),
      )
    } catch (error) {
      setFallo(error instanceof Error ? error.message : 'No se pudo enviar la invitación.')
      setEnviando(false)
    }
  }

  return (
    <Hoja titulo="Invitar a alguien" onCerrar={onCerrar}>
      <form onSubmit={enviar} className="formulario">
        <label className="campo">
          <span>Su correo</span>
          <input
            className="entrada"
            type="email"
            value={correo}
            onChange={(e) => setCorreo(e.target.value)}
            placeholder="nombre@correo.com"
            required
            autoFocus
          />
          <span className="campo-ayuda">
            No hace falta que tenga cuenta: si no la tiene, se le crea al aceptar la invitación.
          </span>
        </label>

        <label className="campo">
          <span>Su nombre (opcional)</span>
          <input
            className="entrada"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            placeholder="Como lo conocen las clientas"
          />
        </label>

        <fieldset className="grupo">
          <legend className="campo-etiqueta">Qué papel tiene aquí</legend>
          <div className="tira tira--envuelve">
            <button
              type="button"
              className="ficha"
              aria-pressed={rol === 'profesional'}
              onClick={() => setRol('profesional')}
            >
              Profesional
            </button>
            <button
              type="button"
              className="ficha"
              aria-pressed={rol === 'dueno'}
              onClick={() => setRol('dueno')}
            >
              Dueño
            </button>
          </div>
          <p className="campo-ayuda" style={{ marginTop: 'var(--espacio-2)' }}>
            {rol === 'profesional'
              ? 'Ve su propia agenda y su horario. Ni la caja, ni el equipo, ni la configuración.'
              : 'Ve y cambia todo el local: la caja, el equipo, la ficha y las personas. Como tú.'}
          </p>
        </fieldset>

        {fallo && (
          <p role="alert" className="aviso aviso--error">
            {fallo}
          </p>
        )}

        <div className="hoja__pie">
          <button type="button" className="boton boton--llano" onClick={onCerrar}>
            Cancelar
          </button>
          <button type="submit" className="boton boton--cierra" disabled={enviando}>
            {enviando ? 'Enviando…' : 'Enviar invitación'}
          </button>
        </div>
      </form>
    </Hoja>
  )
}

function FichaDeMiembro({
  miembro,
  sesion,
  onCerrar,
  onCambiado,
}: {
  miembro: MiembroDelLocal
  sesion: Sesion
  onCerrar: () => void
  onCambiado: () => void
}) {
  const [trabajando, setTrabajando] = useState(false)
  const [fallo, setFallo] = useState<string | null>(null)
  const [confirmandoQuitar, setConfirmandoQuitar] = useState(false)

  async function cambiarPapel(rol: 'dueno' | 'profesional') {
    setTrabajando(true)
    setFallo(null)
    try {
      await conSesion(`/api/v1/negocio/miembros/${miembro.id}`, {
        metodo: 'PATCH',
        token: sesion.acceso,
        cuerpo: { rol },
      })
      onCambiado()
    } catch (error) {
      setFallo(error instanceof Error ? error.message : 'No se pudo cambiar el papel.')
      setTrabajando(false)
    }
  }

  async function quitar() {
    setTrabajando(true)
    setFallo(null)
    try {
      await conSesion(`/api/v1/negocio/miembros/${miembro.id}`, {
        metodo: 'DELETE',
        token: sesion.acceso,
      })
      onCambiado()
    } catch (error) {
      setFallo(error instanceof Error ? error.message : 'No se pudo quitar a esta persona.')
      setTrabajando(false)
    }
  }

  return (
    <Hoja titulo={miembro.nombre} onCerrar={onCerrar}>
      <dl className="datos">
        <dt>Papel</dt>
        <dd>{PAPELES[miembro.rol] ?? miembro.rol}</dd>
        <dt>Situación</dt>
        <dd>{ESTADOS[miembro.estado] ?? miembro.estado}</dd>
        {miembro.correo && (
          <>
            <dt>Correo</dt>
            <dd>{miembro.correo}</dd>
          </>
        )}
        {miembro.aceptada_en && (
          <>
            <dt>Está dentro desde</dt>
            <dd>{soloFecha(miembro.aceptada_en)}</dd>
          </>
        )}
      </dl>

      {miembro.ultimo_dueno && (
        <p className="aviso aviso--info" style={{ marginTop: 'var(--espacio-4)' }}>
          Es el <strong>único dueño</strong> de este local, así que no se le puede bajar de papel
          ni quitar. Invita antes a otro dueño y entonces sí.
        </p>
      )}

      {!miembro.ultimo_dueno && miembro.estado !== 'revocada' && (
        <>
          <fieldset className="grupo" style={{ marginTop: 'var(--espacio-5)' }}>
            <legend className="campo-etiqueta">Cambiarle el papel</legend>
            <div className="tira tira--envuelve">
              <button
                type="button"
                className="ficha"
                aria-pressed={miembro.rol === 'profesional'}
                disabled={trabajando || miembro.rol === 'profesional'}
                onClick={() => void cambiarPapel('profesional')}
              >
                Profesional
              </button>
              <button
                type="button"
                className="ficha"
                aria-pressed={miembro.rol === 'dueno'}
                disabled={trabajando || miembro.rol === 'dueno'}
                onClick={() => void cambiarPapel('dueno')}
              >
                Dueño
              </button>
            </div>
          </fieldset>

          {/* Quitar a alguien va abajo del todo y separado, y pide confirmación: es la acción de
              la que uno se arrepiente, y no puede estar pegada a las que se hacen a diario. */}
          <div className="acciones acciones--separadas">
            {confirmandoQuitar ? (
              <>
                <p className="aviso aviso--error" style={{ width: '100%' }}>
                  {miembro.nombre} pierde el acceso en cuanto pulses. Sus citas y su ficha de
                  equipo <strong>se quedan</strong>: el historial del salón no se toca.
                </p>
                <button
                  type="button"
                  className="boton boton--llano"
                  onClick={() => setConfirmandoQuitar(false)}
                >
                  Mejor no
                </button>
                <button
                  type="button"
                  className="boton boton--peligro"
                  disabled={trabajando}
                  onClick={() => void quitar()}
                >
                  {trabajando ? 'Quitando…' : 'Sí, quitarle el acceso'}
                </button>
              </>
            ) : (
              <button
                type="button"
                className="boton boton--secundario"
                onClick={() => setConfirmandoQuitar(true)}
              >
                Quitar del local
              </button>
            )}
          </div>
        </>
      )}

      {fallo && (
        <p role="alert" className="aviso aviso--error" style={{ marginTop: 'var(--espacio-4)' }}>
          {fallo}
        </p>
      )}
    </Hoja>
  )
}
