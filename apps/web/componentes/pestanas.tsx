'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { ReactNode } from 'react'

/**
 * La navegación por pestañas de las zonas con sesión.
 *
 * Es **una sola pieza con dos formas**, no dos componentes: en el teléfono es una barra
 * inferior fija, porque el pulgar llega abajo y no arriba; en escritorio es una fila bajo la
 * cabecera. Tener dos componentes acaba con dos listas de pestañas que se desincronizan, y eso
 * se nota el día que alguien añade una y solo aparece en un sitio.
 *
 * La pestaña activa se decide por la URL y no por estado del componente: así una recarga, un
 * enlace compartido y el botón de atrás del navegador coinciden siempre.
 */

export type Pestana = {
  href: string
  texto: string
  icono: ReactNode
  /** Cuenta que se pinta encima del icono. `0` no se pinta: un cero no es una novedad. */
  cuenta?: number
}

export function Pestanas({ pestanas, etiqueta }: { pestanas: Pestana[]; etiqueta: string }) {
  const ruta = usePathname()

  return (
    <nav className="pestanas" aria-label={etiqueta}>
      <ul className="pestanas__lista">
        {pestanas.map((p) => {
          // Coincidencia por prefijo para que /panel/servicios/nuevo siga marcando «Servicios».
          // La raíz se compara exacta o marcaría todas.
          const activa = ruta === p.href || (p.href !== '/' && ruta.startsWith(`${p.href}/`))
          return (
            <li key={p.href}>
              <Link
                href={p.href}
                className="pestana"
                aria-current={activa ? 'page' : undefined}
              >
                <span className="pestana__icono" aria-hidden="true">
                  {p.icono}
                  {p.cuenta ? <span className="pestana__cuenta">{p.cuenta > 9 ? '9+' : p.cuenta}</span> : null}
                </span>
                <span className="pestana__texto">{p.texto}</span>
              </Link>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

/**
 * Los iconos.
 *
 * Están dibujados aquí y no vienen de una librería porque son ocho, se usan a un solo tamaño y
 * una dependencia de iconos entera pesa más que estas líneas. Todos comparten trazo de 1,75 y
 * caja de 24, que es lo que hace que una fila de iconos se lea como una familia y no como un
 * muestrario.
 */
const trazo = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.75,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

function Svg({ children }: { children: ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" {...trazo}>
      {children}
    </svg>
  )
}

export const Iconos = {
  buscar: (
    <Svg>
      <circle cx="11" cy="11" r="7" />
      <path d="M16.5 16.5 21 21" />
    </Svg>
  ),
  agenda: (
    <Svg>
      <rect x="3" y="5" width="18" height="16" rx="1" />
      <path d="M3 10h18M8 3v4M16 3v4" />
    </Svg>
  ),
  citas: (
    <Svg>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3.5 2" />
    </Svg>
  ),
  corazon: (
    <Svg>
      <path d="M12 20s-7.5-4.6-7.5-9.6A4.4 4.4 0 0 1 12 7.6a4.4 4.4 0 0 1 7.5 2.8C19.5 15.4 12 20 12 20Z" />
    </Svg>
  ),
  persona: (
    <Svg>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M4.5 20c1.2-3.6 4-5.4 7.5-5.4s6.3 1.8 7.5 5.4" />
    </Svg>
  ),
  equipo: (
    <Svg>
      <circle cx="9" cy="8" r="3.2" />
      <path d="M2.5 19.5c1-3.1 3.4-4.7 6.5-4.7s5.5 1.6 6.5 4.7" />
      <path d="M16.5 5.4a3.2 3.2 0 0 1 0 5.2M18 14.9c2.1.5 3.3 1.9 4 4.6" />
    </Svg>
  ),
  servicios: (
    <Svg>
      <path d="M4 7h16M4 12h16M4 17h10" />
    </Svg>
  ),
  horario: (
    <Svg>
      <rect x="3" y="5" width="18" height="16" rx="1" />
      <path d="M3 10h18" />
      <path d="M8 14h3M8 17.5h6" />
    </Svg>
  ),
  clientes: (
    <Svg>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M4.5 20c1.2-3.6 4-5.4 7.5-5.4s6.3 1.8 7.5 5.4" />
      <path d="M17.5 3.5 19 5l3-3" />
    </Svg>
  ),
  ficha: (
    <Svg>
      <rect x="3" y="4" width="18" height="17" rx="1" />
      <path d="M3 9h18M7 13h5M7 16.5h9" />
    </Svg>
  ),
  ajustes: (
    <Svg>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2.8v2.4M12 18.8v2.4M4.5 4.5l1.7 1.7M17.8 17.8l1.7 1.7M2.8 12h2.4M18.8 12h2.4M4.5 19.5l1.7-1.7M17.8 6.2l1.7-1.7" />
    </Svg>
  ),
  negocios: (
    <Svg>
      <path d="M3 21V9l9-6 9 6v12" />
      <path d="M9 21v-6h6v6" />
    </Svg>
  ),
  moderacion: (
    <Svg>
      <path d="M12 3 4 6v6c0 4.4 3.2 8 8 9 4.8-1 8-4.6 8-9V6l-8-3Z" />
      <path d="M12 9v4M12 16.2v.1" />
    </Svg>
  ),
  metricas: (
    <Svg>
      <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
    </Svg>
  ),
} as const
