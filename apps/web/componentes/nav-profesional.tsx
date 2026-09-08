'use client';

/**
 * La navegación del profesional. **Dos sitios, no seis.**
 *
 * Esa es la diferencia con el portal del dueño, y es a propósito: un profesional entra a
 * trabajar —su día— y de vez en cuando a arreglar cómo lo ven. Ni dinero del salón, ni equipo,
 * ni publicidad. Si tuviera las mismas puertas y la mitad diera error, la zona sería una
 * promesa incumplida en vez de una herramienta.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const SITIOS = [
  ['/mi-agenda', 'Mi día'],
  ['/mi-ficha', 'Mi ficha'],
] as const;

export function NavProfesional() {
  const donde = usePathname();
  return (
    <nav className="nav-local" aria-label="Tu zona">
      <ul className="nav-local__carril">
        {SITIOS.map(([ruta, rotulo]) => (
          <li key={ruta}>
            <Link
              href={ruta}
              className="nav-local__sitio"
              data-elegida={donde === ruta ? 'si' : 'no'}
              aria-current={donde === ruta ? 'page' : undefined}
            >
              {rotulo}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
