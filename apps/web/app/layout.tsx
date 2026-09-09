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

const PROMESA =
  'Reservas de barbería, salón, uñas, cejas y spa en la ciudad de Panamá. Elige a quién quieres que te atienda y a qué hora.';

export const metadata: Metadata = {
  /**
   * `metadataBase` no es un adorno: sin ella, Next resuelve las direcciones de `openGraph` como
   * relativas y **lo que se comparte por WhatsApp llega sin tarjeta**. Aquí se entra por el
   * enlace que el salón pega en su bio de Instagram, así que la tarjeta es la portada del
   * producto para media ciudad.
   */
  metadataBase: new URL(process.env.NEXT_PUBLIC_URL_PUBLICA ?? 'http://localhost:3100'),
  title: {
    default: `${NOMBRE_COMERCIAL} · reserva tu turno en Panamá`,
    template: `%s · ${NOMBRE_COMERCIAL}`,
  },
  description: PROMESA,
  applicationName: NOMBRE_COMERCIAL,
  openGraph: {
    type: 'website',
    locale: 'es_PA',
    siteName: NOMBRE_COMERCIAL,
    title: `${NOMBRE_COMERCIAL} · reserva tu turno en Panamá`,
    description: PROMESA,
  },
  twitter: { card: 'summary_large_image', title: NOMBRE_COMERCIAL, description: PROMESA },
  // El icono se dibuja en `icon.svg`, con la misma geometría que el sello de la marca.
  icons: { icon: '/icon.svg' },
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
