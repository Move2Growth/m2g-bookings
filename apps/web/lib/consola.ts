'use client';

/**
 * La sesión de la consola interna de M2G.
 *
 * **No comparte nada con la de la clienta, y es deliberado.** Vive en otra llave del navegador,
 * la escribe otro sistema de acceso —otras tablas, otro rol de base de datos, segundo factor
 * obligatorio— y caduca antes. Si un superadministrador fuera una casilla marcada en la cuenta
 * de una clienta, cualquier fallo de escalada en la aplicación pública sería una escalada al
 * back-office de toda la plataforma.
 *
 * Va en `sessionStorage` y no en `localStorage`: la consola se cierra al cerrar la pestaña. Una
 * sesión de back-office que sobrevive a apagar el portátil es una sesión que alguien encuentra
 * abierta.
 */

import { pedir } from './api';

const LLAVE = 'agenda.consola';

export type SesionDeConsola = { acceso: string; refresco: string };

export function leerConsola(): SesionDeConsola | null {
  if (typeof window === 'undefined') return null;
  const crudo = window.sessionStorage.getItem(LLAVE);
  if (!crudo) return null;
  try {
    return JSON.parse(crudo) as SesionDeConsola;
  } catch {
    return null;
  }
}

export function guardarConsola(sesion: SesionDeConsola): void {
  window.sessionStorage.setItem(LLAVE, JSON.stringify(sesion));
}

export function salirDeConsola(): void {
  window.sessionStorage.removeItem(LLAVE);
}

/** Como `conSesion`, pero de la consola: si el acceso caduca, se vuelve a entrar. Sin bucles. */
export async function conConsola<T>(llamada: (acceso: string) => Promise<T>): Promise<T> {
  const sesion = leerConsola();
  if (!sesion) throw new Error('SIN_CONSOLA');
  try {
    return await llamada(sesion.acceso);
  } catch (error) {
    const estado = (error as { estado?: number }).estado;
    if (estado !== 401) throw error;
    try {
      const renovada = await pedir<SesionDeConsola>('/api/v1/consola/refrescar', {
        metodo: 'POST',
        cuerpo: { refresco: sesion.refresco },
      });
      guardarConsola(renovada);
      return await llamada(renovada.acceso);
    } catch {
      salirDeConsola();
      throw error;
    }
  }
}
