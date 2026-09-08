'use client';

/**
 * La sesión del navegador.
 *
 * Vive en `localStorage` porque en local no hay dominio ni cookie de sesión que valga, y
 * porque el crítico tiene que poder recargar la página sin volver a entrar. El acceso caduca a
 * los 900 segundos: cuando la API contesta 401 se rota el refresco una vez y se repite la
 * llamada; si el refresco tampoco vale, se cierra la sesión y se manda a entrar.
 */

import { api, Credenciales, FalloDeApi, pedir } from './api';

const LLAVE = 'agenda.sesion';

export type Sesion = {
  acceso: string;
  refresco: string;
  usuarioId: string;
  negocioActivo: string | null;
};

const oyentes = new Set<() => void>();

export function leerSesion(): Sesion | null {
  if (typeof window === 'undefined') return null;
  const crudo = window.localStorage.getItem(LLAVE);
  if (!crudo) return null;
  try {
    return JSON.parse(crudo) as Sesion;
  } catch {
    return null;
  }
}

export function guardarSesion(credenciales: Credenciales): Sesion {
  const sesion: Sesion = {
    acceso: credenciales.acceso,
    refresco: credenciales.refresco,
    usuarioId: credenciales.usuario_id,
    negocioActivo: credenciales.negocio_activo ?? null,
  };
  window.localStorage.setItem(LLAVE, JSON.stringify(sesion));
  oyentes.forEach((avisar) => avisar());
  return sesion;
}

export function borrarSesion(): void {
  window.localStorage.removeItem(LLAVE);
  oyentes.forEach((avisar) => avisar());
}

export function alCambiarLaSesion(avisar: () => void): () => void {
  oyentes.add(avisar);
  window.addEventListener('storage', avisar);
  return () => {
    oyentes.delete(avisar);
    window.removeEventListener('storage', avisar);
  };
}

/**
 * Llama a la API con la sesión puesta y, si el acceso caducó, lo renueva una sola vez.
 * Una sola vez a propósito: si el refresco tampoco vale, insistir es un bucle.
 */
export async function conSesion<T>(llamada: (acceso: string) => Promise<T>): Promise<T> {
  const sesion = leerSesion();
  if (!sesion) throw new FalloDeApi({ codigo: 'SIN_SESION', mensaje: 'Hay que entrar primero.', estado: 401 });

  try {
    return await llamada(sesion.acceso);
  } catch (error) {
    if (!(error instanceof FalloDeApi) || error.estado !== 401) throw error;

    let renovadas: Credenciales;
    try {
      renovadas = await pedir<Credenciales>('/api/v1/auth/refrescar', {
        metodo: 'POST',
        cuerpo: { refresco: sesion.refresco },
      });
    } catch {
      borrarSesion();
      throw new FalloDeApi({ codigo: 'SESION_CADUCADA', mensaje: 'Se cerró la sesión. Vuelve a entrar.', estado: 401 });
    }

    // El refresco devuelve un acceso sin negocio: si estábamos en modo salón, hay que volver.
    const nueva = guardarSesion({ ...renovadas, negocio_activo: renovadas.negocio_activo ?? sesion.negocioActivo });
    if (sesion.negocioActivo && !renovadas.negocio_activo) {
      const enModo = await api.modoNegocio(sesion.negocioActivo, nueva.acceso);
      guardarSesion(enModo);
      return llamada(enModo.acceso);
    }
    return llamada(nueva.acceso);
  }
}
