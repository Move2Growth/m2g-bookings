import Image from 'next/image'

/**
 * Una foto de salón, venga de donde venga.
 *
 * Hay dos orígenes y no se tratan igual:
 *
 * · **Rutas nuestras** (`/fotos/spa.webp`): pasan por `next/image`, que las sirve en el tamaño
 *   que hace falta y en formato moderno. Es lo que hace que la portada no baje 400 KB en 3G.
 * · **Direcciones de fuera**, que es lo que pega un salón con sus fotos en otro sitio: van en
 *   una etiqueta normal con carga diferida. **A propósito no se optimizan**: hacerlo obligaría
 *   a que nuestro servidor descargue una URL que ha escrito cualquiera, y eso es un servidor
 *   pidiendo cosas por ti a donde le digan.
 *
 * El texto alternativo va vacío cuando la foto acompaña a un nombre que ya está escrito al
 * lado: repetirlo es ruido para quien usa un lector de pantalla.
 */
export function FotoDeSalon({
  src,
  alt = '',
  ancho,
  alto,
  sizes,
  prioridad,
  className,
}: {
  src: string
  alt?: string
  ancho: number
  alto: number
  sizes?: string
  prioridad?: boolean
  className?: string
}) {
  const esNuestra = src.startsWith('/')

  if (esNuestra) {
    return (
      <Image
        src={src}
        alt={alt}
        width={ancho}
        height={alto}
        sizes={sizes}
        priority={prioridad}
        className={className}
      />
    )
  }

  // eslint-disable-next-line @next/next/no-img-element
  return (
    <img
      src={src}
      alt={alt}
      width={ancho}
      height={alto}
      loading={prioridad ? 'eager' : 'lazy'}
      decoding="async"
      referrerPolicy="no-referrer"
      className={className}
    />
  )
}
