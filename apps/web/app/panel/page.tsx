import { redirect } from 'next/navigation'

/** El panel abre por la agenda: es la pantalla que se mira cuarenta veces al día. */
export default function Panel() {
  redirect('/panel/agenda')
}
