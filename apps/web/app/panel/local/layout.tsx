'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { ReactNode } from 'react'

/**
 * El portal del dueño.
 *
 * Luis lo pidió con estas palabras: «el portal del dueño, que eso hay que diferenciarlo de
 * alguna manera». La diferencia **no puede ser el color** —la dirección visual está en revisión y
 * se sustituye entera—, así que es estructural y sobrevive al cambio de estilo:
 *
 * · Es **una zona propia con su nombre**, no seis pestañas más sueltas en la misma barra. Quien
 *   entra aquí lee «Portal del local» antes que nada.
 * · Tiene **su propia navegación**, con las seis piezas que son suyas y de nadie más: los
 *   calendarios de todo el equipo, la caja, el ranking del mes, la publicidad, el fichaje y las
 *   personas del local.
 * · Un profesional **nunca la ve**, y no por esconderle un enlace: `/panel/layout.tsx` lo manda a
 *   su agenda, y debajo la API le cierra estos endpoints con `exigir_dueno` y con las políticas
 *   de fila de PostgreSQL. Aquí no hay ni un permiso decidido en el navegador.
 */

const SECCIONES = [
  { href: '/panel/local', texto: 'Hoy' },
  { href: '/panel/local/calendarios', texto: 'Calendarios' },
  { href: '/panel/local/finanzas', texto: 'Finanzas' },
  { href: '/panel/local/mejor-del-mes', texto: 'Mejor del mes' },
  { href: '/panel/local/publicidad', texto: 'Publicidad' },
  { href: '/panel/local/fichaje', texto: 'Fichaje' },
  { href: '/panel/local/personas', texto: 'Personas' },
]

export default function DisposicionDelPortal({ children }: { children: ReactNode }) {
  const ruta = usePathname()

  return (
    <>
      <div className="contenedor">
        <p className="etiqueta">Portal del local</p>
        {/* La navegación de la zona se desplaza a lo ancho dentro de su carril: en un teléfono
            no caben siete destinos en una línea, y envolverlos en tres filas empuja el contenido
            de la pantalla fuera de la vista antes de haber leído nada. */}
        <nav className="tira" aria-label="Secciones del portal del local">
          {SECCIONES.map((s) => {
            // «Hoy» se compara exacta o se marcaría en las seis pantallas de dentro.
            const activa =
              s.href === '/panel/local' ? ruta === s.href : ruta.startsWith(s.href)
            return (
              <Link
                key={s.href}
                href={s.href}
                className="ficha"
                aria-current={activa ? 'page' : undefined}
              >
                {s.texto}
              </Link>
            )
          })}
        </nav>
      </div>
      {children}
    </>
  )
}
