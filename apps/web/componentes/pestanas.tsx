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
 * Están dibujados aquí y no vienen de una librería, y eso importa más de lo que parece: los que
 * había eran de una librería con el grosor cambiado, y **traían remates redondos** mientras el
 * logotipo de la marca se dibuja a escuadra. Un icono redondo al lado de un rótulo a escuadra se
 * nota aunque nadie sepa decir por qué.
 *
 * Tres reglas y ninguna más:
 *
 * · **Remate a escuadra y unión en ángulo vivo**, como el wordmark. Nada redondeado.
 * · **Trazo de 2 sobre caja de 24**, en coordenadas enteras. Así el dibujo cae en la rejilla de
 *   píxeles y no sale gris y borroso a tamaño pequeño, que es donde vive un icono de pestaña.
 * · **Rectilíneo salvo cuando la curva es el significado.** El corazón de guardar y la cabeza de
 *   una persona necesitan curva; una agenda, un servicio o una métrica, no.
 */
const trazo = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'square' as const,
  strokeLinejoin: 'miter' as const,
}

function Svg({ children }: { children: ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" {...trazo}>
      {children}
    </svg>
  )
}

export const Iconos = {
  /* La lupa es un cuadrado con mango: el círculo era el único redondeado de la familia. */
  buscar: (
    <Svg>
      <path d="M4 4h12v12H4z" />
      <path d="M16 16l4 4" />
    </Svg>
  ),
  /* La agenda es el bloque con la muesca del icono de marca, con la anilla arriba. */
  agenda: (
    <Svg>
      <path d="M3 6h18v15H3z" />
      <path d="M3 11h18" />
      <path d="M8 3v4M16 3v4" />
      <path d="M13 15h5v4h-5z" />
    </Svg>
  ),
  citas: (
    <Svg>
      <path d="M3 4h18v17H3z" />
      <path d="M12 9v4h4" />
    </Svg>
  ),
  corazon: (
    <Svg>
      <path d="M12 20 4 12.4A4.6 4.6 0 0 1 12 7.4a4.6 4.6 0 0 1 8 5z" />
    </Svg>
  ),
  persona: (
    <Svg>
      <path d="M8 4h8v6H8z" />
      <path d="M4 21v-4h16v4" />
    </Svg>
  ),
  equipo: (
    <Svg>
      <path d="M3 4h7v6H3z" />
      <path d="M14 4h7v6h-7z" />
      <path d="M3 21v-4h7v4M14 21v-4h7v4" />
    </Svg>
  ),
  /* La carta de servicios: renglones de distinta longitud, como una lista de precios. */
  servicios: (
    <Svg>
      <path d="M4 6h16M4 12h16M4 18h10" />
    </Svg>
  ),
  horario: (
    <Svg>
      <path d="M3 6h18v15H3z" />
      <path d="M3 11h18M9 11v10M15 11v10" />
    </Svg>
  ),
  clientes: (
    <Svg>
      <path d="M4 5h9v5H4z" />
      <path d="M3 21v-4h11v4" />
      <path d="M17 8l2 2 4-4" />
    </Svg>
  ),
  ficha: (
    <Svg>
      <path d="M3 4h18v17H3z" />
      <path d="M3 9h18" />
      <path d="M7 13h6M7 17h10" />
    </Svg>
  ),
  ajustes: (
    <Svg>
      <path d="M5 4v16M12 4v16M19 4v16" />
      <path d="M2 8h6M9 15h6M16 7h6" />
    </Svg>
  ),
  negocios: (
    <Svg>
      <path d="M3 21V8l9-5 9 5v13z" />
      <path d="M9 21v-7h6v7" />
    </Svg>
  ),
  /* La moderación es el hueco de la marca dentro de un escudo cuadrado. */
  moderacion: (
    <Svg>
      <path d="M4 4h16v9l-8 8-8-8z" />
      <path d="M12 8v4" />
      <path d="M12 15v1" />
    </Svg>
  ),
  metricas: (
    <Svg>
      <path d="M3 21h18" />
      <path d="M5 21V11h4v10M14 21V4h5v17" />
    </Svg>
  ),
} as const
