import type { Metadata, Viewport } from 'next'
// Las dos familias de la dirección Tanda, **variables y autoalojadas**: cada una baja un solo
// archivo con todo su eje de peso, y ninguna se enlaza a un tercero — sería una dependencia
// ajena, un problema de política de contenido y una petición más en 3G.
import '@fontsource-variable/familjen-grotesk/wght'
import '@fontsource-variable/public-sans/wght'
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
    <html lang="es-PA">
      <body>{children}</body>
    </html>
  )
}
