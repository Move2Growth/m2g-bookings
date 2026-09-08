import { Suspense } from 'react';

import { Entrada } from '@/componentes/entrada';

export const metadata = { title: 'Entrar' };

/**
 * Entrar.
 *
 * Correo y contraseña, que es lo que decidió el encargo del 7 de septiembre: el código por
 * WhatsApp se retiró y el segundo factor y los botones de Google o Apple quedaron para más
 * adelante. Aquí no se enseña lo que todavía no existe.
 */
export default function PantallaDeEntrada() {
  return (
    <Suspense fallback={null}>
      <Entrada />
    </Suspense>
  );
}
