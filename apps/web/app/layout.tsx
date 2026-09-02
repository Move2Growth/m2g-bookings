import type { Metadata, Viewport } from 'next'
import { GeistSans } from 'geist/font/sans'
import '@fontsource-variable/outfit'
import './globales.css'
import { NOMBRE, PROMESA } from '@/lib/marca'

/**
 * Las dos familias van **autoalojadas**: Geist como paquete de npm con su propia clase, Outfit
 * desde Fontsource. Enlazar a Google Fonts sería una dependencia de un tercero, un problema de
 * CSP y una petición más en una red de 3G, que es donde vive este producto.
 */

export const metadata: Metadata = {
  title: { default: `${NOMBRE} · ${PROMESA}`, template: `%s · ${NOMBRE}` },
  description:
    'Encuentra barberías, salones y spas cerca de ti en Panamá y reserva tu cita en un minuto. Y si tienes un salón, tu agenda es gratis.',
  metadataBase: new URL(process.env.NEXT_PUBLIC_URL_PUBLICA ?? 'http://localhost:3000'),
  openGraph: { type: 'website', locale: 'es_PA', siteName: NOMBRE },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  // Sin `maximum-scale`: impedir el zoom es una barrera de accesibilidad, y esto se lee en un
  // teléfono, muchas veces con mala luz.
  themeColor: '#F7F6F4',
}

export default function Raiz({ children }: { children: React.ReactNode }) {
  // Modo claro por defecto. El oscuro ya tiene sus tokens y se enciende cambiando este
  // atributo, no rediseñando.
  return (
    <html lang="es-PA" data-tema="claro" className={GeistSans.className}>
      <body>{children}</body>
    </html>
  )
}
