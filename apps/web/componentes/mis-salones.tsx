'use client';

/**
 * Los salones guardados.
 *
 * Existe por una razón muy concreta: la clienta que vuelve cada tres semanas **no busca**, va al
 * mismo sitio. Obligarla a escribir el nombre otra vez es cobrarle el peaje de la búsqueda a
 * quien ya decidió.
 */

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import { Boton } from '@/componentes/boton';
import { Cargando, Roto, Vacio } from '@/componentes/estados';
import { Abierto, Inicial, Nota } from '@/componentes/piezas';
import { api, comoMensaje, type NegocioFavorito } from '@/lib/api';
import { conSesion, leerSesion } from '@/lib/sesion';

export function MisSalones() {
  const [lista, setLista] = useState<NegocioFavorito[] | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [sinSesion, setSinSesion] = useState(false);
  const [quitando, setQuitando] = useState<string | null>(null);

  const traer = useCallback(() => {
    if (!leerSesion()) {
      setSinSesion(true);
      return;
    }
    setFallo(null);
    conSesion((acceso) => api.favoritos(acceso))
      .then(setLista)
      .catch((error) => setFallo(comoMensaje(error)));
  }, []);
  useEffect(traer, [traer]);

  async function quitar(negocio: NegocioFavorito) {
    setQuitando(negocio.negocio_id);
    try {
      await conSesion((acceso) => api.quitarFavorito(negocio.negocio_id, acceso));
      setLista((actual) => (actual ?? []).filter((f) => f.negocio_id !== negocio.negocio_id));
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setQuitando(null);
    }
  }

  if (sinSesion)
    return (
      <Vacio
        titulo="Entra para guardar salones"
        explicacion="Los salones que guardes se quedan aquí, para volver sin buscar."
        accion={
          <Link className="boton boton--abre" href="/entrar?volver=%2Fmis-salones">
            Entrar
          </Link>
        }
      />
    );
  if (fallo) return <Roto mensaje={fallo} accion={<Boton tono="abre" onClick={traer} hijos="Reintentar" />} />;
  if (!lista) return <Cargando que="Buscando tus salones" filas={3} />;
  if (lista.length === 0)
    return (
      <Vacio
        titulo="Todavía no has guardado ninguno"
        explicacion="En la ficha de cualquier salón hay un botón para guardarlo. Después vuelves aquí y está."
        accion={
          <Link className="boton boton--abre" href="/buscar">
            Buscar un salón
          </Link>
        }
      />
    );

  return (
    <ul className="pila pila--apretada">
      {lista.map((salon) => (
        <li key={salon.negocio_id} className="ficha-persona">
          <Link className="ficha-persona__quien" href={`/salon/${salon.slug}`}>
            <Inicial texto={salon.nombre} />
            <span className="pila pila--apretada">
              <span className="rotulo rotulo--pequeno">{salon.nombre}</span>
              <span className="fila__datos">
                {salon.zona ? <span>{salon.zona}</span> : null}
                <Nota valor={salon.rating} resenas={salon.numero_reviews} />
                <Abierto abierto={salon.abierto_ahora} />
              </span>
            </span>
          </Link>
          <div className="ficha-persona__acciones">
            <Boton
              tono="secundario"
              onClick={() => void quitar(salon)}
              cargando={quitando === salon.negocio_id}
              rotuloCargando="Quitando"
              hijos="Quitar"
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
