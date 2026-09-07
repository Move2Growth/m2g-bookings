'use client'

import { useCallback, useEffect, useState } from 'react'
import { Error as BloqueDeError, Esqueleto } from '@/componentes/estados'
import { conSesion, leerSesion, type Sesion } from '@/lib/sesion'
import { dinero, type Caja, type ProfesionalDelLocal } from '@/lib/dueno'

/**
 * Finanzas: **lo facturado por día, por semana y por mes**.
 *
 * Cuatro reglas, y ninguna es de diseño:
 *
 * · **El dinero se pinta con el importe que manda la API.** Ni un total se recompone sumando las
 *   barras: la API ya devuelve `importe_centavos` y `ticket_medio_centavos`, y dos aritméticas
 *   distintas acaban dando dos cifras distintas el día que hay un redondeo de por medio.
 * · **Las citas sin precio salen con el mismo tamaño que el total.** Es la cifra que pidió Luis y
 *   la que evita el engaño: un salón con la mitad de la carta «a consultar» ve un total que
 *   parece completo y no lo es. Aquí se dice cuántas son y que no suman.
 * · **Solo cuenta lo atendido.** Una cita confirmada es una promesa; la caja de hoy a media
 *   mañana es pequeña a propósito, y el rótulo lo dice para que nadie crea que falta dinero.
 * · **Nada se pinta en blanco.** Un periodo sin nada dice que no hubo nada, no se queda vacío.
 */

type Agrupacion = 'dia' | 'semana' | 'mes'

/** Los tres periodos que se miran de verdad, con la agrupación que tiene sentido en cada uno. */
const RANGOS: { id: string; texto: string; dias: number; agrupacion: Agrupacion }[] = [
  { id: 'semana', texto: 'Últimos 7 días', dias: 7, agrupacion: 'dia' },
  { id: 'mes', texto: 'Últimos 30 días', dias: 30, agrupacion: 'dia' },
  { id: 'trimestre', texto: 'Últimos 3 meses', dias: 90, agrupacion: 'semana' },
  { id: 'ano', texto: 'Último año', dias: 365, agrupacion: 'mes' },
]

const NOMBRE_DE_AGRUPACION: Record<Agrupacion, string> = {
  dia: 'Por día',
  semana: 'Por semana',
  mes: 'Por mes',
}

export default function Finanzas() {
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [rango, setRango] = useState(RANGOS[1])
  const [agrupacion, setAgrupacion] = useState<Agrupacion>(RANGOS[1].agrupacion)
  const [quien, setQuien] = useState<string | null>(null)
  const [equipo, setEquipo] = useState<ProfesionalDelLocal[]>([])
  const [caja, setCaja] = useState<Caja | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => setSesion(leerSesion()), [])

  useEffect(() => {
    if (!sesion) return
    // Si el equipo no carga, la pantalla sigue sirviendo: se pierde el filtro por persona, no la
    // caja. Por eso este fallo no se propaga al bloque de error de arriba.
    conSesion<ProfesionalDelLocal[]>('/api/v1/negocio/profesionales', { token: sesion.acceso })
      .then((gente) => setEquipo(gente.filter((p) => p.activo)))
      .catch(() => setEquipo([]))
  }, [sesion])

  const cargar = useCallback(
    async (actual: Sesion, dias: number, como: Agrupacion, profesional: string | null) => {
      setCargando(true)
      setError(null)
      const hasta = new Date()
      const desde = new Date(hasta)
      desde.setDate(desde.getDate() - dias)
      const parametros = new URLSearchParams({
        desde: desde.toISOString(),
        hasta: hasta.toISOString(),
        agrupacion: como,
      })
      if (profesional) parametros.set('profesional', profesional)
      try {
        setCaja(
          await conSesion<Caja>(`/api/v1/negocio/finanzas?${parametros}`, { token: actual.acceso }),
        )
      } catch (fallo) {
        setError(fallo instanceof Error ? fallo.message : 'No se pudo cargar la caja.')
      } finally {
        setCargando(false)
      }
    },
    [],
  )

  useEffect(() => {
    if (sesion) void cargar(sesion, rango.dias, agrupacion, quien)
  }, [sesion, rango, agrupacion, quien, cargar])

  return (
    <div className="contenedor">
      <div className="cabeza-seccion">
        <h1 style={{ fontSize: 'var(--tipografia-tamano-titulo-3)' }}>Finanzas</h1>
      </div>

      <div className="tira" role="group" aria-label="Periodo">
        {RANGOS.map((r) => (
          <button
            key={r.id}
            type="button"
            className="ficha ficha--modo"
            aria-pressed={rango.id === r.id}
            onClick={() => {
              setRango(r)
              setAgrupacion(r.agrupacion)
            }}
          >
            {r.texto}
          </button>
        ))}
      </div>

      <div className="tira" role="group" aria-label="Agrupar">
        {(['dia', 'semana', 'mes'] as Agrupacion[]).map((a) => (
          <button
            key={a}
            type="button"
            className="ficha ficha--modo"
            aria-pressed={agrupacion === a}
            onClick={() => setAgrupacion(a)}
          >
            {NOMBRE_DE_AGRUPACION[a]}
          </button>
        ))}
      </div>

      {equipo.length > 1 && (
        <div className="tira" role="group" aria-label="De quién">
          <button
            type="button"
            className="ficha ficha--modo"
            aria-pressed={quien === null}
            onClick={() => setQuien(null)}
          >
            Todo el salón
          </button>
          {equipo.map((p) => (
            <button
              key={p.id}
              type="button"
              className="ficha ficha--modo"
              aria-pressed={quien === p.id}
              onClick={() => setQuien(p.id)}
            >
              {p.nombre}
            </button>
          ))}
        </div>
      )}

      {error && (
        <BloqueDeError
          mensaje={error}
          reintentar={sesion ? () => void cargar(sesion, rango.dias, agrupacion, quien) : undefined}
        />
      )}

      {cargando && !error && <Esqueleto filas={4} alto={92} etiqueta="Cargando la caja" />}

      {!cargando && !error && caja && (
        <>
          <div className="cifras-clave">
            <Cifra
              titulo="Facturado · solo citas atendidas"
              valor={dinero(caja.importe_centavos, caja.moneda)}
            />
            <Cifra titulo="Citas atendidas" valor={String(caja.citas)} />
            <Cifra
              titulo="Ticket medio"
              valor={dinero(caja.ticket_medio_centavos, caja.moneda)}
            />
            <Cifra titulo="Citas sin precio" valor={String(caja.citas_sin_precio)} />
          </div>

          {/* La explicación va debajo de la cifra y no en un signo de interrogación: si hay que
              tocar algo para entender un número, casi nadie lo toca y todo el mundo interpreta
              el número mal. */}
          <p
            className={`aviso ${caja.citas_sin_precio > 0 ? 'aviso--info' : ''}`}
            style={{ marginTop: 'var(--espacio-4)' }}
          >
            {caja.citas_sin_precio > 0 ? (
              <>
                {caja.citas_sin_precio}{' '}
                {caja.citas_sin_precio === 1 ? 'cita llevaba' : 'citas llevaban'} algún servicio «a
                consultar». Esas no tienen precio y suman cero, así que{' '}
                <strong>lo cobrado de verdad es más que {dinero(caja.importe_centavos, caja.moneda)}</strong>.
              </>
            ) : (
              <>
                Todas las citas de este periodo llevaban precio, así que el total está completo.
              </>
            )}
          </p>

          <Serie caja={caja} agrupacion={agrupacion} />
        </>
      )}
    </div>
  )
}

