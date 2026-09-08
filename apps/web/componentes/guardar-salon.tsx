'use client';

/**
 * Guardar un salón, desde su ficha.
 *
 * Es una isla de cliente dentro de una página que se pinta en el servidor: la ficha tiene que
 * seguir llegando entera en el HTML —es la página que este producto existe para que Google
 * indexe— y guardar necesita sesión, que es cosa del navegador.
 *
 * Sin sesión no se esconde el botón: se ofrece y lleva a entrar, volviendo aquí. Esconder lo que
 * hay que estar dentro para hacer es la forma más rápida de que nadie sepa que existe.
 */

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Boton } from '@/componentes/boton';
import { api, comoMensaje } from '@/lib/api';
import { conSesion, leerSesion } from '@/lib/sesion';

export function GuardarSalon({ negocioId, slug }: { negocioId: string; slug: string }) {
  const router = useRouter();
  const [guardado, setGuardado] = useState<boolean | null>(null);
  const [tocando, setTocando] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);

  useEffect(() => {
    if (!leerSesion()) {
      setGuardado(null);
      return;
    }
    conSesion((acceso) => api.favoritos(acceso))
      .then((lista) => setGuardado(lista.some((f) => f.negocio_id === negocioId)))
      .catch(() => setGuardado(null));
  }, [negocioId]);

  async function cambiar() {
    if (!leerSesion()) {
      router.push(`/entrar?volver=${encodeURIComponent(`/salon/${slug}`)}`);
      return;
    }
    setTocando(true);
    setFallo(null);
    try {
      if (guardado) {
        await conSesion((acceso) => api.quitarFavorito(negocioId, acceso));
        setGuardado(false);
      } else {
        await conSesion((acceso) => api.guardarFavorito(negocioId, acceso));
        setGuardado(true);
      }
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setTocando(false);
    }
  }

  return (
    <>
      <Boton
        tono={guardado ? 'secundario' : 'abre'}
        onClick={() => void cambiar()}
        cargando={tocando}
        rotuloCargando="Guardando"
        aria-pressed={guardado === true}
        hijos={guardado ? 'Guardado' : 'Guardar este salón'}
      />
      {fallo ? (
        <p className="campo__fallo" role="alert">
          {fallo}
        </p>
      ) : null}
    </>
  );
}
