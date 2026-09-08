/**
 * La marca: el sello de **Tanda** y el nombre a su lado.
 *
 * El sello es un círculo de seis porciones al que le falta una. Esa que falta es el turno que
 * viene, que es literalmente lo que vende el producto: la clienta que vuelve cada tres semanas.
 * **No se rellena nunca.**
 *
 * Va dibujado como geometría y no como tipografía, así que no depende de que cargue una fuente,
 * se pinta con `currentColor` y funciona igual en tinta sobre hueso, en hueso sobre tinta y
 * dentro de un bloque de color. Son cinco sectores de 60 grados con 3 grados de aire entre
 * ellos: el mismo dibujo que el del brandbook, no una versión parecida.
 *
 * Un solo archivo y ninguna versión invertida a mano. Una versión invertida a mano es una
 * versión que alguien acaba usando en el sitio equivocado.
 */

import { NOMBRE } from '@/lib/marca'

/** Los cinco sectores. El sexto —de 0° a 60°, a la derecha— es el hueco. */
const SELLO =
  'M50 50L71.9 90.4A46 46 0 0 1 28.1 90.4ZM50 50L26.0 89.2A46 46 0 0 1 4.0 51.2Z' +
  'M50 50L4.0 48.8A46 46 0 0 1 26.0 10.8ZM50 50L28.1 9.6A46 46 0 0 1 71.9 9.6Z' +
  'M50 50L74.0 10.8A46 46 0 0 1 96.0 48.8Z'

export function Marca({ alto = 26 }: { alto?: number }) {
  return (
    <span
      role="img"
      aria-label={NOMBRE}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.42em',
        // El nombre se compone con la familia de rótulo y hereda el color: la marca es una sola
        // tinta, siempre.
        fontFamily: 'var(--tipografia-familia-display)',
        fontWeight: 'var(--tipografia-pesos-display)',
        fontSize: alto * 0.86,
        letterSpacing: '-0.03em',
        lineHeight: 1,
        color: 'currentColor',
      }}
    >
      <svg viewBox="0 0 100 100" height={alto} width={alto} aria-hidden="true" style={{ display: 'block' }}>
        <path d={SELLO} fill="currentColor" />
      </svg>
      {NOMBRE}
    </span>
  )
}

/**
 * El sello solo, para cuando no cabe el nombre: favicon, avatar, marca de agua. A 16 px lo que
 * queda es la mancha con su mordida, que es justo lo que tiene que quedar.
 */
export function Icono({ alto = 24 }: { alto?: number }) {
  return (
    <svg viewBox="0 0 100 100" height={alto} width={alto} role="img" aria-label={NOMBRE}>
      <path d={SELLO} fill="currentColor" />
    </svg>
  )
}
