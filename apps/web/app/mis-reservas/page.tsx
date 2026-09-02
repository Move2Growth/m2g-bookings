import { redirect } from 'next/navigation'

/**
 * La dirección vieja de las citas.
 *
 * Se queda como redirección permanente porque está en enlaces ya mandados por WhatsApp y en la
 * prueba de humo. Una URL publicada no se borra: se redirige.
 */
export default function MisReservas() {
  redirect('/mi/citas')
}
