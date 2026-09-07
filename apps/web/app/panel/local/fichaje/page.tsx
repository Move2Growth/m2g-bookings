'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto, Vacio } from '@/componentes/estados'
import { Iconos } from '@/componentes/pestanas'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'
import { horasYMinutos, type ParteDeFichaje, type ProfesionalDelLocal } from '@/lib/dueno'

/**
 * Fichaje: **el interruptor de cada persona** y el parte de horas.
 *
 * El encargo trae dos condiciones y las dos mandan sobre esta pantalla:
 *
 * · **Es opcional y nace apagado.** No hay un interruptor para todo el salón, ni siquiera
 *   escondido: un fichaje que se enciende para todos porque alguien lo quería para uno se lee
 *   como vigilancia, y con razón. Aquí se enciende de uno en uno y se ve quién lo tiene.
 * · **Apagarlo no borra nada.** El parte de las semanas pasadas sigue siendo cierto, y la
 *   pantalla lo dice al lado del interruptor, antes de tocarlo, no en una nota al pie.
 *
 * Lo que se pinta del parte sale calculado del servidor: **una jornada abierta no suma**. Sumar
 * «hasta ahora» daría un total que crece solo mientras la pantalla está abierta, y eso no es un
 * registro horario, es un cronómetro.
 */

const RANGOS = [
  { id: '7', texto: 'Últimos 7 días', dias: 7 },
  { id: '14', texto: 'Últimos 14 días', dias: 14 },
  { id: '30', texto: 'Últimos 30 días', dias: 30 },
]

export default function Fichaje() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [equipo, setEquipo] = useState<ProfesionalDelLocal[] | null>(null)
  const [partes, setPartes] = useState<ParteDeFichaje[]>([])
  const [rango, setRango] = useState(RANGOS[0])
  const [error, setError] = useState<string | null>(null)
  const [cambiando, setCambiando] = useState<string | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion, dias: number) => {
    setError(null)
    const hasta = new Date()
    const desde = new Date(hasta)
    desde.setDate(desde.getDate() - dias)
    try {
      const [gente, parte] = await Promise.all([
        conSesion<ProfesionalDelLocal[]>('/api/v1/negocio/profesionales', { token: actual.acceso }),
        conSesion<ParteDeFichaje[]>(
          `/api/v1/negocio/fichajes?desde=${desde.toISOString()}&hasta=${hasta.toISOString()}`,
          { token: actual.acceso },
        ),
      ])
      setEquipo(gente.filter((p) => p.activo))
      setPartes(parte)
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar el fichaje.')
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion, rango.dias)
  }, [sesion, rango, cargar])

  /**
   * El interruptor cambia **en el acto** y se deshace si el servidor dice que no.
   *
   * Esperar a la respuesta para mover la casilla hace que se sienta rota: se toca, no pasa nada
   * durante medio segundo de 3G y se vuelve a tocar, con lo que se acaba de apagar lo que se
   * quería encender. Se mueve ya, se guarda detrás, y si falla se devuelve a donde estaba con el
   * error escrito al lado: eso sí se entiende.
   */
  async function cambiarInterruptor(persona: ProfesionalDelLocal, activo: boolean) {
    if (!sesion) return
    setCambiando(persona.id)
    setError(null)
    setEquipo((previo) =>
      (previo ?? []).map((p) => (p.id === persona.id ? { ...p, fichaje_activo: activo } : p)),
    )
    try {
      await conSesion(`/api/v1/negocio/profesionales/${persona.id}/fichaje`, {
        metodo: 'PUT',
        token: sesion.acceso,
        cuerpo: { activo },
      })
      await cargar(sesion, rango.dias)
    } catch (fallo) {
      setEquipo((previo) =>
        (previo ?? []).map((p) =>
          p.id === persona.id ? { ...p, fichaje_activo: !activo } : p,
        ),
      )
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cambiar el fichaje.')
    } finally {
      setCambiando(null)
    }
  }

  const encendidos = (equipo ?? []).filter((p) => p.fichaje_activo)

  return (
    <div className="contenedor">
      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Fichaje</h1>
      </div>

      <p className="tenue medida">
        Nace apagado para todo el mundo, y se enciende <strong>persona a persona</strong>. Quien lo
        tenga encendido verá en su panel dos botones: «ya llegué» y «ya salgo».
      </p>

      {error && (
        <BloqueDeError
          mensaje={error}
          reintentar={sesion ? () => void cargar(sesion, rango.dias) : undefined}
        />
      )}

      {equipo === null && !error && (
        <Esqueleto filas={3} alto={80} etiqueta="Cargando el equipo" />
      )}

      {equipo !== null && equipo.length === 0 && (
        <Vacio
          icono={Iconos.equipo}
          titulo="Todavía no hay nadie en el equipo"
          texto="El fichaje se enciende por persona, así que primero hace falta que haya alguien."
          accion={{ href: '/panel/equipo', texto: 'Ir al equipo' }}
        />
      )}

      {equipo && equipo.length > 0 && (
        <section className="bloque-panel">
          <h2 className="etiqueta">Quién ficha</h2>
          <ul className="filas" style={{ marginTop: 'var(--espacio-3)' }}>
            {equipo.map((persona) => (
              <li key={persona.id} className="fila">
                <label
                  className="interruptor"
                  style={{ padding: 'var(--espacio-3)', width: '100%' }}
                >
                  <input
                    type="checkbox"
                    checked={persona.fichaje_activo}
                    disabled={cambiando === persona.id}
                    onChange={(e) => void cambiarInterruptor(persona, e.target.checked)}
                  />
                  <span className="fila__principal">
                    <span className="fila__nombre">{persona.nombre}</span>
                    <span className="fila__detalle">
                      {cambiando === persona.id
                        ? 'guardando…'
                        : persona.fichaje_activo
                          ? 'Ficha su entrada y su salida'
                          : 'No ficha. Al encenderlo, podrá fichar desde hoy'}
                    </span>
                  </span>
                </label>
              </li>
            ))}
          </ul>
          <p className="tenue" style={{ marginTop: 'var(--espacio-3)' }}>
            Apagarlo no borra lo ya fichado: el parte de las semanas anteriores se queda como
            está.
          </p>
        </section>
      )}

      {equipo && encendidos.length > 0 && (
        <section className="bloque-panel">
          <div className="cabeza-seccion" style={{ marginBlock: 0 }}>
            <h2 className="etiqueta">Parte de horas</h2>
          </div>

          <div className="tira" role="group" aria-label="Periodo del parte">
            {RANGOS.map((r) => (
              <button
                key={r.id}
                type="button"
                className="ficha ficha--modo"
                aria-pressed={rango.id === r.id}
                onClick={() => setRango(r)}
              >
                {r.texto}
              </button>
            ))}
          </div>

          {partes.length === 0 ? (
            <p className="tenue" style={{ marginTop: 'var(--espacio-3)' }}>
              Nadie ha fichado todavía en este periodo. Las entradas aparecen aquí en cuanto
              alguien pulse «ya llegué».
            </p>
          ) : (
            <ul className="filas escalona" style={{ marginTop: 'var(--espacio-3)' }}>
              {partes.map((parte) => (
                <Parte key={parte.profesional_id} parte={parte} />
              ))}
            </ul>
          )}
        </section>
      )}

      {equipo && equipo.length > 0 && encendidos.length === 0 && (
        <p className="aviso aviso--info" style={{ marginTop: 'var(--espacio-4)' }}>
          Ahora mismo no ficha nadie, así que no hay parte de horas que enseñar. Enciende el
          interruptor de quien lo necesite y el parte aparece aquí.
        </p>
      )}
    </div>
  )
}

