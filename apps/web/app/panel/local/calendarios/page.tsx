'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Error as BloqueDeError, Vacio } from '@/componentes/estados'
import { Iconos } from '@/componentes/pestanas'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'
import {
  ESTADO_DE_RESERVA,
  diaISO,
  diaRelativo,
  fechaEn,
  horaEn,
  type ColumnaDelDia,
  type DiaEnColumnas,
} from '@/lib/dueno'

/**
 * Todos los calendarios: **el día del salón con una columna por persona**.
 *
 * Es la pantalla que separa a un dueño de un profesional. El profesional mira su día; el dueño
 * mira si a las cinco de la tarde hay tres sillas ocupadas y una libre, y eso solo se ve en
 * paralelo.
 *
 * ## El problema de verdad: cuatro columnas en 390 px
 *
 * No caben. Cuatro columnas legibles a 390 px salen a menos de cien píxeles cada una, y ahí no
 * entra ni «Zuleika Rodríguez». Las tres salidas posibles eran encoger la letra, apilar por
 * persona o desplazar a lo ancho, y solo una no rompe nada:
 *
 * · **Encoger la letra está descartado.** Bajar de 15 px hace ilegible la pantalla que más se
 *   mira, y en un iPhone además empieza a hacer zoom solo en los campos.
 * · **Apilar por persona pierde el paralelo**, que es justo lo que se venía a ver.
 * · **Se desplaza a lo ancho**, con la columna de horas quieta a la izquierda, y encima se puede
 *   **elegir a quién ver**: con una persona elegida, su columna ocupa la pantalla entera. Las dos
 *   cosas a la vez, porque cada una sirve para un momento distinto — el vistazo general y el
 *   «¿qué tiene Marielys esta tarde?».
 *
 * ## Dos cosas que no se hacen en el navegador
 *
 * · **La hora se pinta en la zona del negocio** (ADR-0003), no en la del navegador. Un dueño de
 *   viaje vería su salón desplazado cinco horas.
 * · **El recorte del día lo hace el servidor.** Aquí se manda `dia=AAAA-MM-DD` y la API decide
 *   dónde empieza y acaba en hora local. Calcular el rango aquí en UTC es cómo se pierden las
 *   cinco últimas citas de un sábado en Panamá.
 */

/** Fuera de este rango no hay nada que enseñar aunque el salón esté cerrado: es el marco. */
const HORA_MINIMA = 8
const HORA_MAXIMA = 20

type Pieza = {
  clave: string
  desde: number
  hasta: number
  titulo: string
  detalle: string | null
  clase: string
  descripcion: string
}

