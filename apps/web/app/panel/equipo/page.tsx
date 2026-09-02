'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto, Vacio } from '@/componentes/estados'
import { Hoja } from '@/componentes/hoja'
import { Iconos } from '@/componentes/pestanas'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'

/**
 * El equipo del salón.
 *
 * Aquí se decide **quién hace qué**, que es lo que hace que la disponibilidad salga bien o mal.
 * Un profesional sin servicios asignados no aparece en ninguna hora libre, y un servicio que no
 * hace nadie no se puede reservar aunque esté activo: las dos cosas se avisan en la fila, donde
 * se ven, en vez de dejar que alguien las descubra el día que nadie reserva.
 *
 * Un salón de una sola persona **también tiene un profesional**: es ella. No es burocracia, es
 * lo que hace que el mismo motor sirva para uno y para seis sin dos caminos distintos.
 */

type Tramo = { dia: number; desde: string; hasta: string; clase: string }

type Profesional = {
  id: string
  nombre: string
  bio: string | null
  foto: string | null
  activo: boolean
  visible_en_marketplace: boolean
  acepta_cualquiera: boolean
  orden: number
  tiene_cuenta: boolean
  servicios: string[]
  horario: Tramo[]
  citas_futuras: number
}

type Servicio = { id: string; nombre: string; activo: boolean }

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

