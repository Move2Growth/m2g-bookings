'use client'

import Link from 'next/link'
import { useState } from 'react'

/**
 * Calendario de mes para elegir día de cita.
 *
 * **Es a propósito el patrón de toda la vida**: rejilla de siete columnas, lunes a domingo,
 * flechas para cambiar de mes, el día de hoy señalado y los días sin hueco apagados. Aquí no se
 * innova: quien reserva una cita ya sabe usar un calendario, y cualquier cosa más lista que esto
 * se paga en gente que no reserva. Lo de la marca entra en el color y en la letra, no en la
 * mecánica.
 *
 * La tira de siete días que había antes solo dejaba llegar a una semana vista: quien quería hora
 * para dentro de tres semanas no tenía por dónde pedirla.
 */

const DIAS_CABECERA = ['L', 'M', 'X', 'J', 'V', 'S', 'D']

/** Lunes = 0. `getDay()` cuenta desde el domingo y aquí la semana empieza en lunes. */
function columnaDe(dia: Date): number {
  return (dia.getDay() + 6) % 7
}

function iso(dia: Date): string {
  const y = dia.getFullYear()
  const m = String(dia.getMonth() + 1).padStart(2, '0')
  const d = String(dia.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function mismoDia(a: Date, b: Date): boolean {
  return iso(a) === iso(b)
}

export function Calendario({
  diaElegido,
  diasConHueco,
  enlaceBase,
  desde = new Date(),
  meses = 3,
}: {
  /** El día que está mirando ahora mismo. */
  diaElegido: Date
  /** Días con al menos un hueco, en `YYYY-MM-DD`. Lo que no está aquí se apaga. */
  diasConHueco: Set<string>
  /**
   * Principio de la URL de cada día; el calendario le pega `YYYY-MM-DD` y el ancla.
   * Es un texto y no una función porque esto corre en el cliente y las funciones no cruzan
   * la frontera desde el servidor.
   */
  enlaceBase: string
  /** No se puede pedir hora para ayer. */
  desde?: Date
  /** Cuántos meses hacia delante se dejan abrir. */
  meses?: number
}) {
  const hoy = new Date(desde)
  hoy.setHours(0, 0, 0, 0)
  const [mes, setMes] = useState(() => new Date(diaElegido.getFullYear(), diaElegido.getMonth(), 1))

  const limite = new Date(hoy.getFullYear(), hoy.getMonth() + meses, 1)
  const primeroDelMesDeHoy = new Date(hoy.getFullYear(), hoy.getMonth(), 1)
  const puedeAtras = mes > primeroDelMesDeHoy
  const puedeAdelante = mes < limite

  const nombreMes = new Intl.DateTimeFormat('es-PA', { month: 'long', year: 'numeric' }).format(mes)
  const diasDelMes = new Date(mes.getFullYear(), mes.getMonth() + 1, 0).getDate()
  const huecosAntes = columnaDe(new Date(mes.getFullYear(), mes.getMonth(), 1))

  const celdas: (Date | null)[] = [
    ...Array.from({ length: huecosAntes }, () => null),
    ...Array.from({ length: diasDelMes }, (_, i) => new Date(mes.getFullYear(), mes.getMonth(), i + 1)),
  ]

  return (
    <div className="calendario">
      <div className="calendario__cabecera">
        <button
          type="button"
          className="calendario__flecha"
          onClick={() => setMes(new Date(mes.getFullYear(), mes.getMonth() - 1, 1))}
          disabled={!puedeAtras}
          aria-label="Mes anterior"
        >
          ‹
        </button>
        <span className="calendario__mes" aria-live="polite">
          {nombreMes}
        </span>
        <button
          type="button"
          className="calendario__flecha"
          onClick={() => setMes(new Date(mes.getFullYear(), mes.getMonth() + 1, 1))}
          disabled={!puedeAdelante}
          aria-label="Mes siguiente"
        >
          ›
        </button>
      </div>

      <div className="calendario__semana" aria-hidden="true">
        {DIAS_CABECERA.map((d, i) => (
          <span key={`${d}-${i}`}>{d}</span>
        ))}
      </div>

      <div className="calendario__dias" role="grid" aria-label="Elegir día">
        {celdas.map((dia, i) => {
          if (!dia) return <span key={`vacio-${i}`} className="calendario__hueco" />

          const pasado = dia < hoy
          const hayHueco = diasConHueco.has(iso(dia))
          const elegido = mismoDia(dia, diaElegido)
          const esHoy = mismoDia(dia, hoy)

          // Sin hueco o en el pasado: se ve, pero no se puede pulsar. Esconder los días
          // llenos deja al cliente sin saber si es que no hay hora o si la web falla.
          if (pasado || !hayHueco) {
            return (
              <span
                key={iso(dia)}
                className={`calendario__dia calendario__dia--apagado${esHoy ? ' calendario__dia--hoy' : ''}`}
                aria-disabled="true"
                title={pasado ? 'Día pasado' : 'Sin horas libres'}
              >
                {dia.getDate()}
              </span>
            )
          }

          return (
            <Link
              key={iso(dia)}
              href={`${enlaceBase}${iso(dia)}#horas`}
              scroll={false}
              className={`calendario__dia${elegido ? ' calendario__dia--elegido' : ''}${esHoy ? ' calendario__dia--hoy' : ''}`}
              aria-current={elegido ? 'date' : undefined}
            >
              {dia.getDate()}
              <span className="calendario__punto" aria-hidden="true" />
            </Link>
          )
        })}
      </div>

      <p className="calendario__leyenda">
        <span className="calendario__punto calendario__punto--suelto" aria-hidden="true" /> con horas
        libres · los días apagados no tienen
      </p>
    </div>
  )
}
