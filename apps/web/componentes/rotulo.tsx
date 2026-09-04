/**
 * El rótulo de un salón.
 *
 * Es **la forma por defecto de presentar un salón**, no un parche para cuando falta la foto.
 * Cuando hay fotografía, la fotografía manda; cuando no la hay, esto es la pieza normal.
 *
 * Sigue el rótulo de la dirección «Noche de barrio panameño»: fondo de una de las superficies,
 * el nombre en versales condensadas ocupando la pieza, el oficio debajo en pequeño, y **el tubo
 * de neón encendido arriba**, que es lo que hace que un rótulo apagado y uno encendido se
 * distingan sin leer nada.
 *
 * El prototipo que manda es `docs/marca/revision-3/direccion-1.html`.
 */

/** De la categoría del salón al oficio que se escribe debajo del nombre. */
const OFICIO: Record<string, string> = {
  barberia: 'Barbería',
  peluqueria: 'Peluquería',
  unas: 'Uñas',
  'pestanas-cejas': 'Pestañas y cejas',
  maquillaje: 'Maquillaje',
  depilacion: 'Depilación',
  'spa-masajes': 'Spa y masajes',
  estetica: 'Estética',
}

/**
 * Las cuatro superficies del rótulo. **El neón sale una de cada cuatro**: si saliera en todas
 * dejaría de ser un acento y pasaría a ser el color de fondo del producto.
 */
export const PARES = [
  { fondo: 'var(--superficie-calle-alta)', tubo: 'tubo' },
  { fondo: 'var(--superficie-local-alta)', tubo: 'tubo tubo--calido' },
  { fondo: 'var(--superficie-calle-media)', tubo: 'tubo tubo--apagado' },
  { fondo: 'var(--superficie-trastienda-alta)', tubo: 'tubo' },
]

export function parDeRotulo(indice: number) {
  return PARES[indice % PARES.length]
}

export function Rotulo({
  nombre,
  categoria,
  indice = 0,
  talla = 'cartel',
  className = '',
}: {
  nombre: string
  categoria?: string | null
  /** Posición en la lista: es lo que reparte las superficies para que la rejilla tenga ritmo. */
  indice?: number
  /** `cartel` en una cabecera, `sello` en una lista, `fondo` donde el nombre ya está escrito. */
  talla?: 'cartel' | 'sello' | 'fondo'
  className?: string
}) {
  const par = parDeRotulo(indice)
  const oficio = OFICIO[categoria ?? '']

  return (
    <span
      className={`rotulo rotulo--${talla} ${className}`}
      style={{ background: par.fondo }}
      // El nombre ya está escrito al lado en todos los sitios donde se usa esto, así que
      // repetirlo para un lector de pantalla es ruido.
      aria-hidden="true"
    >
      <span className={par.tubo} />
      {talla !== 'fondo' && (
        <>
          <span className="rotulo__nombre">
            {talla === 'sello' ? nombre.trim().charAt(0) : nombre}
          </span>
          {oficio && talla === 'cartel' && <span className="rotulo__oficio tenue">{oficio}</span>}
        </>
      )}
    </span>
  )
}