export default function Equipo() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [equipo, setEquipo] = useState<Profesional[] | null>(null)
  const [servicios, setServicios] = useState<Servicio[]>([])
  const [error, setError] = useState<string | null>(null)
  const [editando, setEditando] = useState<Profesional | 'nuevo' | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion) => {
    setError(null)
    try {
      const [gente, catalogo] = await Promise.all([
        conSesion<Profesional[]>('/api/v1/negocio/profesionales', { token: actual.acceso }),
        conSesion<Servicio[]>('/api/v1/negocio/servicios', { token: actual.acceso }),
      ])
      setEquipo(gente)
      setServicios(catalogo.filter((s) => s.activo))
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar tu equipo.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion)
  }, [sesion, cargar])

  return (
    <div className="contenedor">
      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Equipo</h1>
        <button type="button" className="boton boton--primario" onClick={() => setEditando('nuevo')}>
          Añadir a alguien
        </button>
      </div>

      {error && (
        <BloqueDeError mensaje={error} reintentar={sesion ? () => void cargar(sesion) : undefined} />
      )}

      {equipo === null && !error && <Esqueleto filas={3} alto={72} etiqueta="Cargando tu equipo" />}

      {equipo !== null && equipo.length === 0 && (
        <Vacio
          icono={Iconos.equipo}
          titulo="Todavía no hay nadie en el equipo"
          texto="Si trabajas sola, añádete a ti: es lo que hace que tus horas salgan en tu ficha."
        />
      )}

      {equipo && equipo.length > 0 && (
        <ul className="filas escalona">
          {equipo.map((p) => {
            const dias = new Set(p.horario.filter((t) => t.clase !== 'descanso').map((t) => t.dia))
            return (
              <li key={p.id} className="fila">
                <button type="button" className="fila__boton" onClick={() => setEditando(p)}>
                  <span className="fila__principal">
                    <span className="fila__nombre">
                      {p.nombre}
                      {!p.activo && <span className="tenue"> · desactivado</span>}
                    </span>
                    <span className="fila__detalle">
                      {p.servicios.length === 0 ? (
                        <span className="fila__alerta">sin servicios asignados</span>
                      ) : (
                        `${p.servicios.length} ${p.servicios.length === 1 ? 'servicio' : 'servicios'}`
                      )}
                      {' · '}
                      {dias.size === 0 ? (
                        <span className="fila__alerta">sin horario</span>
                      ) : (
                        `${dias.size} ${dias.size === 1 ? 'día' : 'días'} a la semana`
                      )}
                    </span>
                  </span>
                  {p.citas_futuras > 0 && (
                    <span className="fila__cifra cifras">{p.citas_futuras} por delante</span>
                  )}
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {editando && sesion && (
        <FormularioDeProfesional
          profesional={editando === 'nuevo' ? null : editando}
          servicios={servicios}
          sesion={sesion}
          onCerrar={() => setEditando(null)}
          onGuardado={() => {
            setEditando(null)
            void cargar(sesion)
          }}
        />
      )}
    </div>
  )
}

function FormularioDeProfesional({
  profesional,
  servicios,
  sesion,
  onCerrar,
  onGuardado,
}: {
  profesional: Profesional | null
  servicios: Servicio[]
  sesion: Sesion
  onCerrar: () => void
  onGuardado: () => void
}) {
  const [nombre, setNombre] = useState(profesional?.nombre ?? '')
  const [telefono, setTelefono] = useState('')
  const [bio, setBio] = useState(profesional?.bio ?? '')
  const [activo, setActivo] = useState(profesional?.activo ?? true)
  const [visible, setVisible] = useState(profesional?.visible_en_marketplace ?? true)
  const [suyos, setSuyos] = useState<Set<string>>(new Set(profesional?.servicios ?? []))
  const [horario, setHorario] = useState<Tramo[]>(
    profesional?.horario.filter((t) => t.clase !== 'descanso') ?? [],
  )
  const [guardando, setGuardando] = useState(false)
  const [fallo, setFallo] = useState<string | null>(null)

  function alternarDia(dia: number) {
    setHorario((previo) => {
      if (previo.some((t) => t.dia === dia)) return previo.filter((t) => t.dia !== dia)
      // Un día que se enciende arranca con la jornada más común de un salón. Se puede cambiar
      // debajo; lo que no puede es obligar a teclear dos horas por cada día de la semana.
      return [...previo, { dia, desde: '09:00', hasta: '18:00', clase: 'trabajo' }].sort(
        (a, b) => a.dia - b.dia,
      )
    })
  }

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault()
    setGuardando(true)
    setFallo(null)
    try {
      if (profesional) {
        await conSesion(`/api/v1/negocio/profesionales/${profesional.id}`, {
          metodo: 'PATCH',
          token: sesion.acceso,
          cuerpo: {
            nombre: nombre.trim(),
            bio: bio.trim() || null,
            activo,
            visible_en_marketplace: visible,
          },
        })
        await conSesion(`/api/v1/negocio/profesionales/${profesional.id}/servicios`, {
          metodo: 'PUT',
          token: sesion.acceso,
          cuerpo: { servicios: [...suyos] },
        })
        await conSesion(`/api/v1/negocio/profesionales/${profesional.id}/horario`, {
          metodo: 'PUT',
          token: sesion.acceso,
          cuerpo: { horario },
        })
      } else {
        await conSesion('/api/v1/negocio/profesionales', {
          metodo: 'POST',
          token: sesion.acceso,
          cuerpo: {
            nombre: nombre.trim(),
            telefono: telefono.trim() || null,
            servicios: [...suyos],
            horario: horario.map((t) => ({ dia: t.dia, abre: t.desde, cierra: t.hasta })),
          },
        })
      }
      onGuardado()
    } catch (error) {
      setFallo(error instanceof Error ? error.message : 'No se pudo guardar.')
      setGuardando(false)
    }
  }

  return (
    <Hoja titulo={profesional ? profesional.nombre : 'Añadir a alguien'} onCerrar={onCerrar}>
      <form onSubmit={guardar} className="formulario">
        <label className="campo">
          <span>Nombre</span>
          <input
            className="entrada"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            placeholder="Como lo conocen las clientas"
            required
            autoFocus
          />
        </label>

        {!profesional && (
          <label className="campo">
            <span>Su teléfono (opcional)</span>
            <input
              className="entrada cifras"
              type="tel"
              value={telefono}
              onChange={(e) => setTelefono(e.target.value)}
              placeholder="+507"
            />
            <span className="tenue" style={{ fontSize: 'var(--tipografia-tamano-menor)' }}>
              Si lo pones, esa persona puede entrar y ver su propia agenda. Nada más: ni la caja
              ni la configuración.
            </span>
          </label>
        )}

        <fieldset className="grupo">
          <legend className="campo-etiqueta">Qué hace</legend>
          {servicios.length === 0 ? (
            <p className="tenue">Cuando tengas servicios podrás asignárselos.</p>
          ) : (
            <div className="tira tira--envuelve">
              {servicios.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  className="ficha"
                  aria-pressed={suyos.has(s.id)}
                  onClick={() =>
                    setSuyos((previos) => {
                      const siguiente = new Set(previos)
                      if (siguiente.has(s.id)) siguiente.delete(s.id)
                      else siguiente.add(s.id)
                      return siguiente
                    })
                  }
                >
                  {s.nombre}
                </button>
              ))}
            </div>
          )}
        </fieldset>

        <fieldset className="grupo">
          <legend className="campo-etiqueta">Cuándo trabaja</legend>
          <div className="tira tira--envuelve">
            {DIAS.map((nombreDia, i) => (
              <button
                key={i}
                type="button"
                className="ficha"
                aria-pressed={horario.some((t) => t.dia === i)}
                onClick={() => alternarDia(i)}
              >
                {nombreDia.slice(0, 3)}
              </button>
            ))}
          </div>

          {horario.length > 0 && (
            <ul className="tramos">
              {horario.map((t) => (
                <li key={t.dia} className="tramo">
                  <span className="tramo__dia">{DIAS[t.dia]}</span>
                  <input
                    type="time"
                    className="entrada cifras"
                    value={t.desde}
                    onChange={(e) =>
                      setHorario((p) =>
                        p.map((x) => (x.dia === t.dia ? { ...x, desde: e.target.value } : x)),
                      )
                    }
                    aria-label={`${DIAS[t.dia]}, empieza a las`}
                  />
                  <span aria-hidden="true">a</span>
                  <input
                    type="time"
                    className="entrada cifras"
                    value={t.hasta}
                    onChange={(e) =>
                      setHorario((p) =>
                        p.map((x) => (x.dia === t.dia ? { ...x, hasta: e.target.value } : x)),
                      )
                    }
                    aria-label={`${DIAS[t.dia]}, termina a las`}
                  />
                </li>
              ))}
            </ul>
          )}
        </fieldset>

        {profesional && (
          <>
            <label className="interruptor">
              <input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} />
              <span>Trabaja aquí ahora mismo</span>
            </label>
            <label className="interruptor">
              <input
                type="checkbox"
                checked={visible}
                onChange={(e) => setVisible(e.target.checked)}
              />
              <span>Sale con su nombre en la ficha pública</span>
            </label>
            {profesional.citas_futuras > 0 && !activo && (
              <p className="aviso aviso--info">
                Tiene {profesional.citas_futuras} citas por delante. Al desactivarlo dejan de
                poder reservarle horas nuevas, pero esas citas siguen en pie.
              </p>
            )}
          </>
        )}

        {fallo && (
          <p role="alert" className="aviso aviso--error">
            {fallo}
          </p>
        )}

        <div className="hoja__pie">
          <button type="button" className="boton boton--llano" onClick={onCerrar}>
            Cancelar
          </button>
          <button type="submit" className="boton boton--cierra" disabled={guardando}>
            {guardando ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
      </form>
    </Hoja>
  )
}
