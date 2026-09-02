import type { Metadata, Viewport } from 'next'
import './globales.css'
import { NOMBRE } from '@/lib/marca'


export const metadata: Metadata = {
  title: {
    default: `${NOMBRE} · Reserva en salones y barberías de Panamá`,
    template: `%s · ${NOMBRE}`,
  },
  description:
    'Encuentra barberías, salones y spas cerca de ti en Panamá y reserva tu cita en un minuto.',
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  // Sin `maximum-scale`: impedir el zoom es una barrera de accesibilidad, y aquí se lee en
  // un teléfono, muchas veces con mala luz.
  themeColor: '#FFFFFF',
}

export default function Raiz({ children }: { children: React.ReactNode }) {
  // `data-tema` sale en claro por defecto (ADR-0013). El oscuro ya tiene sus tokens definidos
  // y se enciende cambiando este atributo, no rediseñando.
  return (
    <html lang="es-PA" data-tema="claro">
      <body>{children}</body>
    </html>
  )
}
