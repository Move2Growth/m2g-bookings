/**
 * Dónde mira el mapa antes de que exista el mapa.
 *
 * Vive **fuera del componente** por un motivo que costó una hora: `componentes/mapa.tsx` es un
 * componente de cliente, y lo que exporta un módulo de cliente **no se puede leer desde el
 * servidor** — llega vacío, sin ruido y sin error. La consecuencia fue una consulta con
 * `oeste=undefined` que la API rechazaba, una lista vacía y una pantalla que decía «buscando
 * salones» para siempre. Un módulo normal lo pueden leer los dos lados.
 */

/** El centro de Ciudad de Panamá y un zoom en el que se ven los barrios, no el país. */
export const CENTRO: [number, number] = [8.9824, -79.5199];
export const ZOOM = 14;

/**
 * Lo que se ve, **a ojo**, antes de que exista el mapa. Lo usa el servidor para traer la primera
 * lista.
 *
 * Es una aproximación deliberada y no hace falta que sea exacta: Leaflet, en cuanto arranca,
 * vuelve a preguntar por el rectángulo de verdad y sustituye la lista. Lo que se gana con esta
 * cuenta a mano es que haya algo escrito en el HTML desde el primer byte.
 */
export const RECTANGULO_DE_ARRANQUE = {
  oeste: CENTRO[1] - 0.045,
  este: CENTRO[1] + 0.045,
  sur: CENTRO[0] - 0.03,
  norte: CENTRO[0] + 0.03,
};
