'use client';

/**
 * Las cuatro pantallas del portal del dueño que no son la agenda (encargo §6).
 *
 * Van juntas en un archivo porque comparten lo único que tienen en común y que importa: **las
 * cuatro piden con la sesión del salón, las cuatro pueden llegar vacías y las cuatro tienen que
 * decirlo sin parecer rotas**. Un salón nuevo no tiene dinero hecho, ni podio, ni anuncio; y esa
 * pantalla es la que más veces se va a ver el primer día.
 */

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import { Boton } from '@/componentes/boton';
import { QrDelSalon } from '@/componentes/qr-del-salon';
import { Cargando, Roto, Vacio } from '@/componentes/estados';
import { Inicial, Seccion } from '@/componentes/piezas';
import {
  api,
  comoMensaje,
  type AnuncioDelSalon,
  type EnElPodio,
  type Finanzas,
  type ProfesionalEnPanel,
} from '@/lib/api';
import { conSesion } from '@/lib/sesion';

/** Centavos a dólares, con el símbolo que decidió el brief (D12). */
function dinero(centavos: number): string {
  return `$${(centavos / 100).toFixed(2)}`;
}

/**
 * El molde de las cuatro: pide, y mientras tanto dice qué está pidiendo. El error trae su
 * reintento, porque «algo falló» sin una salida es una pantalla muerta.
 */