function Cifra({ titulo, valor }: { titulo: string; valor: string }) {
  return (
    <div className="cifra-clave">
      <span className="cifra-clave__valor cifra-grande cifras">{valor}</span>
      <span className="cifra-clave__titulo">{titulo}</span>
    </div>
  )
}

/**
 * La serie del periodo, dibujada con divs.
 *
 * Una librería de gráficas son cientos de kilobytes para pintar rectángulos, y el presupuesto de
 * JavaScript de este producto no da para eso (ADR-0011). Cada barra lleva su cifra en texto para
 * quien navega con lector de pantalla: una gráfica que solo existe como forma no existe.
 */
function Serie({ caja, agrupacion }: { caja: Caja; agrupacion: Agrupacion }) {
  if (caja.periodos.length === 0) {
    return (
      <section className="bloque-panel">
        <h2 className="etiqueta">Cómo fue repartido</h2>
        <p className="tenue" style={{ marginTop: 'var(--espacio-3)' }}>
          En este periodo no hay ninguna cita atendida todavía. En cuanto marques una como
          atendida, aparece aquí.
        </p>
      </section>
    )
  }

  const maximo = Math.max(1, ...caja.periodos.map((p) => p.importe_centavos))
  const formato = new Intl.DateTimeFormat('es-PA', {
    day: agrupacion === 'mes' ? undefined : 'numeric',
    month: 'short',
    year: agrupacion === 'mes' ? 'numeric' : undefined,
    timeZone: caja.zona,
  })
  const mejor = caja.periodos.reduce((a, b) => (b.importe_centavos > a.importe_centavos ? b : a))

  return (
    <section className="bloque-panel">
      <div className="cabeza-seccion" style={{ marginBlock: 0 }}>
        <h2 className="etiqueta">
          {agrupacion === 'dia' ? 'Día a día' : agrupacion === 'semana' ? 'Semana a semana' : 'Mes a mes'}
        </h2>
        <span className="cifras tenue">
          mejor: {dinero(mejor.importe_centavos, caja.moneda)}
        </span>
      </div>

      <ol className="serie" aria-label="Facturado por periodo">
        {caja.periodos.map((p) => (
          <li
            key={p.inicio}
            className="serie__barra"
            title={`${formato.format(new Date(p.inicio))}: ${dinero(p.importe_centavos, caja.moneda)}`}
          >
            <span
              style={{ height: `${Math.round((p.importe_centavos / maximo) * 100)}%` }}
            />
            <span className="oculto-visualmente">
              {formato.format(new Date(p.inicio))}: {dinero(p.importe_centavos, caja.moneda)} en{' '}
              {p.citas} {p.citas === 1 ? 'cita' : 'citas'}
            </span>
          </li>
        ))}
      </ol>

      {/* Sin las dos fechas, treinta barras no dicen de cuándo a cuándo. */}
      <p className="serie__eje cifras">
        <span>{formato.format(new Date(caja.periodos[0].inicio))}</span>
        <span>{formato.format(new Date(caja.periodos[caja.periodos.length - 1].inicio))}</span>
      </p>

      {/* Y debajo, la tabla. La barra da la forma; la cifra exacta la da esto, y es lo que se
          copia a un cuaderno a fin de mes. */}
      <table className="tabla" style={{ marginTop: 'var(--espacio-4)' }}>
        <caption className="oculto-visualmente">Facturado por periodo</caption>
        <thead>
          <tr>
            <th scope="col">Cuándo</th>
            <th scope="col">Citas</th>
            <th scope="col">Facturado</th>
          </tr>
        </thead>
        <tbody>
          {[...caja.periodos].reverse().map((p) => (
            <tr key={p.inicio}>
              <td className="primera-mayuscula">{formato.format(new Date(p.inicio))}</td>
              <td className="cifras">{p.citas}</td>
              <td className="cifras">{dinero(p.importe_centavos, caja.moneda)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
