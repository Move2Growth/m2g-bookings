'use client';

/**
 * Mis citas.
 *
 * Lo primero que se ve es **el próximo turno**, grande y solo, porque el 90 % de las veces que
 * alguien abre esta pantalla es para acordarse de a qué hora tiene que estar. Lo demás va
 * debajo y en pequeño.
 *
 * Cancelar no abre una ventana emergente: la fila se convierte en su propia pregunta, con el
 * sí y el no a la vista. Una ventana emergente en un móvil tapa justo lo que hay que leer
 * antes de decidir.
 */

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { Boton } from '@/componentes/boton';
import { Opinar } from '@/componentes/opinar';
import { Cargando, Roto, Vacio } from '@/componentes/estados';
import { api, comoMensaje, type MiCita } from '@/lib/api';
import { cuandoEs, diaLargo, dinero, duracion, estaCancelada, familiaDeEstado, hora, rotuloDeEstado } from '@/lib/formato';
import { conSesion, leerSesion } from '@/lib/sesion';

export function MisCitas() {
  const router = useRouter();
  const [opinando, setOpinando] = useState<string | null>(null);
  /** Cuántas páginas de historia se han pedido. La primera trae además lo que viene. */
  const [paginas, setPaginas] = useState(1);
  const [trayendoMas, setTrayendoMas] = useState(false);
  const [hayMas, setHayMas] = useState(true);
  const [repitiendo, setRepitiendo] = useState<string | null>(null);

  /**
   * Reservar otra vez lo mismo. Se pregunta primero al servidor si el servicio y la persona
   * siguen existiendo: mandar a alguien a reservar algo que el salón ya quitó es peor que no
   * ofrecer el atajo. **La hora se vuelve a elegir**, porque el hueco de hace un mes no
   * significa nada hoy.
   */
  async function repetir(cita: MiCita) {
    setRepitiendo(cita.id);
    try {
      const plan = await conSesion((acceso) => api.repetir(cita.id, acceso));
      const servicio = plan.servicios.find((s) => s.sigue_disponible);
      const destino = new URLSearchParams();
      if (servicio) destino.set('servicio', servicio.id);
      if (plan.profesional_disponible && plan.profesional_id) destino.set('profesional', plan.profesional_id);
      router.push(`/reservar/${plan.negocio_slug}?${destino}`);
    } catch {
      // Si el atajo falla, la ficha del salón sigue siendo el sitio correcto al que ir.
      router.push(`/salon/${cita.negocio_slug}`);
    } finally {
      setRepitiendo(null);
    }
  }
  const [citas, setCitas] = useState<MiCita[] | null>(null);
  const [cargando, setCargando] = useState(true);
  const [fallo, setFallo] = useState<string | null>(null);
  const [sinSesion, setSinSesion] = useState(false);
  const [preguntando, setPreguntando] = useState<string | null>(null);
  const [cancelando, setCancelando] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setFallo(null);
    if (leerSesion() === null) {
      setSinSesion(true);
      setCargando(false);
      return;
    }
    setSinSesion(false);
    try {
      // Se vuelven a pedir **todas las páginas que ya estaban abiertas**: si se recarga después
      // de opinar, lo que se había desplegado no puede encogerse solo.
      const trozos = await Promise.all(
        Array.from({ length: paginas }, (_, i) => conSesion((acceso) => api.misCitas(acceso, i + 1))),
      );
      setCitas(trozos.flat());
    } catch (error) {
      if (leerSesion() === null) setSinSesion(true);
      else setFallo(comoMensaje(error));
    } finally {
      setCargando(false);
    }
  }, [paginas]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  /**
   * Traer más historia.
   *
   * La API devuelve treinta pasadas por página, y sin esto la historia se acababa ahí. No es un
   * detalle de comodidad: **el botón de opinar vive en la cita**, así que quien tenía la agenda
   * llena no llegaba nunca a una cita atendida y no podía opinar de ninguna. La cita existía, el
   * permiso existía, y no había manera de verla.
   */
  async function traerMas() {
    setTrayendoMas(true);
    try {
      const mas = await conSesion((acceso) => api.misCitas(acceso, paginas + 1));
      setCitas((antes) => [...(antes ?? []), ...mas]);
      setPaginas((n) => n + 1);
      setHayMas(mas.length === 30);
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setTrayendoMas(false);
    }
  }

  async function cancelar(cita: MiCita) {
    setCancelando(cita.id);
    setFallo(null);
    try {
      const actualizada = await conSesion((acceso) => api.cancelar(cita.id, acceso));
      setCitas((antes) => (antes ?? []).map((otra) => (otra.id === cita.id ? actualizada : otra)));
      setPreguntando(null);
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setCancelando(null);
    }
  }

  const ahora = Date.now();
  /**
   * «Lo que viene» se decide por la HORA, no por el estado. Una cita que se acaba de cancelar
   * sigue siendo de mañana, y si al cancelarla desapareciera de golpe —cayendo dentro del
   * pliegue de lo pasado— quien la canceló se quedaría sin ver que le hicieron caso.
   */
  const proximas = (citas ?? [])
    .filter((cita) => new Date(cita.inicio).getTime() >= ahora)
    .sort((una, otra) => new Date(una.inicio).getTime() - new Date(otra.inicio).getTime());
  const resto = (citas ?? []).filter((cita) => !proximas.includes(cita));
  /** El turno de arriba sí ignora las canceladas: no se recuerda una hora a la que no se va. */
  const siguiente = proximas.find((cita) => !estaCancelada(cita.estado));
  const restantes = proximas.filter((cita) => cita.id !== siguiente?.id);

  return (
    <div className="contenido" data-superficie="local">
      <div className="seccion--corta pila">
        <span className="etiqueta">Tu agenda</span>
        <h1 className="rotulo rotulo--grande">Mis citas</h1>
      </div>

      {cargando ? (
        <Cargando que="Buscando tus citas" filas={2} />
      ) : sinSesion ? (
        <div className="seccion--corta">
          <Vacio
            titulo="Aquí van tus citas, cuando entres"
            explicacion="Las citas están atadas a tu cuenta. Entra con tu correo y las verás todas, con la de más cerca arriba."
            accion={
              <Link className="boton boton--cierra" href="/entrar?volver=%2Fmis-citas">
                Entrar
              </Link>
            }
          />
        </div>
      ) : fallo && !citas ? (
        <div className="seccion--corta">
          <Roto mensaje={fallo} accion={<Boton tono="secundario" onClick={() => void cargar()} hijos="Reintentar" />} />
        </div>
      ) : (citas ?? []).length === 0 ? (
        <div className="seccion--corta">
          <Vacio
            titulo="Todavía no has reservado nada"
            explicacion="Cuando cojas una hora, aparecerá aquí con su salón, su persona y su precio."
            accion={
              <Link className="boton boton--cierra" href="/buscar?cuando=hoy">
                Ver qué hay libre hoy
              </Link>
            }
          />
        </div>
      ) : (
        <>
          {fallo ? (
            <div className="bloque bloque--peligro relleno" role="alert">
              <p>{fallo}</p>
            </div>
          ) : null}

          {siguiente ? (
            <section className="seccion--corta aparece" aria-label="Tu próximo turno">
              <div className="bloque bloque--cobalto relleno--grande pila pila--apretada">
                <span className="etiqueta etiqueta--clara">Tu próximo turno · {cuandoEs(siguiente.inicio, siguiente.zona_horaria)}</span>
                <p className="rotulo rotulo--cartel">{hora(siguiente.inicio, siguiente.zona_horaria)}</p>
                <p className="rotulo rotulo--pequeno">{siguiente.negocio}</p>
                <p>
                  {diaLargo(siguiente.inicio, siguiente.zona_horaria)} ·{' '}
                  {siguiente.servicios.map((servicio) => servicio.nombre).join(' + ')}
                </p>
                <div className="tira">
                  <Link className="boton boton--secundario" href={`/salon/${siguiente.negocio_slug}`}>
                    Ver el salón
                  </Link>
                </div>
              </div>
            </section>
          ) : null}

          <section className="seccion--corta" aria-label="Lo que viene">
            <div className="titulo-seccion">
              <h2 className="rotulo rotulo--medio">Después de esa</h2>
              <span className="menor">{restantes.length} citas</span>
            </div>

            {restantes.length === 0 ? (
              <p className="parrafo">No tienes nada más apuntado. Lo de arriba es todo.</p>
            ) : (
              <ul className="lista">{restantes.map((cita) => filaDeCita(cita))}</ul>
            )}
          </section>

          {/* Lo pasado se pliega. Con sesenta citas detrás, dejarlo abierto convierte esta
              pantalla en un rollo de veinte metros y entierra lo que sí importa. */}
          {/* Una vez que se ha pedido más historia, el pliegue **se queda abierto**: cerrarse
              solo justo después de que alguien pida ver más es contestarle que no. */}
          <details className="plegable seccion--corta" open={paginas > 1 || undefined}>
            <summary className="plegable__tirador">Lo que ya pasó ({resto.length})</summary>
            <div className="plegable__cuerpo">
              {resto.length === 0 ? (
                <p className="parrafo">Todavía no has ido a ninguna cita.</p>
              ) : (
                <>
                  <ul className="lista">{resto.map((cita) => filaDeCita(cita))}</ul>
                  {/* **Sin esto la historia se acababa a las treinta.** Y con ella se acababa la
                      posibilidad de opinar, porque el botón vive en la cita. */}
                  {hayMas ? (
                    <div className="fila__pie">
                      <Boton
                        tono="secundario"
                        onClick={() => void traerMas()}
                        cargando={trayendoMas}
                        rotuloCargando="Buscando"
                        hijos="Ver más de antes"
                      />
                    </div>
                  ) : null}
                </>
              )}
            </div>
          </details>
        </>
      )}
    </div>
  );

  /** Ya pasó si su hora de fin quedó atrás. Por la hora, no por el estado. */
  function yaPaso(cita: MiCita): boolean {
    return new Date(cita.fin).getTime() < Date.now();
  }

  function filaDeCita(cita: MiCita) {
    return (
      <li key={cita.id} className="fila">
        <div className="tira tira--entre">
          <div className="pila pila--apretada">
            <span className="cita__hora">
              {cuandoEs(cita.inicio, cita.zona_horaria)} · {hora(cita.inicio, cita.zona_horaria)}
            </span>
            <Link className="fila__titulo" href={`/salon/${cita.negocio_slug}`}>
              {cita.negocio}
            </Link>
            <span className="fila__datos">
              <span>{cita.servicios.map((servicio) => servicio.nombre).join(' + ')}</span>
              <span>
                {duracion(cita.servicios.reduce((suma, servicio) => suma + servicio.duracion_minutos, 0))}
              </span>
              <span className="cifra">{dinero(cita.total_centavos)}</span>
            </span>
          </div>
          <span className="estado" data-estado={familiaDeEstado(cita.estado)}>
            {rotuloDeEstado(cita.estado)}
          </span>
        </div>

        {/* **Opinar y repetir viven en la cita**, no en una pantalla aparte: es donde se
            acuerda uno de que fue, y donde el servidor ya ha dicho si se puede. */}
        {/* **Opinar y repetir no dependen de lo mismo, y colgarlos de la misma condición fue un
            fallo:** repetir vale para cualquier cita que ya pasó —incluida una que cancelaste— y
            opinar solo cuando el servidor dice que se puede. Con las dos juntas, «repetir» no
            aparecía casi nunca. */}
        {yaPaso(cita) && opinando !== cita.id ? (
          <div className="fila__pie">
            {cita.se_puede_resenar ? (
              <Boton tono="cierra" onClick={() => setOpinando(cita.id)} hijos="Contar qué tal fue" />
            ) : null}
            <Boton
              tono="secundario"
              onClick={() => void repetir(cita)}
              cargando={repitiendo === cita.id}
              rotuloCargando="Buscando huecos"
              hijos="Repetir esta cita"
            />
          </div>
        ) : null}

        {cita.ya_resenada ? <p className="fila__pie menor tenue">Ya opinaste de esta cita. Gracias.</p> : null}

        {opinando === cita.id ? (
          <Opinar
            cita={cita}
            alGuardar={() => {
              setOpinando(null);
              void cargar();
            }}
          />
        ) : null}

        {cita.se_puede_cancelar ? (
          preguntando === cita.id ? (
            <div className="bloque bloque--peligro relleno pila pila--apretada" role="group">
              <p>¿Seguro que sueltas esta hora? Se la queda quien la pida después.</p>
              <div className="tira">
                <Boton
                  tono="riesgo"
                  cargando={cancelando === cita.id}
                  rotuloCargando="Cancelando"
                  onClick={() => void cancelar(cita)}
                  hijos="Sí, cancelar"
                />
                <Boton tono="secundario" onClick={() => setPreguntando(null)} hijos="No, dejarla" />
              </div>
            </div>
          ) : (
            <div className="fila__pie">
              <Boton tono="riesgo-suave" onClick={() => setPreguntando(cita.id)} hijos="Cancelar" />
            </div>
          )
        ) : null}
      </li>
    );
  }
}