function useDelSalon<T>(pedir: (acceso: string) => Promise<T>, que: string) {
  const [dato, setDato] = useState<T | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const traer = useCallback(() => {
    setFallo(null);
    conSesion(pedir)
      .then(setDato)
      .catch((error) => setFallo(comoMensaje(error)));
    // La función de pedir cambia en cada render; lo que manda es `que`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [que]);
  useEffect(traer, [traer]);
  return { dato, fallo, traer };
}

/* ── El equipo, con el fichaje persona a persona ──────────────────────────────────────────── */

export function ElEquipo() {
  const { dato: gente, fallo, traer } = useDelSalon((a) => api.profesionalesDelLocal(a), 'equipo');
  const [cambiando, setCambiando] = useState<string | null>(null);
  const [falloAlCambiar, setFalloAlCambiar] = useState<string | null>(null);

  async function cambiarFichaje(persona: ProfesionalEnPanel) {
    setCambiando(persona.id);
    setFalloAlCambiar(null);
    try {
      await conSesion((acceso) => api.ponerFichaje(persona.id, !persona.fichaje_activo, acceso));
      traer();
    } catch (error) {
      setFalloAlCambiar(comoMensaje(error));
    } finally {
      setCambiando(null);
    }
  }

  if (fallo) return <Roto mensaje={fallo} accion={<Boton tono="abre" onClick={traer} hijos="Volver a intentarlo" />} />;
  if (!gente) return <Cargando que="Cargando tu equipo" />;
  if (gente.length === 0) {
    return (
      <Vacio
        titulo="Todavía no hay nadie"
        explicacion="Un salón necesita al menos una persona para poder dar horas. Invita a quien trabaja contigo, o date de alta a ti misma."
        accion={
          <Link className="boton boton--cierra" href="/local/alta">
            Añadir a alguien
          </Link>
        }
      />
    );
  }

  return (
    <div className="pila">
      {falloAlCambiar ? (
        <p className="campo__fallo" role="alert">
          {falloAlCambiar}
        </p>
      ) : null}

      <ul className="pila pila--apretada">
        {gente.map((persona) => (
          <li key={persona.id} className="ficha-persona">
            <div className="ficha-persona__quien">
              <Inicial texto={persona.nombre} persona />
              <div className="pila pila--apretada">
                <p className="rotulo rotulo--pequeno">
                  {persona.nombre}
                  {!persona.activo ? <span className="sello sello--apagado"> de baja</span> : null}
                </p>
                <p className="menor tenue">
                  {persona.titular ?? 'Sin descripción'}
                  {persona.citas_futuras > 0 ? ` · ${persona.citas_futuras} citas por delante` : ' · sin citas'}
                </p>
                <p className="menor tenue">
                  {persona.tiene_cuenta ? 'Entra con su propia cuenta' : 'Todavía sin cuenta: la agenda la lleva el salón'}
                </p>
              </div>
            </div>

            <div className="ficha-persona__acciones">
              {persona.slug ? (
                <Link className="boton boton--texto" href={`/local/equipo/${persona.slug}`}>
                  Ver su ficha
                </Link>
              ) : null}
              {/* **El fichaje es opcional y va persona a persona**, que es literal del encargo:
                  el dueño lo enciende a quien quiere y no para todos a la vez. */}
              <Boton
                tono={persona.fichaje_activo ? 'secundario' : 'abre'}
                onClick={() => cambiarFichaje(persona)}
                cargando={cambiando === persona.id}
                rotuloCargando="Cambiando"
                hijos={persona.fichaje_activo ? 'Quitarle el fichaje' : 'Pedirle fichaje'}
              />
            </div>
          </li>
        ))}
      </ul>

      <p className="menor tenue">
        El fichaje es opcional y se decide por persona. A quien lo tenga encendido se le pide marcar entrada y salida;
        a quien no, no se le pide nada.
      </p>
    </div>
  );
}

/* ── El dinero ────────────────────────────────────────────────────────────────────────────── */

const AGRUPACIONES = [
  ['dia', 'Por día'],
  ['semana', 'Por semana'],
  ['mes', 'Por mes'],
] as const;

export function ElDinero() {
  const [agrupacion, setAgrupacion] = useState<'dia' | 'semana' | 'mes'>('semana');
  const [datos, setDatos] = useState<Finanzas | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);

  const traer = useCallback(() => {
    setFallo(null);
    setDatos(null);
    const hasta = new Date();
    const desde = new Date(hasta);
    desde.setDate(desde.getDate() - (agrupacion === 'dia' ? 14 : agrupacion === 'semana' ? 56 : 365));
    const iso = (d: Date) => d.toISOString().slice(0, 10);
    conSesion((acceso) => api.finanzas(acceso, iso(desde), iso(hasta), agrupacion))
      .then(setDatos)
      .catch((error) => setFallo(comoMensaje(error)));
  }, [agrupacion]);
  useEffect(traer, [traer]);

  const tope = Math.max(1, ...(datos?.periodos ?? []).map((p) => p.importe_centavos));

  return (
    <div className="pila">
      <div className="opciones">
        {AGRUPACIONES.map(([valor, rotulo]) => (
          <button
            key={valor}
            type="button"
            className="opcion"
            data-elegida={agrupacion === valor ? 'si' : 'no'}
            aria-pressed={agrupacion === valor}
            onClick={() => setAgrupacion(valor)}
          >
            {rotulo}
          </button>
        ))}
      </div>

      {fallo ? <Roto mensaje={fallo} accion={<Boton tono="abre" onClick={traer} hijos="Volver a intentarlo" />} /> : null}
      {!datos && !fallo ? <Cargando que="Echando la cuenta" filas={4} /> : null}

      {datos ? (
        <>
          <ul className="cifras-grandes">
            <li>
              <span className="cifras-grandes__valor">{dinero(datos.importe_centavos)}</span>
              <span className="cifras-grandes__que">facturado</span>
            </li>
            <li>
              <span className="cifras-grandes__valor">{datos.citas}</span>
              <span className="cifras-grandes__que">citas atendidas</span>
            </li>
            <li>
              <span className="cifras-grandes__valor">{dinero(datos.ticket_medio_centavos)}</span>
              <span className="cifras-grandes__que">por cita</span>
            </li>
          </ul>

          {/* **El número que hace honesta a la media.** Si hay citas sin precio —«a consultar»—
              el ticket medio se calcula sobre menos citas de las que se ven, y callarlo es
              enseñar una media que no cuadra con lo que hay en la caja. */}
          {datos.citas_sin_precio > 0 ? (
            <p className="bloque relleno menor">
              {datos.citas_sin_precio} de esas citas iban <strong>a consultar</strong>, así que no suman al importe. La
              media es de las que sí tenían precio.
            </p>
          ) : null}

          {datos.periodos.length === 0 ? (
            <Vacio
              titulo="Todavía no hay nada que contar"
              explicacion="Aquí sale el dinero de las citas ya atendidas. En cuanto cierres la primera, aparece."
            />
          ) : (
            <Seccion titulo="Cómo ha ido">
              <ul className="barras">
                {datos.periodos.map((periodo) => (
                  <li key={periodo.inicio} className="barras__fila">
                    <span className="barras__cuando">
                      {new Intl.DateTimeFormat('es-PA', {
                        day: agrupacion === 'mes' ? undefined : 'numeric',
                        month: 'short',
                        year: agrupacion === 'mes' ? 'numeric' : undefined,
                        timeZone: datos.zona,
                      }).format(new Date(periodo.inicio))}
                    </span>
                    {/* La barra es un elemento de interfaz, no un adorno: lleva su cifra al lado
                        porque una barra sin número no se puede leer con precisión. */}
                    <span className="barras__pista">
                      <span
                        className="barras__relleno"
                        style={{ inlineSize: `${Math.round((periodo.importe_centavos / tope) * 100)}%` }}
                      />
                    </span>
                    <span className="barras__cuanto cifras">{dinero(periodo.importe_centavos)}</span>
                  </li>
                ))}
              </ul>
            </Seccion>
          )}
        </>
      ) : null}
    </div>
  );
}

/* ── El mejor del mes ─────────────────────────────────────────────────────────────────────── */

export function MejorDelMes() {
  const [criterio, setCriterio] = useState<'importe' | 'servicios'>('importe');
  const [podio, setPodio] = useState<EnElPodio[] | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);

  const traer = useCallback(() => {
    setFallo(null);
    setPodio(null);
    conSesion((acceso) => api.mejorDelMes(acceso, criterio))
      .then(setPodio)
      .catch((error) => setFallo(comoMensaje(error)));
  }, [criterio]);
  useEffect(traer, [traer]);

  return (
    <div className="pila">
      <div className="opciones">
        <button
          type="button"
          className="opcion"
          data-elegida={criterio === 'importe' ? 'si' : 'no'}
          aria-pressed={criterio === 'importe'}
          onClick={() => setCriterio('importe')}
        >
          Quién facturó más
        </button>
        <button
          type="button"
          className="opcion"
          data-elegida={criterio === 'servicios' ? 'si' : 'no'}
          aria-pressed={criterio === 'servicios'}
          onClick={() => setCriterio('servicios')}
        >
          Quién hizo más servicios
        </button>
      </div>

      {fallo ? <Roto mensaje={fallo} accion={<Boton tono="abre" onClick={traer} hijos="Volver a intentarlo" />} /> : null}
      {!podio && !fallo ? <Cargando que="Contando el mes" /> : null}

      {podio && podio.length === 0 ? (
        <Vacio
          titulo="El mes todavía está en blanco"
          explicacion="Aquí sale quién va por delante en cuanto haya citas cerradas este mes."
        />
      ) : null}

      {podio && podio.length > 0 ? (
        <ol className="podio">
          {podio.map((quien, puesto) => (
            <li key={quien.profesional_id} className="podio__puesto" data-primero={puesto === 0 ? 'si' : 'no'}>
              <span className="podio__numero cifras">{puesto + 1}</span>
              <span className="pila pila--apretada">
                <span className="rotulo rotulo--pequeno">{quien.nombre}</span>
                <span className="menor tenue">
                  {quien.servicios} servicios · {dinero(quien.importe_centavos)}
                </span>
              </span>
              <span className="podio__cifra cifras">
                {criterio === 'importe' ? dinero(quien.importe_centavos) : quien.servicios}
              </span>
            </li>
          ))}
        </ol>
      ) : null}

      {/* Un empate a la cabeza es información, no un fallo de la pantalla. */}
      {podio && podio.length > 1 && podio[0].importe_centavos === podio[1].importe_centavos && criterio === 'importe' ? (
        <p className="menor tenue">Van empatados. Aquí no se desempata a dedo: si es empate, se dice.</p>
      ) : null}
    </div>
  );
}

