import Link from 'next/link'
import { NOMBRE } from '@/lib/marca'
import { Marca } from './marca'

/**
 * La cabecera. Una sola línea en escritorio y como mucho cuatro destinos: cada enlace de más
 * es una decisión que le pasamos a quien llega, y quien llega solo quiere dos cosas, buscar un
 * salón o entrar a su agenda.
 */
export function Cabecera({ variante = 'clara' }: { variante?: 'clara' | 'transparente' }) {
  return (
    <header
      style={{
        borderBottom: variante === 'clara' ? '1px solid var(--color-borde)' : 'none',
        background: variante === 'clara' ? 'var(--color-lienzo)' : 'transparent',
      }}
    >
      <div
        className="contenedor"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--espacio-4)',
          minHeight: '68px',
        }}
      >
        <Link href="/" aria-label={`${NOMBRE}, inicio`} style={{ display: 'flex' }}>
          <Marca alto={22} />
        </Link>

        <nav
          aria-label="Principal"
          style={{ display: 'flex', alignItems: 'center', gap: 'var(--espacio-2)' }}
        >
          <Link href="/buscar" className="boton boton--llano">
            Buscar
          </Link>
          <Link href="/como-funciona" className="boton boton--llano oculto-en-movil">
            Cómo funciona
          </Link>
          <Link href="/para-negocios" className="boton boton--llano oculto-en-movil">
            Para salones
          </Link>
          <Link href="/entrar" className="boton boton--secundario">
            Entrar
          </Link>
        </nav>
      </div>
    </header>
  )
}
