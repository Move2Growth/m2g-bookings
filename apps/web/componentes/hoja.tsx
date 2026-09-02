'use client'

import { useEffect, useRef, type ReactNode } from 'react'

/**
 * La hoja que sube desde abajo.
 *
 * Es el contenedor de todo lo que es **un ajuste y no un viaje**: editar un servicio, poner un
 * filtro, confirmar algo. Al cerrarla se vuelve exactamente a la pantalla de antes, con el
 * mismo desplazamiento, que es justo lo que no pasa cuando eso mismo se hace con otra página.
 *
 * Hace tres cosas que se olvidan siempre y que son la diferencia entre una hoja y un div
 * flotante: **atrapa el foco** mientras está abierta, **cierra con Escape** y **bloquea el
 * desplazamiento de la página de detrás**. Sin lo primero, quien navega con teclado se sale de
 * la hoja sin darse cuenta y sigue tabulando por una página que no puede ver.
 */
export function Hoja({
  titulo,
  onCerrar,
  children,
}: {
  titulo: string
  onCerrar: () => void
  children: ReactNode
}) {
  const caja = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const antes = document.activeElement as HTMLElement | null
    const alPulsar = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCerrar()
        return
      }
      if (e.key !== 'Tab' || !caja.current) return
      const focos = caja.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )
      if (focos.length === 0) return
      const primero = focos[0]
      const ultimo = focos[focos.length - 1]
      if (e.shiftKey && document.activeElement === primero) {
        e.preventDefault()
        ultimo.focus()
      } else if (!e.shiftKey && document.activeElement === ultimo) {
        e.preventDefault()
        primero.focus()
      }
    }

    document.addEventListener('keydown', alPulsar)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', alPulsar)
      document.body.style.overflow = ''
      // Devolver el foco a donde estaba: si no, quien cierra con teclado vuelve al principio
      // de la página y tiene que recorrer la lista entera otra vez.
      antes?.focus?.()
    }
  }, [onCerrar])

  return (
    <>
      <div className="hoja-fondo" onClick={onCerrar} aria-hidden="true" />
      <div className="hoja" role="dialog" aria-modal="true" aria-label={titulo} ref={caja}>
        <div className="hoja__cabeza">
          <h2 style={{ fontSize: 'var(--tipografia-tamano-titulo-4)' }}>{titulo}</h2>
          <button type="button" className="boton boton--llano" onClick={onCerrar}>
            Cerrar
          </button>
        </div>
        {children}
      </div>
    </>
  )
}