/* ── La publicidad flash ──────────────────────────────────────────────────────────────────── */

export function Publicidad() {
  const { dato: anuncios, fallo, traer } = useDelSalon((a) => api.anuncios(a), 'anuncios');
  // El QR y el enlace viven aquí y no en una puerta propia: son lo mismo que el anuncio —cómo
  // llega gente a tu ficha—, y una puerta más en el carril por cada cosa que se reparte
  // acabaría siendo un menú donde ya no se encuentra nada.
  const { dato: suyos } = useDelSalon((a) => api.misNegocios(a), 'mis-negocios');
  const salon = suyos?.[0] ?? null;
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [falloAlEscribir, setFalloAlEscribir] = useState<string | null>(null);

  async function crear(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setFalloAlEscribir(null);
    try {
      await conSesion((acceso) => api.crearAnuncio(texto.trim(), acceso));
      setTexto('');
      traer();
    } catch (error) {
      setFalloAlEscribir(comoMensaje(error));
    } finally {
      setEnviando(false);
    }
  }

  async function cambiar(anuncio: AnuncioDelSalon, activo: boolean) {
    setFalloAlEscribir(null);
    try {
      await conSesion((acceso) => api.cambiarAnuncio(anuncio.id, { activo }, acceso));
      traer();
    } catch (error) {
      setFalloAlEscribir(comoMensaje(error));
    }
  }

  return (
    <div className="pila">
      <p className="parrafo">
        Una línea que sale en tu ficha, encima de todo. Sirve para lo de esta semana: una oferta, un horario raro, que
        te has mudado. <strong>Se escribe y se quita desde aquí</strong>, sin pedírselo a nadie.
      </p>

      {salon ? <QrDelSalon slug={salon.slug} nombre={salon.nombre} /> : null}

      <h2 className="rotulo">Tu línea de esta semana</h2>

      <form className="pila" onSubmit={crear} noValidate>
        <div className="campo">
          <label className="campo__rotulo" htmlFor="anuncio">
            Qué quieres decir
          </label>
          <textarea
            className="campo__caja"
            id="anuncio"
            rows={2}
            maxLength={280}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            placeholder="Esta semana, corte + barba a $15."
          />
          <p className="campo__pista">{280 - texto.length} caracteres libres.</p>
        </div>

        {/* La vista previa es el mismo bloque que verá la clienta, no una aproximación. */}
        {texto.trim() ? (
          <Seccion titulo="Así se verá en tu ficha">
            <p className="bloque bloque--cobalto relleno">{texto.trim()}</p>
          </Seccion>
        ) : null}

        {falloAlEscribir ? (
          <p className="campo__fallo" role="alert">
            {falloAlEscribir}
          </p>
        ) : null}

        <Boton
          tono="cierra"
          type="submit"
          cargando={enviando}
          rotuloCargando="Publicando"
          disabled={!texto.trim()}
          hijos="Publicar el anuncio"
        />
      </form>

      {fallo ? <Roto mensaje={fallo} accion={<Boton tono="abre" onClick={traer} hijos="Volver a intentarlo" />} /> : null}
      {!anuncios && !fallo ? <Cargando que="Buscando tus anuncios" filas={2} /> : null}

      {anuncios && anuncios.length === 0 ? (
        <Vacio titulo="No tienes ningún anuncio" explicacion="Cuando escribas uno, sale aquí y en tu ficha pública." />
      ) : null}

      {/* **Solo se ve uno.** La ficha pública pinta un anuncio, no una lista, así que tener dos
          encendidos no los enseña los dos: enseña uno y esconde el otro sin decírselo a nadie.
          Aquí se dice, y se dice cuál se está viendo. */}
      {anuncios && anuncios.filter((a) => a.activo).length > 1 ? (
        <p className="bloque relleno menor" role="note">
          Tienes {anuncios.filter((a) => a.activo).length} anuncios encendidos y en tu ficha{' '}
          <strong>solo sale uno</strong>. Retira los que no quieras que salgan.
        </p>
      ) : null}

      {anuncios && anuncios.length > 0 ? (
        <Seccion titulo={`Tus anuncios (${anuncios.length})`}>
          <ul className="pila pila--apretada">
            {anuncios.map((anuncio) => (
              <li key={anuncio.id} className="anuncio">
                <p>{anuncio.texto}</p>
                <p className="menor tenue">
                  {anuncio.vigente ? 'Se está viendo ahora' : anuncio.activo ? 'Encendido, fuera de fecha' : 'Apagado'}
                </p>
                {/* **Un solo botón, porque la API hace una sola cosa.** Retirar un anuncio lo
                    apaga y conserva la fila a propósito —«por si el salón quiere volver a
                    lanzarlo en diciembre»—, así que un botón de «Borrar» al lado de «Apagar»
                    prometía algo que no pasa: se pulsaba y el anuncio seguía en la lista. */}
                <div className="tira">
                  <Boton
                    tono="secundario"
                    onClick={() => cambiar(anuncio, !anuncio.activo)}
                    hijos={anuncio.activo ? 'Retirar de mi ficha' : 'Volver a lanzarlo'}
                  />
                </div>
              </li>
            ))}
          </ul>
        </Seccion>
      ) : null}
    </div>
  );
}
