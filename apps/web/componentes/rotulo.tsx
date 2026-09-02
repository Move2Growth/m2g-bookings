/**
 * El rótulo de un salón.
 *
 * Es **la forma por defecto de presentar un salón**, no un parche para cuando falta la foto.
 * Cuando hay fotografía, la fotografía manda; cuando no la hay, esto es la pieza normal del
 * sistema. Antes había una inicial sobre un rectángulo de color, que es lo que Luis llamó
 * vaguería y tenía razón: una inicial es un avatar, y un nombre grande es un rótulo.
 *
 * Tres ingredientes y ninguno pesa:
 *
 * · **El nombre entero** a tamaño de cartel, en versales y ancho de rótulo. Es lo único que
 *   distingue a un salón de otro, así que ocupa la pieza entera.
 * · **La trama del oficio**, dibujada a trazo y aplicada como máscara, así que hereda el color
 *   del bloque igual que el logotipo hereda con `currentColor`. Distingue el oficio y no el
 *   negocio, y eso está bien: dos barberías comparten el poste rojiblanco y nadie las confunde.
 * · **El par de colores**, elegido por la posición en la lista. Con seis tramas y cuatro pares
 *   hay veinticuatro combinaciones para once salones.
 *
 * Todo el sistema pesa 1.369 bytes comprimido, que es el 2,4 % de una sola fotografía, y no
 * añade ni una petición de red.
 */

/** De la categoría del salón a la trama que se dibuja detrás. */
const OFICIO: Record<string, string> = {
  barberia: 'barberia',
  peluqueria: 'barberia',
  unas: 'unas',
  'pestanas-cejas': 'cejas',
  maquillaje: 'maquillaje',
  depilacion: 'cejas',
  'spa-masajes': 'spa',
  estetica: 'spa',
}

/** Los cuatro pares de la paleta. El orden es el del ritmo, no el de la importancia. */
export const PARES = [
  { fondo: 'var(--color-acento)', tinta: 'var(--color-acento-texto)' },
  { fondo: 'var(--color-tinta)', tinta: 'var(--color-papel)' },
  { fondo: 'var(--color-abre)', tinta: 'var(--color-abre-texto)' },
  { fondo: 'var(--color-lienzo)', tinta: 'var(--color-tinta)' },
]

/**
 * La talla la decide **la palabra más larga**, no el ancho de la pantalla.
 *
 * Así estrecha el letrero un rotulista: manda el nombre. Se cuenta aquí, en el servidor, porque
 * calcularlo con unidades de contenedor se muerde la cola —el ancho del rótulo depende del
 * texto que hay que medir—.
 */
function talla(nombre: string) {
  const masLarga = Math.max(...nombre.split(/\s+/).map((p) => p.length))
  if (masLarga >= 10) return 'rotulo--larga'
  if (masLarga >= 7) return 'rotulo--media'
  return 'rotulo--corta'
}

/**
 * El par de colores que le toca a una posición.
 *
 * Se exporta porque hay un caso en el que el color tiene que estar **en el propio elemento** y
 * no en el rótulo: cuando el nombre se escribe encima. Si el color vive en un hermano, el texto
 * queda sin fondo real, y eso no es solo un problema de verificación: es que basta con que el
 * rótulo no cargue para que el nombre desaparezca.
 */
export function parDeRotulo(indice: number) {
  return PARES[indice % PARES.length]
}

export function Rotulo({
  nombre,
  categoria,
  indice = 0,
  talla: variante = 'cartel',
  className = '',
}: {
  nombre: string
  /** Slug de la categoría principal. Si no llega, se usa la trama de horas, que vale para todo. */
  categoria?: string | null
  /** Posición en la lista: es lo que reparte los colores para que la rejilla tenga ritmo. */
  indice?: number
  talla?: 'cartel' | 'sello' | 'fondo'
  className?: string
}) {
  const par = PARES[indice % PARES.length]
  const oficio = OFICIO[categoria ?? ''] ?? 'horas'

  return (
    <span
      className={`rotulo rotulo--${variante} oficio--${oficio} ${variante === 'cartel' ? talla(nombre) : ''} ${className}`}
      style={{ ['--rotulo-fondo' as string]: par.fondo, ['--rotulo-tinta' as string]: par.tinta }}
      // El nombre ya está escrito al lado en todos los sitios donde se usa esto, así que
      // repetirlo para un lector de pantalla es ruido.
      aria-hidden="true"
    >
      {/* La talla «fondo» solo pinta color y trama: se usa donde el nombre ya está escrito
          encima, como en las celdas de categoría de la portada. Meter ahí el texto del rótulo
          lo escribiría dos veces y a un tamaño que no cabe en 132 px de alto. */}
      {variante !== 'fondo' && (
        <span className="rotulo__texto">{variante === 'sello' ? nombre.trim().charAt(0) : nombre}</span>
      )}
    </span>
  )
}
