/**
 * La marca. Vive aquí, en configuración, y **no se escribe a fuego en ninguna pantalla**: si
 * mañana cambia, se cambia este valor y los tokens, no el JSX de treinta componentes.
 */
export const NOMBRE = process.env.NEXT_PUBLIC_NOMBRE_COMERCIAL ?? 'Bukeo'

/** Lo que va detrás del nombre en el título del navegador y en las tarjetas al compartir. */
export const PROMESA = 'Reserva en salones y barberías de Panamá'
