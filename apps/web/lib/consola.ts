/**
 * La sesión de la consola interna de M2G.
 *
 * Vive **separada de la sesión de clientes** y con otra clave de almacenamiento, y eso no es
 * pulcritud: son dos identidades distintas contra dos roles distintos de la base de datos. Si
 * compartieran sitio, entrar en la consola sacaría a alguien de su cuenta de clienta, y peor,
 * un descuido al leer la clave equivocada mandaría un token de cliente a la consola.
 *
 * Se guarda en `sessionStorage` y no en `localStorage` a propósito: la sesión de administración
 * **muere al cerrar la pestaña**. Es la superficie con más poder del producto y no tiene por
 * qué sobrevivir a un ordenador que alguien deja abierto.
 */

const CLAVE = 'agenda.consola'

export const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export type SesionDeConsola = {
  acceso: string
  refresco: string
  expira_en_segundos: number
  admin_id: string
  rol: string
  nombre: string
}

export function guardarSesionDeConsola(sesion: SesionDeConsola): void {
  window.sessionStorage.setItem(CLAVE, JSON.stringify(sesion))
}

export function leerSesionDeConsola(): SesionDeConsola | null {
  if (typeof window === 'undefined') return null
  const bruto = window.sessionStorage.getItem(CLAVE)
  if (!bruto) return null
  try {
    return JSON.parse(bruto) as SesionDeConsola
  } catch {
    window.sessionStorage.removeItem(CLAVE)
    return null
  }
}

export function borrarSesionDeConsola(): void {
  window.sessionStorage.removeItem(CLAVE)
}

export async function conConsola<T>(
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