export default function Calendarios() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [desplazamiento, setDesplazamiento] = useState(0)
  const [dia, setDia] = useState<DiaEnColumnas | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [soloEsta, setSoloEsta] = useState<string | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  const cargar = useCallback(async (actual: Sesion, cuantos: number) => {
    setCargando(true)
    setError(null)
    try {
      setDia(
        await conSesion<DiaEnColumnas>(
          `/api/v1/negocio/agenda/columnas?dia=${diaISO(diaRelativo(cuantos))}`,
          { token: actual.acceso },
        ),
      )
    } catch (fallo) {
      setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar el día del salón.')
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => {
    if (sesion) void cargar(sesion, desplazamiento)
  }, [sesion, desplazamiento, cargar])

  const columnas = useMemo(() => {
    if (!dia) return []
    return soloEsta ? dia.columnas.filter((c) => c.profesional_id === soloEsta) : dia.columnas
  }, [dia, soloEsta])

  // El marco de horas se calcula sobre **todo el día**, no sobre lo filtrado: si al elegir a una
  // persona el carril cambiara de altura, comparar dos personas seguidas sería imposible.
  const marco = useMemo(() => marcoDeHoras(dia), [dia])

  // ¿Se sale algo del carril? Se mide, no se supone: depende del ancho de la ventana y de
  // cuánta gente hay, y las dos cosas cambian sin recargar.
  const carril = useRef<HTMLDivElement>(null)
  const [sobra, setSobra] = useState(false)
  useEffect(() => {
    const medir = () => {
      const caja = carril.current
      setSobra(caja !== null && caja.scrollWidth > caja.clientWidth + 1)
    }
    medir()
    window.addEventListener('resize', medir)
    return () => window.removeEventListener('resize', medir)
  })

  const hora = dia ? horaEn(dia.zona) : null
  const fecha = dia ? fechaEn(dia.zona) : null
  const citasDelDia = (dia?.columnas ?? []).reduce((n, c) => n + c.citas.length, 0)
  // Un día sin citas pero con vacaciones apuntadas **no está vacío**: si la rejilla no se pinta,
  // el dueño no ve que media plantilla está fuera y cree que ese lunes está libre.
  const hayAlgoQueVer =
    (dia?.columnas ?? []).reduce((n, c) => n + c.citas.length + c.bloqueos.length, 0) > 0

  return (
    <div className="contenedor">
      <h1 className="oculto-visualmente">Todos los calendarios del salón</h1>

      <nav aria-label="Cambiar de día" className="dias">
        <button
          type="button"
          onClick={() => setDesplazamiento((d) => d - 1)}
          className="dias__flecha"
          aria-label="Día anterior"
        >
          ←
        </button>
        <div>
          <strong className="primera-mayuscula">
            {desplazamiento === 0 ? 'Hoy, ' : ''}
            {fecha ? fecha.format(diaRelativo(desplazamiento)) : '—'}
          </strong>
          <span className="tenue" style={{ display: 'block' }}>
            {cargando
              ? 'cargando…'
              : citasDelDia === 0
                ? 'sin citas en todo el salón'
                : `${citasDelDia} ${citasDelDia === 1 ? 'cita' : 'citas'} · ${dia?.columnas.length} ${dia?.columnas.length === 1 ? 'persona' : 'personas'}`}
          </span>
        </div>
        <button
          type="button"
          onClick={() => setDesplazamiento((d) => d + 1)}
          className="dias__flecha"
          aria-label="Día siguiente"
        >
          →
        </button>
      </nav>

      {/* Elegir a quién ver. No es un filtro escondido detrás de un botón: en un teléfono es la
          mitad de la solución al problema del ancho, así que va delante. */}
      {dia && dia.columnas.length > 1 && (
        <div className="tira" role="group" aria-label="Elegir a quién ver">
          <button
            type="button"
            className="ficha"
            aria-pressed={soloEsta === null}
            onClick={() => setSoloEsta(null)}
          >
            Todas ({dia.columnas.length})
          </button>
          {dia.columnas.map((c) => (
            <button
              key={c.profesional_id}
              type="button"
              className="ficha"
              aria-pressed={soloEsta === c.profesional_id}
              onClick={() => setSoloEsta(c.profesional_id)}
            >
              {c.nombre}
            </button>
          ))}
        </div>
      )}

      {error && (
        <BloqueDeError
          mensaje={error}
          reintentar={sesion ? () => void cargar(sesion, desplazamiento) : undefined}
        />
      )}

      {/* El esqueleto tiene la forma de la rejilla, con sus columnas y su carril de horas: si
          fuera una ruedecita, la pantalla daría un salto de trescientos píxeles al llegar. */}
      {cargando && !error && <EsqueletoDeJornada marco={marco} />}

      {!cargando && !error && dia && dia.columnas.length === 0 && (
        <Vacio
          icono={Iconos.equipo}
          titulo="Todavía no hay nadie en el equipo"
          texto="Los calendarios son las personas del salón. Añade al menos a una —si trabajas sola, a ti— y aquí verás su día."
          accion={{ href: '/panel/equipo', texto: 'Ir al equipo' }}
        />
      )}

      {!cargando && !error && dia && dia.columnas.length > 0 && !hayAlgoQueVer && (
        <Vacio
          icono={Iconos.agenda}
          titulo="Nadie tiene citas este día"
          texto="Cuando alguien reserve, aparece en su columna sin que tengas que recargar."
        />
      )}

      {!cargando && !error && dia && hayAlgoQueVer && hora && (
        <div className={`jornada${columnas.length === 1 ? ' jornada--una' : ''}`}>
          <div className="jornada__horas" aria-hidden="true">
            {marco.horas.map((h) => (
              <div key={h} className="jornada__hora">
                {String(h).padStart(2, '0')}
              </div>
            ))}
          </div>

          <div className="jornada__carril" ref={carril}>
            <div className="jornada__columnas">
              {columnas.map((columna) => (
                <Columna
                  key={columna.profesional_id}
                  columna={columna}
                  dia={dia}
                  marco={marco}
                  hora={hora}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* La pista de arrastrar solo se enseña **cuando de verdad hay algo fuera de la pantalla**.
          En un portátil las cuatro columnas caben enteras, y decirle a alguien que arrastre para
          ver lo que ya está viendo es ruido que le hace dudar de si se está perdiendo algo. */}
      {!cargando && !error && dia && columnas.length > 1 && sobra && (
        <p className="tenue" style={{ marginTop: 'var(--espacio-3)' }}>
          Arrastra a los lados para ver el resto del equipo, o toca un nombre de arriba para verlo
          a pantalla completa.
        </p>
      )}
    </div>
  )
}

function Columna({
  columna,
  dia,
  marco,
  hora,
}: {
  columna: ColumnaDelDia
  dia: DiaEnColumnas
  marco: Marco
  hora: Intl.DateTimeFormat
}) {
  const inicioDelDia = new Date(dia.inicio).getTime()
  const piezas = piezasDeLaColumna(columna, inicioDelDia, hora)
  const total = (marco.hasta - marco.desde) * 60

  // La línea de «ahora» solo tiene sentido en el día que se está viviendo. En un martes de la
  // semana que viene sería una raya que no significa nada.
  const ahora = (Date.now() - inicioDelDia) / 60000
  const esHoy = ahora >= 0 && ahora <= 24 * 60
  const ahoraDentro = esHoy && ahora >= marco.desde * 60 && ahora <= marco.hasta * 60

  return (
    <div className="jornada__col">
      <div className="jornada__cab">
        <b>{columna.nombre}</b>
        <small className="cifras">
          {columna.citas.length === 0 ? 'libre' : `${columna.citas.length} cita${columna.citas.length === 1 ? '' : 's'}`}
        </small>
      </div>

      <div className="jornada__pista" style={{ height: `calc(var(--jornada-hora) * ${marco.horas.length})` }}>
        {marco.horas.map((h) => (
          <div key={h} className="jornada__linea" />
        ))}

        <div className="jornada__piezas">
          {piezas.length === 0 && <p className="jornada__libre">Sin nada apuntado</p>}

          {piezas.map((pieza) => {
            const desde = Math.max(pieza.desde, marco.desde * 60)
            const hasta = Math.min(pieza.hasta, marco.hasta * 60)
            if (hasta <= desde) return null
            return (
              <article
                key={pieza.clave}
                className={`jornada__cita ${pieza.clase}`}
                style={{
                  top: `${((desde - marco.desde * 60) / total) * 100}%`,
                  height: `${((hasta - desde) / total) * 100}%`,
                }}
                aria-label={pieza.descripcion}
                title={pieza.descripcion}
              >
                <time>{pieza.titulo}</time>
                {pieza.detalle && <b>{pieza.detalle}</b>}
              </article>
            )
          })}

          {ahoraDentro && (
            <div
              className="jornada__ahora"
              style={{ top: `${((ahora - marco.desde * 60) / total) * 100}%` }}
              aria-hidden="true"
            />
          )}
        </div>
      </div>
    </div>
  )
}

type Marco = { desde: number; hasta: number; horas: number[] }

/**
 * De qué hora a qué hora se dibuja el carril.
 *
 * Arranca en el marco de un salón normal —de ocho a ocho— y **se estira si hace falta**: la cita
 * de las siete de la mañana de un día de bodas no puede quedarse fuera de la pantalla sin que
 * nadie se entere. Se calcula sobre todas las columnas para que filtrar por persona no cambie la
 * altura de la rejilla.
 */
function marcoDeHoras(dia: DiaEnColumnas | null): Marco {
  let desde = HORA_MINIMA
  let hasta = HORA_MAXIMA
  if (dia) {
    const inicio = new Date(dia.inicio).getTime()
    for (const columna of dia.columnas) {
      for (const tramo of [...columna.citas, ...columna.bloqueos]) {
        const a = (new Date(tramo.inicio).getTime() - inicio) / 3600000
        const b = (new Date(tramo.fin).getTime() - inicio) / 3600000
        desde = Math.min(desde, Math.floor(a))
        hasta = Math.max(hasta, Math.ceil(b))
      }
    }
  }
  desde = Math.max(0, desde)
  hasta = Math.min(24, Math.max(hasta, desde + 1))
  return { desde, hasta, horas: Array.from({ length: hasta - desde }, (_, i) => desde + i) }
}

/** Citas y bloqueos de una persona, en minutos desde la medianoche local del negocio. */
function piezasDeLaColumna(
  columna: ColumnaDelDia,
  inicioDelDia: number,
  hora: Intl.DateTimeFormat,
): Pieza[] {
  const minutos = (instante: string) => (new Date(instante).getTime() - inicioDelDia) / 60000

  const citas: Pieza[] = columna.citas.map((cita) => ({
    clave: cita.id,
    desde: minutos(cita.inicio),
    hasta: minutos(cita.fin),
    titulo: `${hora.format(new Date(cita.inicio))}–${hora.format(new Date(cita.fin))}`,
    detalle: cita.cliente,
    clase: `jornada__cita--${cita.estado}`,
    descripcion: `${hora.format(new Date(cita.inicio))} · ${cita.cliente} · ${cita.servicios.join(' + ')} · ${ESTADO_DE_RESERVA[cita.estado] ?? cita.estado}`,
  }))

  const bloqueos: Pieza[] = columna.bloqueos.map((bloqueo) => ({
    clave: bloqueo.id,
    desde: minutos(bloqueo.inicio),
    hasta: minutos(bloqueo.fin),
    titulo: `${hora.format(new Date(bloqueo.inicio))}–${hora.format(new Date(bloqueo.fin))}`,
    detalle: bloqueo.motivo ?? 'No disponible',
    clase: 'jornada__cita--bloqueo',
    descripcion: `${hora.format(new Date(bloqueo.inicio))} · ${bloqueo.motivo ?? 'No disponible'}`,
  }))

  return [...bloqueos, ...citas]
}

function EsqueletoDeJornada({ marco }: { marco: Marco }) {
  return (
    <div className="jornada" role="status" aria-live="polite">
      <span className="oculto-visualmente">Cargando el día del salón…</span>
      <div className="jornada__horas" aria-hidden="true">
        {marco.horas.map((h) => (
          <div key={h} className="jornada__hora">
            {String(h).padStart(2, '0')}
          </div>
        ))}
      </div>
      <div className="jornada__carril" aria-hidden="true">
        <div className="jornada__columnas">
          {[0, 1, 2].map((i) => (
            <div key={i} className="jornada__col">
              <div className="jornada__cab">
                <b className="esqueleto__linea" style={{ width: '70%' }} />
              </div>
              <div className="jornada__pista" style={{ height: `calc(var(--jornada-hora) * ${marco.horas.length})` }}>
                {marco.horas.map((h) => (
                  <div key={h} className="jornada__linea" />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
