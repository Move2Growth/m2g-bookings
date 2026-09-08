import type { Metadata, Viewport } from 'next';

import { Cabecera } from '@/componentes/cabecera';
import { Pie } from '@/componentes/pie';
import { NOMBRE_COMERCIAL } from '@/lib/marca';
import './globales.css';

/**
 * El armazón de TODAS las pantallas.
 *
 * La cabecera y el pie se ponen aquí y no en cada página a propósito: así no existe la
 * posibilidad de entregar una pantalla a medias. Lo único que cambia por ruta es lo de dentro.
 */

export const metadata: Metadata = {
  title: {
    default: `${NOMBRE_COMERCIAL} · reserva tu turno en Panamá`,
    template: `%s · ${NOMBRE_COMERCIAL}`,
  },
  description:
    'Reservas de barbería, salón, uñas, cejas y spa en la ciudad de Panamá. Elige a quién quieres que te atienda y a qué hora.',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  // El producto abre en claro (ADR-0022). El oscuro está definido y sin encender.
  colorScheme: 'light',
};

export default function ArmazonRaiz({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-PA">
      <body>
        <div className="pagina">
          <a className="saltar" href="#contenido">
            Saltar al contenido
          </a>
          <Cabecera />
          <main id="contenido">{children}</main>
          <Pie />
        </div>
      </body>
    </html>
  );
}
