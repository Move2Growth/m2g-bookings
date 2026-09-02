/**
 * El wordmark de Bukeo.
 *
 * Está dibujado a trazo, con las letras construidas como geometría y no como tipografía: así el
 * logotipo no depende de que una fuente cargue, se pinta con `currentColor` y funciona igual en
 * tinta sobre cal, en cal sobre tinta y sobre un bloque de color.
 *
 * Un solo archivo y ninguna versión invertida. Una versión invertida a mano es una versión que
 * alguien acaba usando en el sitio equivocado.
 */

export function Marca({ alto = 26 }: { alto?: number }) {
  return (
    <svg
      viewBox="0 0 304 96"
      height={alto}
      role="img"
      aria-label="Bukeo"
      fill="none"
      stroke="currentColor"
      strokeWidth={13}
      strokeLinecap="square"
      strokeLinejoin="miter"
      style={{ width: 'auto', display: 'block' }}
    >
      <path d="M20 16 V80" />
      <path d="M20 16 H36 A16 16 0 0 1 36 48 H20" />
      <path d="M20 48 H36 A16 16 0 0 1 36 80 H20" />
      <path d="M78 16 V64 A16 16 0 0 0 110 64 V16" />
      <path d="M136 16 V80" />
      <path d="M168 16 L136 48" />
      <path d="M136 48 L168 80" />
      <path d="M194 16 V80" />
      <path d="M194 16 H224" />
      <path d="M194 48 H218" />
      <path d="M194 80 H224" />
      <ellipse cx="264" cy="48" rx="20" ry="32" />
    </svg>
  )
}

/**
 * El símbolo para cuando no cabe el wordmark: favicon, avatar, sello. Es **el hueco**, que es
 * literalmente lo que vende el producto, la hora que sí está libre en una jornada llena. Va
 * calado con regla par-impar y no pintado del color del fondo, para que se sostenga sobre
 * cualquier cosa.
 */
export function Icono({ alto = 24 }: { alto?: number }) {
  return (
    <svg viewBox="0 0 24 24" height={alto} width={alto} role="img" aria-label="Bukeo" fill="none">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M2 2h20v20H2V2zm7 7h9v6H9V9z"
        fill="currentColor"
      />
    </svg>
  )
}
