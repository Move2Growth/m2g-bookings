'use client';

/**
 * La navegación del portal del dueño.
 *
 * Existe para que el portal **se distinga del panel de un profesional**, que es lo que pidió el
 * encargo: un profesional entra y ve su agenda y nada más; el dueño entra y tiene seis sitios a
 * los que ir. Si las dos zonas se vieran igual, la única diferencia sería lo que falta, y eso no
 * se ve.
 *
 * Es un carril que se arrastra a 390 px y una fila normal en cuanto cabe. No se esconde en un
 * menú: un menú de tres puntos en la herramienta que se usa doce veces al día es un clic de más
 * doce veces al día.
 */

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const SITIOS = [
  ['/local', 'La agenda'],
  ['/local/equipo', 'El equipo'],
  ['/local/horario', 'Horario'],
  ['/local/finanzas', 'El dinero'],
  ['/local/mejor-del-mes', 'Mejor del mes'],
  ['/local/publicidad', 'Publicidad'],
] as const;

export function NavLocal() {
  const donde = usePathname();
  return (
    <nav className="nav-local" aria-label="Zonas del salón">
      <ul className="nav-local__carril">
        {SITIOS.map(([ruta, rotulo]) => {
          const aqui = donde === ruta;
          return (
            <li key={ruta}>
              <Link
                href={ruta}
                className="nav-local__sitio"
                data-elegida={aqui ? 'si' : 'no'}
                aria-current={aqui ? 'page' : undefined}
              >
                {rotulo}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
