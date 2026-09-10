'use client';

/**
 * Las fotos del salón: la portada y la galería (NEG-1, D11).
 *
 * Es la pantalla que faltaba. Sin ella una foto solo se podía poner el día del alta y nunca
 * cambiar, y la primera foto que sube un salón casi nunca es la buena: la buena la hacen la
 * semana siguiente, con luz.
 *
 * **La portada se enseña grande y aparte**, porque no es una foto más: es la única que se ve en
 * el listado de búsqueda y en el mapa, y por tanto la que decide si alguien entra. Mezclarla con
 * las demás en una cuadrícula esconde justo esa diferencia.
 *
 * **Cambiar de portada no borra la anterior**: pasa a la galería. Lo hace la API y aquí se dice,
 * porque «poner de portada» sonando a que la otra desaparece hace que nadie lo pruebe.
 */

import { useCallback, useEffect, useState } from 'react';

import { Boton } from '@/componentes/boton';
import { Cargando, Roto, Vacio } from '@/componentes/estados';
import { SubirFoto } from '@/componentes/subir-foto';
import { api, comoMensaje, type FotoDelSalon } from '@/lib/api';
import { conSesion } from '@/lib/sesion';

export function FotosDelSalon() {
  const [fotos, setFotos] = useState<FotoDelSalon[] | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [quitando, setQuitando] = useState<string | null>(null);

  const traer = useCallback(() => {
    conSesion((acceso) => api.fotosDelLocal(acceso))
      .then(setFotos)
      .catch((error) => setFallo(comoMensaje(error)));
  }, []);

  useEffect(traer, [traer]);

  async function quitar(foto: FotoDelSalon) {
    setQuitando(foto.id);
    setFallo(null);
    try {
      await conSesion((acceso) => api.quitarFoto(foto.id, acceso));
      traer();
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setQuitando(null);
    }
  }

  async function ponerDePortada(foto: FotoDelSalon) {
    setFallo(null);
    try {
      // Se registra la MISMA clave como portada. La API se encarga de que la anterior baje a
      // galería, y de que no haya dos.
      await conSesion((acceso) =>
        api.registrarFoto(
          { clave: claveDe(foto.url), clase: 'portada', texto_alternativo: foto.texto_alternativo },
          acceso,
        ),
      );
      await conSesion((acceso) => api.quitarFoto(foto.id, acceso));
      traer();
    } catch (error) {
      setFallo(comoMensaje(error));
    }
  }

  if (fallo && fotos === null) return <Roto mensaje={fallo} accion={<Boton tono="secundario" onClick={traer} hijos="Volver a intentarlo" />} />;
  if (fotos === null) return <Cargando que="Abriendo tus fotos" filas={2} />;

  const portada = fotos.find((foto) => foto.clase === 'portada') ?? null;
  const galeria = fotos.filter((foto) => foto.clase !== 'portada');

  return (
    <div className="pila">
      <p className="parrafo">
        La <strong>portada</strong> es la única que se ve en la búsqueda y en el mapa: es la que decide si alguien
        entra en tu ficha. Las demás se ven dentro.
      </p>

      <div className="pila pila--apretada">
        <span className="etiqueta">Tu portada</span>
        {portada ? (
          <figure className="foto-grande">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={portada.url} alt={portada.texto_alternativo ?? 'La portada de tu salón'} />
            <figcaption className="tira">
              <Boton
                tono="riesgo-suave"
                onClick={() => void quitar(portada)}
                cargando={quitando === portada.id}
                rotuloCargando="Quitando"
                hijos="Quitar"
              />
            </figcaption>
          </figure>
        ) : (
          <Vacio
            titulo="Todavía no tienes portada"
            explicacion="Sin una foto tu salón no se puede publicar. Con el escaparate o la silla recién ordenada basta."
          />
        )}
        <SubirFoto
          clase="portada"
          rotulo={portada ? 'Cambiar la portada' : 'Subir la portada'}
          alSubir={traer}
        />
      </div>

      <div className="pila pila--apretada">
        <span className="etiqueta">Las demás</span>
        {galeria.length === 0 ? (
          <p className="menor tenue">Aquí van trabajos, el local por dentro, el equipo.</p>
        ) : (
          <ul className="galeria">
            {galeria.map((foto) => (
              <li key={foto.id} className="galeria__pieza">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={foto.url} alt={foto.texto_alternativo ?? 'Una foto de tu salón'} />
                <span className="tira">
                  <Boton tono="texto" onClick={() => void ponerDePortada(foto)} hijos="De portada" />
                  <Boton
                    tono="texto"
                    onClick={() => void quitar(foto)}
                    cargando={quitando === foto.id}
                    rotuloCargando="Quitando"
                    hijos="Quitar"
                  />
                </span>
              </li>
            ))}
          </ul>
        )}
        <SubirFoto alSubir={traer} />
      </div>

      {fallo ? (
        <p className="campo__fallo" role="alert">
          {fallo}
        </p>
      ) : null}
    </div>
  );
}

/**
 * De la URL servida a la clave guardada.
 *
 * La API devuelve la URL compuesta —es lo que se pinta— pero para volver a registrar la misma
 * foto como portada hace falta **la clave**. Se recorta por el nombre del cubo, que es donde
 * empieza. Si algún día la URL viniera de otro sitio, esto devuelve la URL entera y la API la
 * acepta como absoluta, que es exactamente lo que hay que hacer con una foto de fuera.
 */
function claveDe(url: string): string {
  const corte = url.indexOf('/negocios/');
  return corte === -1 ? url : url.slice(corte + 1);
}
