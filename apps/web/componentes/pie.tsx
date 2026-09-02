import Link from 'next/link'
import { NOMBRE } from '@/lib/marca'
import { Marca } from './marca'

const ZONAS = [
  ['Bella Vista', 'bella-vista'],
  ['El Cangrejo', 'el-cangrejo'],
  ['Obarrio', 'obarrio'],
  ['San Francisco', 'san-francisco'],
  ['Costa del Este', 'costa-del-este'],
]

const CATEGORIAS = [
  ['Barbería', 'barberia'],
  ['Peluquería', 'peluqueria'],
  ['Uñas', 'unas'],
  ['Pestañas y cejas', 'pestanas-cejas'],
  ['Spa y masajes', 'spa-masajes'],
]

/**
 * El pie. Además de cerrar la página hace trabajo de verdad: son los enlaces internos que le
 * dicen a Google que existen las páginas de zona y de categoría, que es de donde llega media
 * clientela.
 */
export function Pie() {
  return (
    <footer style={{ borderTop: '1px solid var(--color-borde)', background: 'var(--color-lienzo)' }}>
      <div className="contenedor seccion">
        <div className="rejilla rejilla--3">
          <div>
            <Marca alto={20} />
            <p className="apagado" style={{ marginTop: 'var(--espacio-3)', maxWidth: '30ch' }}>
              La agenda de tu salón, gratis. Y el sitio donde tus clientas te encuentran.
            </p>
          </div>

          <nav aria-label="Zonas">
            <h2 className="tenue" style={{ fontFamily: 'inherit', fontWeight: 'inherit' }}>
              Por zona
            </h2>
            <ul style={{ marginTop: 'var(--espacio-2)', display: 'grid', gap: 'var(--espacio-1)' }}>
              {ZONAS.map(([nombre, slug]) => (
                <li key={slug}>
                  <Link href={`/buscar?zona=${slug}`}>{nombre}</Link>
                </li>
              ))}
            </ul>
          </nav>

          <nav aria-label="Categorías">
            <h2 className="tenue" style={{ fontFamily: 'inherit', fontWeight: 'inherit' }}>
              Por servicio
            </h2>
            <ul style={{ marginTop: 'var(--espacio-2)', display: 'grid', gap: 'var(--espacio-1)' }}>
              {CATEGORIAS.map(([nombre, slug]) => (
                <li key={slug}>
                  <Link href={`/buscar?categoria=${slug}`}>{nombre}</Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>

        <div
          style={{
            marginTop: 'var(--espacio-6)',
            paddingTop: 'var(--espacio-4)',
            borderTop: '1px solid var(--color-borde)',
            display: 'flex',
            flexWrap: 'wrap',
            gap: 'var(--espacio-4)',
            justifyContent: 'space-between',
          }}
        >
          <p className="tenue">
            {NOMBRE}, Ciudad de Panamá. Precios en dólares.
          </p>
          <nav aria-label="Legal" style={{ display: 'flex', gap: 'var(--espacio-4)' }}>
            <Link href="/como-funciona" className="tenue">
              Cómo funciona
            </Link>
            <Link href="/legal/privacidad" className="tenue">
              Privacidad
            </Link>
            <Link href="/legal/terminos" className="tenue">
              Términos
            </Link>
            <Link href="/para-negocios" className="tenue">
              Para salones
            </Link>
          </nav>
        </div>
      </div>
    </footer>
  )
}
