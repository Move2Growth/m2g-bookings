/**
 * Los tres estados que casi nadie construye y que son la mitad del tiempo de uso real:
 * **cargando**, **vacío** y **error**.
 *
 * El estado bueno se ve una vez y ya. El de carga se ve en cada apertura con 3G, el vacío lo ve
 * todo salón el primer día y el de error lo ve cualquiera con mala cobertura. Si estos tres no
 * están dibujados, el producto se siente roto justo en los momentos en que más se mira.
 */

import Link from 'next/link'
import type { ReactNode } from 'react'

/**
 * Esqueleto de carga.
 *
 * Tiene **la forma de lo que va a llegar**, no es una ruedecita: así la página no salta cuando
 * entran los datos, que es lo que hace que algo parezca lento aunque tarde lo mismo.
 */
export function Esqueleto({
  filas = 3,
  alto = 76,
  etiqueta = 'Cargando',
}: {
  filas?: number
  alto?: number
  etiqueta?: string
}) {
  return (
    <div className="esqueleto" role="status" aria-live="polite">
      <span className="oculto-visualmente">{etiqueta}…</span>
      {Array.from({ length: filas }, (_, i) => (
        <div
          key={i}
          className="esqueleto__fila"
          style={{ height: alto, animationDelay: `${i * 90}ms` }}
          aria-hidden="true"
        />
      ))}
    </div>
  )
}

/**
 * Estado vacío.
 *
 * Dice **qué pasa y qué hacer ahora**, nunca «sin resultados» a secas. Un vacío sin salida es
 * un callejón, y en el primer día de un salón es todo lo que hay.
 */
export function Vacio({
  titulo,
  texto,
  accion,
  icono,
}: {
  titulo: string
  texto?: ReactNode
  accion?: { href: string; texto: string }
  icono?: ReactNode
}) {
  return (
    <div className="vacio">
      {icono && (
        <span className="vacio__icono" aria-hidden="true">
          {icono}
        </span>
      )}
      <p className="vacio__titulo">{titulo}</p>
      {texto && <p className="vacio__texto">{texto}</p>}
      {accion && (
        <Link href={accion.href} className="boton boton--primario">
          {accion.texto}
        </Link>
      )}
    </div>
  )
}

/**
 * Estado de error.
 *
 * Va en línea y con un botón de reintentar, no en un aviso flotante que desaparece solo: quien
 * pierde la cobertura a mitad de una pantalla tiene que poder volver a intentarlo sin recargar
 * y sin perder dónde estaba.
 */
export function Error({
  mensaje,
  reintentar,
}: {
  mensaje: string
  reintentar?: () => void
}) {
  return (
    <div role="alert" className="aviso aviso--error error-bloque">
      <p>{mensaje}</p>
      {reintentar && (
        <button type="button" onClick={reintentar} className="boton boton--secundario">
          Reintentar
        </button>
      )}
    </div>
  )
}
