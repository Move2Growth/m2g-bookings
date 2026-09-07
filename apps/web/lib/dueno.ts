/**
 * El portal del dueño: tipos y las cuatro funciones de formato que se repiten en sus pantallas.
 *
 * **Los tipos no se escriben aquí.** Salen de `@agenda/api-types`, que se genera del OpenAPI
 * que publica FastAPI (`make contrato`). Escribirlos a mano sería tener un segundo contrato que
 * se desincroniza el día que alguien renombra un campo, y el fallo aparecería en el navegador de
 * un salón y no en la compilación. Lo que hay aquí son **alias con nombre en español** de esos
 * esquemas: `Caja` se lee mejor que `components['schemas']['Caja']` en once sitios.
 *
 * El resto del archivo es formato, y tiene una regla: **el dinero se pinta con el importe que
 * manda la API y con su moneda**. Aquí no se suma, no se resta y no se prorratea nada. Un total
 * calculado en el navegador y otro calculado en el servidor acaban discrepando, y el día que
 * discrepan el que está delante de la pantalla es el dueño del salón.
 */

import type { components } from '@agenda/api-types'

type Esquemas = components['schemas']

/** El día del salón con una columna por persona. `GET /negocio/agenda/columnas`. */
export type DiaEnColumnas = Esquemas['DiaEnColumnas']
export type ColumnaDelDia = Esquemas['ColumnaDelDia']
export type CitaEnColumna = Esquemas['CitaEnColumna']
export type BloqueoEnColumna = Esquemas['BloqueoEnColumna']

/** Lo facturado en un rango. `GET /negocio/finanzas`. */
export type Caja = Esquemas['Caja']
export type PeriodoDeCaja = Esquemas['PeriodoDeCaja']

/** El equipo ordenado por importe o por número de servicios. `GET /negocio/mejor-del-mes`. */
export type FilaDelMes = Esquemas['FilaDelMes']

/** La publicidad flash del salón. `/negocio/anuncios`. */
export type AnuncioDelSalon = Esquemas['AnuncioDelSalon']

/** El parte de entradas y salidas. `GET /negocio/fichajes`. */
export type ParteDeFichaje = Esquemas['ParteDeFichaje']
export type MarcaDeFichaje = Esquemas['MarcaDeFichaje']

/** Quién trabaja en el local y con qué papel. `GET /negocio/miembros`. */
export type MiembroDelLocal = Esquemas['MiembroDelLocal']
export type InvitacionCreada = Esquemas['InvitacionCreada']

/** Una persona del equipo, tal y como la devuelve `GET /negocio/profesionales`. */
export type ProfesionalDelLocal = Esquemas['ProfesionalDelPanel']

/** Una categoría global del catálogo. `GET /catalogo/categorias`. */
export type CategoriaGlobal = Esquemas['CategoriaGlobal']

/**
 * Dinero, con la moneda que dice la API.
 *
 * Divide entre cien y ya: los centavos son la unidad menor y pasarlos a unidades es formato, no
 * cálculo. Lo que **no** se hace en el navegador es sumar periodos para reconstruir un total:
 * ese total ya viene, y calcularlo aquí sería tener dos verdades.
 */
export function dinero(centavos: number, moneda = 'USD'): string {
  return new Intl.NumberFormat('es-PA', {
    style: 'currency',
    currency: moneda,
    // Con el símbolo largo sale «USD 18.00», y en el resto del producto un precio es «$18.00».
    // Dos formas de escribir la misma cifra en la misma aplicación se leen como dos cosas.
    currencyDisplay: 'narrowSymbol',
    minimumFractionDigits: 2,
  }).format(centavos / 100)
}

/**
 * «7 h 30», «45 min», «—».
 *
 * Los partes de fichaje se leen en horas y minutos, nunca en «450 minutos», que no se dice ni se
 * compara de un vistazo con una jornada.
 */
export function horasYMinutos(minutos: number): string {
  if (minutos <= 0) return '0 h'
  const horas = Math.floor(minutos / 60)
  const resto = minutos % 60
  if (horas === 0) return `${resto} min`
  return resto === 0 ? `${horas} h` : `${horas} h ${resto}`
}

/**
 * La hora **en la zona del negocio**, no en la del navegador.
 *
 * Es ADR-0003 y no es una sutileza: un dueño que mira su agenda desde Madrid tiene que ver las
 * diez de la mañana de Panamá, porque a esa hora es cuando entra la clienta por la puerta. Si se
 * pinta en la zona del navegador, la agenda entera se desplaza cinco horas sin avisar.
 */
export function horaEn(zona: string): Intl.DateTimeFormat {
  return new Intl.DateTimeFormat('es-PA', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: zona,
  })
}

/** «sábado, 7 de septiembre», en la zona del negocio. */
export function fechaEn(zona: string): Intl.DateTimeFormat {
  return new Intl.DateTimeFormat('es-PA', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    timeZone: zona,
  })
}

/** El día en `AAAA-MM-DD`, que es como lo pide la API. Sin pasar por UTC, que cambia el día. */
export function diaISO(fecha: Date): string {
  const mes = String(fecha.getMonth() + 1).padStart(2, '0')
  const dia = String(fecha.getDate()).padStart(2, '0')
  return `${fecha.getFullYear()}-${mes}-${dia}`
}

/** Hoy más `dias`, a las 00:00 del navegador. Sirve para navegar por días y por meses. */
export function diaRelativo(dias: number): Date {
  const fecha = new Date()
  fecha.setDate(fecha.getDate() + dias)
  fecha.setHours(0, 0, 0, 0)
  return fecha
}

/**
 * Las etiquetas de los estados de una reserva.
 *
 * Los enumerados del backend viajan **en minúsculas con guion bajo** (ADR-0012) y aquí se
 * comparan tal cual. El `?? estado` del final no es pereza: si mañana la API añade un estado, la
 * pantalla enseña su nombre crudo en vez de un hueco en blanco.
 */
export const ESTADO_DE_RESERVA: Record<string, string> = {
  pendiente: 'Por confirmar',
  confirmada: 'Confirmada',
  completada: 'Atendida',
  no_show: 'No vino',
  cancelada_cliente: 'Cancelada por la clienta',
  cancelada_negocio: 'Cancelada',
}
