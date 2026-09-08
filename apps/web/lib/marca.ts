/**
 * La marca. Vive aquí, en configuración, y **no se escribe a fuego en ninguna pantalla**: si
 * mañana cambia, se cambia este valor y los tokens, no el JSX de treinta componentes.
 */
export const NOMBRE = process.env.NEXT_PUBLIC_NOMBRE_COMERCIAL ?? 'Tanda'

/**
 * El sitio donde vive la web, tal y como se lo enseñamos a un salón para que lo copie en su bio
 * de Instagram. Sale de configuración por lo mismo que el nombre: el dominio está sin decidir
 * (D1). Estaba escrito a fuego como `bukeo.com`, que **no existe**, así que el panel llevaba
 * meses ofreciendo un enlace muerto para pegar en Instagram.
 */
export const DOMINIO = (process.env.NEXT_PUBLIC_URL_PUBLICA ?? 'http://localhost:3100').replace(
  /\/+$/,
  '',
)

/** El dominio sin el `https://` delante, que es como se lee y como se dicta por teléfono. */
export const DOMINIO_VISIBLE = DOMINIO.replace(/^https?:\/\//, '')

/** Lo que va detrás del nombre en el título del navegador y en las tarjetas al compartir. */
export const PROMESA = 'Reserva en salones y barberías de Panamá'
