'use client'

/**
 * La sesión en el navegador.
 *
 * Guardar el token en `localStorage` es lo que hace el 90 % de las aplicaciones y **no es lo
 * ideal**: es accesible desde JavaScript, así que un fallo de inyección de scripts se lleva la
 * sesión. La forma correcta es una cookie `HttpOnly` puesta por el servidor, y es a donde hay
 * que ir; queda anotado como deuda en el tablero.
 *
 * Se acepta hoy porque el acceso caduca en quince minutos y el refresco es revocable, así que
 * el daño está acotado en el tiempo. No porque esté bien.
 */

const CLAVE = 'agenda.sesion'

export type Sesion = {
  acceso: string
  refresco: string
  usuario_id: string
  negocio_activo: string | null
}

export function guardarSesion(sesion: Sesion): void {
  window.localStorage.setItem(CLAVE, JSON.stringify(sesion))
}

export function leerSesion(): Sesion | null {
  if (typeof window === 'undefined') return null
  const bruto = window.localStorage.getItem(CLAVE)
  if (!bruto) return null
  try {
    return JSON.parse(bruto) as Sesion
  } catch {
    // Un valor corrupto no puede dejar la aplicación inservible: se tira y se vuelve a entrar.
    window.localStorage.removeItem(CLAVE)
    return null
  }
}

export function borrarSesion(): void {
  window.localStorage.removeItem(CLAVE)
}

export const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

/** Llama a la API con el token puesto y traduce el sobre de error a algo que se pueda enseñar. */
export async function conSesion<T>(
  ruta: string,
  opciones: { metodo?: string; cuerpo?: unknown; token: string },
): Promise<T> {
  const respuesta = await fetch(`${API}${ruta}`, {
    method: opciones.metodo ?? 'GET',
    headers: {
      Authorization: `Bearer ${opciones.token}`,
      ...(opciones.cuerpo ? { 'Content-Type': 'application/json' } : {}),
    },
    body: opciones.cuerpo ? JSON.stringify(opciones.cuerpo) : undefined,
  })

  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => null)
    throw new Error(cuerpo?.error?.mensaje ?? 'No se pudo completar la operación.')
  }
  if (respuesta.status === 204) return undefined as T
  return (await respuesta.json()) as T
}
