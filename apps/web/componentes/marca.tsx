/**
 * El wordmark de Bukeo y su ícono.
 *
 * El símbolo es **el hueco**: un bloque sólido con una muesca abierta. Es literalmente lo que
 * vende el producto, la hora que sí está libre, y funciona a 16 px porque son dos formas
 * geométricas y nada más.
 *
 * Se dibuja con `currentColor` para que herede el color del contexto: sobre papel es tinta,
 * sobre una sección oscura es papel, y no hacen falta tres archivos de logo.
 */

export function Icono({ alto = 24 }: { alto?: number }) {
  return (
    <svg
      viewBox="0 0 24 24"
      height={alto}
      width={alto}
      role="img"
      aria-label="Bukeo"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Un solo trazado con regla par-impar: el hueco queda **calado**, no pintado del color
          del fondo. Es lo que hace que el símbolo funcione igual sobre papel, sobre tinta y
          sobre una foto, con un solo archivo y sin versiones invertidas. */}
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M2 2h20v20H2V2zm7 7h9v6H9V9z"
        fill="currentColor"
      />
    </svg>
  )
}

export function Marca({ alto = 22 }: { alto?: number }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.45em',
        // Hereda el color del contexto: sobre papel es tinta y sobre una sección oscura es
        // papel, sin necesidad de un segundo logotipo.
        color: 'currentColor',
      }}
    >
      <Icono alto={alto} />
      <span
        style={{
          fontFamily: 'var(--tipografia-familia-display)',
          fontWeight: 'var(--tipografia-pesos-display)',
          fontSize: `${alto * 0.95}px`,
          letterSpacing: '-0.03em',
          lineHeight: 1,
        }}
      >
        bukeo
      </span>
    </span>
  )
}