function Parte({ parte }: { parte: ParteDeFichaje }) {
  const [abierto, setAbierto] = useState(false)
  const hora = new Intl.DateTimeFormat('es-PA', {
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })

  return (
    <li className="fila">
      <button
        type="button"
        className="fila__boton"
        aria-expanded={abierto}
        onClick={() => setAbierto((a) => !a)}
      >
        <span className="fila__principal">
          <span className="fila__nombre">{parte.nombre}</span>
          <span className="fila__detalle">
            {parte.marcas.length === 0
              ? 'sin fichajes en este periodo'
              : `${parte.marcas.length} ${parte.marcas.length === 1 ? 'marca' : 'marcas'}`}
            {parte.jornada_abierta && (
              // Un total que no cuenta la jornada de hoy tiene que decirlo, o parece que faltan
              // horas y alguien acaba discutiendo por un número que no está mal.
              <span className="fila__alerta"> · dentro ahora mismo, sin cerrar la jornada</span>
            )}
          </span>
        </span>
        <span className="fila__cifra cifras">{horasYMinutos(parte.minutos_trabajados)}</span>
      </button>

      {abierto && (
        <div style={{ padding: '0 var(--espacio-3) var(--espacio-3)' }}>
          {parte.marcas.length === 0 ? (
            <p className="tenue">No ha fichado ningún día de este periodo.</p>
          ) : (
            <ul className="tramos">
              {parte.marcas.map((marca) => (
                <li key={marca.id} className="tramo">
                  <span className="tramo__dia primera-mayuscula">
                    {marca.clase === 'entrada' ? 'Entró' : 'Salió'}
                  </span>
                  <span className="cifras primera-mayuscula">
                    {hora.format(new Date(marca.instante))}
                  </span>
                  {/* De dónde viene la marca importa cuando hay una discusión: no es lo mismo
                      que fiche la persona a que la fiche el mostrador por ella. */}
                  <span className="tenue">
                    {marca.origen === 'dueno' ? 'apuntado desde el mostrador' : ''}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </li>
  )
}
