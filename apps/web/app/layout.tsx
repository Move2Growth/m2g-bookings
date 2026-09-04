import type { Metadata, Viewport } from 'next'
// Archivo variable con el eje de anchura: una sola familia hace de rótulo, de texto y de cifra
// cambiando de ancho, y baja un solo archivo. Autoalojada, nunca enlazada a un tercero: sería
// una dependencia ajena, un problema de política de contenido y una petición más en 3G.
import '@fontsource-variable/big-shoulders-display/wght'
import '@fontsource-variable/chivo/wght'
import './globales.css'
import { NOMBRE, PROMESA } from '@/lib/marca'

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
  themeColor: '#0E0A11',
}

export default function Raiz({ children }: { children: React.ReactNode }) {
  // Modo claro por defecto. El oscuro ya tiene sus tokens y se enciende cambiando este
  // atributo, no rediseñando.
  return (
    <html lang="es-PA" data-tema="oscuro">
      <body>{children}</body>
    </html>
  )
}
