'use client';

/**
 * Mi cuenta: mis datos y **la puerta de salida** (Ley 81 · ADR-0025).
 *
 * La ley no da solo el derecho a que te borren: da el derecho a **ejercerlo**, y un derecho que
 * hay que pedir por correo y esperar a que alguien conteste no está ejercido. Aquí se hace en
 * la pantalla y en el momento.
 *
 * ## Lo que se enseña antes de borrar son números, no advertencias
 *
 * «Esto no se puede deshacer» no informa de nada: lo sabe todo el mundo. Lo que hace decidir es
 * **«tienes dos citas puestas y catorce hechas»**. Y lo que se queda también se dice, porque es
 * lo que la gente pregunta: las opiniones no desaparecen, se quedan sin tu nombre.
 *
 * ## Se escribe una palabra a mano
 *
 * No es ceremonia. Un botón de borrar detrás de una sola confirmación se pulsa por error desde
 * un móvil, y esto no tiene vuelta. Escribir cuesta tres segundos y los tres segundos son el
 * punto.
 *
 * ## Y si llevas un salón, no se puede, y se dice por qué
 *
 * Un salón publicado cuyo dueño desaparece sigue aceptando reservas, y la clienta que reserve
 * se encuentra la puerta cerrada. No es una traba administrativa: cerrarlo o pasarlo a otra
 * persona es una decisión suya y tiene que tomarla antes.
 */

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import { Boton } from '@/componentes/boton';
import { Cargando, Roto } from '@/componentes/estados';
import { api, comoMensaje, type LoQueSeVa, type MiPerfil } from '@/lib/api';
import { borrarSesion, conSesion } from '@/lib/sesion';

export function MiCuenta() {
  const router = useRouter();
  const [perfil, setPerfil] = useState<MiPerfil | null>(null);
  const [seVa, setSeVa] = useState<LoQueSeVa | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [abriendoLaPuerta, setAbriendoLaPuerta] = useState(false);
  const [escrito, setEscrito] = useState('');
  const [yendose, setYendose] = useState(false);

  const traer = useCallback(() => {
    Promise.all([
      conSesion((acceso) => api.miPerfil(acceso)),
      conSesion((acceso) => api.loQueSeVa(acceso)),
    ])
      .then(([mio, cuentas]) => {
        setPerfil(mio);
        setSeVa(cuentas);
      })
      .catch((error) => setFallo(comoMensaje(error)));
  }, []);

  useEffect(traer, [traer]);

  async function irse() {
    setYendose(true);
    setFallo(null);
    try {
      await conSesion((acceso) => api.darmeDeBaja(acceso));
      // La sesión ya no vale para nada —las suyas se borraron en el servidor—, así que se
      // limpia aquí también y se sale a la calle. Dejarla puesta enseñaría pantallas con datos
      // que ya no existen.
      borrarSesion();
      router.replace('/?adios=1');
    } catch (error) {
      setFallo(comoMensaje(error));
      setYendose(false);
    }
  }

  if (fallo && perfil === null) {
    return <Roto mensaje={fallo} accion={<Boton tono="secundario" onClick={traer} hijos="Volver a intentarlo" />} />;
  }
  if (perfil === null || seVa === null) return <Cargando que="Abriendo tu cuenta" filas={2} />;

  return (
    <div className="pila">
      <div className="pila pila--apretada">
        <span className="etiqueta">Tus datos</span>
        <ul className="lista-marcada">
          <li>{perfil.nombre}</li>
          {perfil.telefono ? <li className="cifras">{perfil.telefono}</li> : null}
          {perfil.correo ? <li>{perfil.correo}</li> : null}
        </ul>
      </div>

      <div className="pila pila--apretada">
        <span className="etiqueta">Darte de baja</span>

        {seVa.lleva_un_salon ? (
          <div className="bloque bloque--aviso relleno pila pila--apretada">
            <p>
              Llevas un salón, y un salón sin nadie detrás sigue aceptando reservas: quien reserve se
              encontrará la puerta cerrada.
            </p>
            <p className="menor">
              Ciérralo o pásalo a otra persona desde el portal del salón, y entonces podrás darte de baja.
            </p>
            <Link className="boton boton--secundario" href="/local">
              Ir al portal del salón
            </Link>
          </div>
        ) : !abriendoLaPuerta ? (
          <>
            <p className="parrafo">
              Se borra tu nombre, tu teléfono y tu correo, y no se puede deshacer.
            </p>
            <Boton tono="riesgo-suave" onClick={() => setAbriendoLaPuerta(true)} hijos="Quiero darme de baja" />
          </>
        ) : (
          <div className="bloque bloque--peligro relleno pila pila--apretada" role="group">
            {/* Los números de verdad, que es lo que deja decidir. Una advertencia genérica no. */}
            <p>Esto es lo que va a pasar:</p>
            <ul className="lista-marcada">
              <li>
                {seVa.citas_por_venir === 0
                  ? 'No tienes ninguna cita por venir.'
                  : `Se cancelan tus ${seVa.citas_por_venir} ${seVa.citas_por_venir === 1 ? 'cita' : 'citas'} por venir, y el salón recupera esas horas.`}
              </li>
              <li>Se borran tu nombre, tu teléfono y tu correo, aquí y en la ficha de cada salón.</li>
              <li>
                {seVa.citas_pasadas === 0
                  ? 'No tienes historial que quede en ningún salón.'
                  : `Tus ${seVa.citas_pasadas} citas ya hechas se quedan en la contabilidad de cada salón, sin tu nombre.`}
              </li>
              <li>
                Si escribiste alguna opinión, <strong>se queda sin tu nombre</strong>: el salón la reunió y
                quien la lee la usa para elegir.
              </li>
              <li>No se puede deshacer, y no podrás volver a entrar con esta cuenta.</li>
            </ul>

            <div className="campo">
              <label className="campo__rotulo" htmlFor="confirmar-baja">
                Escribe BORRAR para confirmarlo
              </label>
              <input
                className="campo__caja"
                id="confirmar-baja"
                value={escrito}
                autoComplete="off"
                onChange={(e) => setEscrito(e.target.value)}
              />
            </div>

            <div className="tira">
              <Boton
                tono="riesgo"
                disabled={escrito.trim().toUpperCase() !== 'BORRAR'}
                cargando={yendose}
                rotuloCargando="Borrando"
                onClick={() => void irse()}
                hijos="Borrar mi cuenta"
              />
              <Boton
                tono="secundario"
                onClick={() => {
                  setAbriendoLaPuerta(false);
                  setEscrito('');
                }}
                hijos="No, dejarlo"
              />
            </div>
          </div>
        )}

        {fallo ? (
          <p className="campo__fallo" role="alert">
            {fallo}
          </p>
        ) : null}
      </div>
    </div>
  );
}
