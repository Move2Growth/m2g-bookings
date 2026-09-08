'use client';

/**
 * El camino hasta una hora: servicio → persona → hora → confirmar.
 *
 * Tres decisiones que se ven aquí y en ningún otro sitio:
 *
 * 1 · **Cada paso es una URL.** El servicio, la persona, el día y la hora viven en la barra de
 *     direcciones. Se puede volver atrás con el botón del navegador, recargar sin perder la
 *     hora elegida y mandarle el enlace a alguien. Cero ventanas emergentes: una ventana
 *     emergente no tiene URL y no se puede compartir ni recuperar.
 *
 * 2 · **La persona es un paso de verdad, no un desplegable.** Es lo que pidió el encargo y es
 *     lo que exige la API, que rechaza una reserva sin `profesional_id`. Existe «me da igual
 *     quién», y no es trampa: se piden los huecos del salón entero, cada hueco viene con la
 *     persona que lo puede atender y se reserva con esa.
 *
 * 3 · **La hora que se acaba de ocupar se dice donde estaba la hora.** Si al confirmar la API
 *     contesta 409, no se pierde el camino: se enseña su mensaje, se vuelven a pedir los huecos
 *     de ese día y se sigue desde ahí.
 */

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { Boton } from '@/componentes/boton';
import { Cargando, Roto, Vacio } from '@/componentes/estados';
import { Inicial, Nota } from '@/componentes/piezas';
import {
  api,
  comoMensaje,
  type MiCita,
  type PerfilPublico,
  type ProfesionalDelEquipo,
  type Slot,
} from '@/lib/api';
import {
  cuandoEsEnMayuscula,
  diaLargo,
  dinero,
  duracion,
  fechaLocal,
  FRANJAS,
  hora,
  minutosDelDia,
  precioDeServicio,
  sumarDias,
} from '@/lib/formato';
import { conSesion, leerSesion } from '@/lib/sesion';

type Arranque = { servicio?: string; profesional?: string; dia?: string; inicio?: string };

export function Reserva({
  salon,
  equipo,
  inicial,
}: {
  salon: PerfilPublico;
  equipo: ProfesionalDelEquipo[];
  inicial: Arranque;
}) {
  const router = useRouter();
  const camino = usePathname();
  const zona = salon.zona_horaria;

  const [servicios, setServicios] = useState<string[]>(inicial.servicio ? [inicial.servicio] : []);
  const [profesional, setProfesional] = useState<string | null>(inicial.profesional ?? null);
  const [dia, setDia] = useState<string>(inicial.dia ?? fechaLocal(new Date(), zona));
  const [elegida, setElegida] = useState<Slot | null>(null);
  const [nota, setNota] = useState('');

  const [huecos, setHuecos] = useState<Slot[] | null>(null);
  const [cargandoHuecos, setCargandoHuecos] = useState(false);
  const [falloHuecos, setFalloHuecos] = useState<string | null>(null);

  const [enviando, setEnviando] = useState(false);
  const [falloEnvio, setFalloEnvio] = useState<string | null>(null);
  const [hecha, setHecha] = useState<MiCita | null>(null);
  const [haySesion, setHaySesion] = useState<boolean | null>(null);

  useEffect(() => {
    setHaySesion(leerSesion() !== null);
  }, []);

  const elegidos = useMemo(
    () => salon.servicios.filter((servicio) => servicios.includes(servicio.id)),
    [salon.servicios, servicios],
  );
  const minutos = elegidos.reduce((suma, servicio) => suma + servicio.duracion_minutos, 0);
  const total = elegidos.reduce((suma, servicio) => suma + (servicio.precio_centavos ?? 0), 0);
  const hayPrecioAConsultar = elegidos.some((servicio) => servicio.precio_centavos === null);

  /** Quién puede hacer TODO lo elegido. Si no puede con uno, no sale: no se le puede reservar. */
  const puedenAtender = useMemo(
    () => equipo.filter((persona) => servicios.every((servicio) => persona.servicios.includes(servicio))),
    [equipo, servicios],
  );

  const paso: 'servicio' | 'persona' | 'hora' | 'confirmar' = hecha
    ? 'confirmar'
    : servicios.length === 0
      ? 'servicio'
      : profesional === null
        ? 'persona'
        : elegida === null
          ? 'hora'
          : 'confirmar';

  /* La URL sigue al estado, sin apilar entradas de historia por cada toque. */
  useEffect(() => {
    const parametros = new URLSearchParams();
    if (servicios[0]) parametros.set('servicio', servicios[0]);
    if (profesional && profesional !== 'cualquiera') parametros.set('profesional', profesional);
    if (profesional === 'cualquiera') parametros.set('profesional', 'cualquiera');
    if (servicios.length > 0) parametros.set('dia', dia);
    if (elegida) parametros.set('inicio', elegida.inicio);
    const cadena = parametros.toString();
    router.replace(cadena ? `${camino}?${cadena}` : camino, { scroll: false });
  }, [servicios, profesional, dia, elegida, camino, router]);

  const pedirHuecos = useCallback(async () => {
    if (servicios.length === 0 || profesional === null) return;
    setCargandoHuecos(true);
    setFalloHuecos(null);
    try {
      const desde = `${dia}T00:00:00`;
      const hasta = `${sumarDias(dia, 1)}T00:00:00`;
      const desfase = desfaseDe(zona, new Date(`${dia}T12:00:00Z`));
      const respuesta =
        profesional === 'cualquiera'
          ? await api.horasDelNegocio(salon.slug, servicios, `${desde}${desfase}`, `${hasta}${desfase}`)
          : await api.horasDelProfesional(profesional, servicios, `${desde}${desfase}`, `${hasta}${desfase}`);
      setHuecos(respuesta.slots);
    } catch (error) {
      setFalloHuecos(comoMensaje(error));
      setHuecos(null);
    } finally {
      setCargandoHuecos(false);
    }
  }, [dia, profesional, salon.slug, servicios, zona]);

  /**
   * Se puede llegar con una persona ya puesta en la URL —desde «Ver sus horas»— y elegir
   * después un servicio que esa persona NO hace. Entonces la elección se suelta y se vuelve al
   * paso de la persona, en vez de pedir huecos que van a venir vacíos sin explicar por qué.
   */
  useEffect(() => {
    if (
      profesional !== null &&
      profesional !== 'cualquiera' &&
      servicios.length > 0 &&
      !puedenAtender.some((persona) => persona.id === profesional)
    ) {
      setProfesional(null);
      setElegida(null);
    }
  }, [profesional, servicios, puedenAtender]);

  useEffect(() => {
    if (servicios.length > 0 && profesional !== null) void pedirHuecos();
  }, [pedirHuecos, servicios.length, profesional]);

  /* Si venimos de un enlace con `inicio`, se recupera esa hora en cuanto llegan los huecos. */
  useEffect(() => {
    if (!inicial.inicio || elegida || !huecos) return;
    const encontrada = huecos.find((slot) => slot.inicio === inicial.inicio);
    if (encontrada) setElegida(encontrada);
    // Solo la primera vez que llegan huecos.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [huecos]);

  async function confirmar() {
    if (!elegida) return;
    setEnviando(true);
    setFalloEnvio(null);
    try {
      const quien = profesional === 'cualquiera' ? elegida.profesional_id : profesional;
      if (!quien) {
        setFalloEnvio('Ese hueco no dice quién lo atiende. Elige a alguien del equipo y vuelve a intentarlo.');
        return;
      }
      const llave = `${salon.slug}-${elegida.inicio}-${servicios.join('-')}`;
      const cita = await conSesion((acceso) =>
        api.reservar(
          {
            negocio_slug: salon.slug,
            servicios,
            inicio: elegida.inicio,
            profesional_id: quien,
            nota: nota.trim() || null,
          },
          acceso,
          llave,
        ),
      );
      setHecha(cita);
    } catch (error) {
      setFalloEnvio(comoMensaje(error));
      setElegida(null);
      void pedirHuecos();
    } finally {
      setEnviando(false);
    }
  }

  if (hecha) {
    return (
      <div className="contenido" data-superficie="local">
        <div className="seccion pila aparece">
          <div className="bloque bloque--exito relleno--grande pila">
            <span className="etiqueta">Confirmada</span>
            <h1 className="rotulo rotulo--grande">Tu turno está cogido.</h1>
            <p className="parrafo">
              {diaLargo(hecha.inicio, hecha.zona_horaria)} a las {hora(hecha.inicio, hecha.zona_horaria)}, en{' '}
              {hecha.negocio}.
            </p>
          </div>
          <dl className="resumen">
            <div className="resumen__linea">
              <dt>Qué</dt>
              <dd>{hecha.servicios.map((servicio) => servicio.nombre).join(' + ')}</dd>
            </div>
            <div className="resumen__linea">
              <dt>Cuánto dura</dt>
              <dd>{duracion(hecha.servicios.reduce((suma, servicio) => suma + servicio.duracion_minutos, 0))}</dd>
            </div>
            <div className="resumen__linea">
              <dt>Total</dt>
              <dd>{dinero(hecha.total_centavos)}</dd>
            </div>
          </dl>
          <div className="tira">
            <Link className="boton boton--abre" href="/mis-citas">
              Ver mis citas
            </Link>
            <Link className="boton boton--secundario" href={`/salon/${salon.slug}`}>
              Volver al salón
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="contenido" data-superficie="local">
      <nav className="migas" aria-label="Dónde estás">
        <Link href="/">Portada</Link>
        <span aria-hidden="true">›</span>
        <Link href={`/salon/${salon.slug}`}>{salon.nombre}</Link>
        <span aria-hidden="true">›</span>
        <span>Reservar</span>
      </nav>

      <h1 className="rotulo rotulo--grande">Reservar en {salon.nombre}</h1>

      <ol className="pasos" aria-label="Por dónde vas">
        {(
          [
            ['servicio', 'Qué'],
            ['persona', 'Con quién'],
            ['hora', 'Cuándo'],
            ['confirmar', 'Confirmar'],
          ] as const
        ).map(([clave, rotulo], indice) => {
          const orden = ['servicio', 'persona', 'hora', 'confirmar'];
          const estado = orden.indexOf(clave) < orden.indexOf(paso) ? 'hecho' : clave === paso ? 'ahora' : 'falta';
          return (
            <li key={clave} className="paso" data-estado={estado} aria-current={clave === paso ? 'step' : undefined}>
              {indice + 1}. {rotulo}
            </li>
          );
        })}
      </ol>

      {/* ── 1 · Qué ─────────────────────────────────────────────────────────────────────── */}
      <section className="seccion--corta" aria-label="Elegir servicio">
        <div className="titulo-seccion">
          <h2 className="rotulo rotulo--pequeno">1 · Qué te vas a hacer</h2>
          {servicios.length > 0 ? <span className="menor">{duracion(minutos)}</span> : null}
        </div>
        <ul className="lista">
          {salon.servicios.map((servicio) => {
            const puesto = servicios.includes(servicio.id);
            return (
              <li key={servicio.id} className="fila">
                <button
                  type="button"
                  className="opcion opcion--ancha opcion--entre"
                  aria-pressed={puesto}
                  onClick={() => {
                    setElegida(null);
                    setServicios((antes) =>
                      antes.includes(servicio.id)
                        ? antes.filter((id) => id !== servicio.id)
                        : [...antes, servicio.id],
                    );
                  }}
                >
                  <span>{servicio.nombre}</span>
                  <span>
                    {duracion(servicio.duracion_minutos)} · {precioDeServicio(servicio)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        {servicios.length === 0 ? <p className="campo__pista">Puedes encadenar varios: corte y barba, por ejemplo.</p> : null}
      </section>

      {/* ── 2 · Con quién ───────────────────────────────────────────────────────────────── */}
      {servicios.length > 0 ? (
        <section className="seccion--corta" aria-label="Elegir persona">
          <div className="titulo-seccion">
            <h2 className="rotulo rotulo--pequeno">2 · Con quién</h2>
          </div>

          {puedenAtender.length === 0 ? (
            <Vacio
              titulo="Nadie hace todo eso a la vez"
              explicacion="Ninguna persona del equipo tiene asignados todos los servicios que elegiste. Quita alguno y vuelve a mirar."
            />
          ) : (
            <ul className="lista">
              <li className="fila">
                <button
                  type="button"
                  className="opcion opcion--ancha"
                  aria-pressed={profesional === 'cualquiera'}
                  onClick={() => {
                    setElegida(null);
                    setProfesional('cualquiera');
                  }}
                >
                  Me da igual quién · quiero la hora más pronta
                </button>
              </li>
              {puedenAtender.map((persona) => (
                <li key={persona.id} className="fila fila--resultado">
                  <Inicial texto={persona.nombre} persona />
                  <div className="fila__cuerpo">
                    <span className="fila__titulo">{persona.nombre}</span>
                    {persona.titular ? <p className="menor">{persona.titular}</p> : null}
                    <p className="fila__datos">
                      {persona.anos_de_experiencia ? <span>{persona.anos_de_experiencia} años</span> : null}
                      <Nota valor={persona.nota} resenas={persona.numero_resenas} />
                    </p>
                    <div className="fila__pie">
                      <button
                        type="button"
                        className="opcion"
                        aria-pressed={profesional === persona.id}
                        onClick={() => {
                          setElegida(null);
                          setProfesional(persona.id);
                        }}
                      >
                        {profesional === persona.id ? 'Elegida' : `Con ${persona.nombre.split(' ')[0]}`}
                      </button>
                      <Link
                        className="boton boton--texto"
                        href={`/salon/${salon.slug}/con/${persona.slug ?? persona.id}`}
                      >
                        Su perfil
                      </Link>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {/* ── 3 · Cuándo ──────────────────────────────────────────────────────────────────── */}
      {servicios.length > 0 && profesional !== null ? (
        <section className="seccion--corta" aria-label="Elegir día y hora">
          <div className="titulo-seccion">
            <h2 className="rotulo rotulo--pequeno">3 · Cuándo</h2>
            <span className="menor">{diaLargo(`${dia}T12:00:00Z`, 'UTC')}</span>
          </div>

          <div className="pila pila--apretada">
            <span className="etiqueta">Qué día</span>
            <div className="opciones">
              {Array.from({ length: 7 }).map((_, salto) => {
                const candidato = sumarDias(fechaLocal(new Date(), zona), salto);
                return (
                  <button
                    key={candidato}
                    type="button"
                    className="opcion"
                    aria-pressed={candidato === dia}
                    onClick={() => {
                      setElegida(null);
                      setDia(candidato);
                    }}
                  >
                    {cuandoEsEnMayuscula(`${candidato}T12:00:00Z`, 'UTC')}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Aquí, y no en el resumen: cuando la API contesta 409 la hora elegida se suelta y el
              resumen desaparece con ella. Si el aviso viviera dentro del resumen se iría con
              él, y la clienta se quedaría mirando una lista de horas sin saber por qué volvió
              atrás. El aviso se queda donde estaba la hora. */}
          {falloEnvio ? (
            <div className="bloque bloque--peligro relleno" role="alert">
              <p>{falloEnvio}</p>
            </div>
          ) : null}

          <div className="pila">
            {cargandoHuecos ? (
              <Cargando que="Calculando los huecos de ese día" filas={2} />
            ) : falloHuecos ? (
              <Roto
                mensaje={falloHuecos}
                accion={
                  <Boton tono="secundario" onClick={() => void pedirHuecos()} hijos="Volver a intentarlo" />
                }
              />
            ) : huecos && huecos.length === 0 ? (
              <Vacio
                titulo="Ese día está lleno"
                explicacion="No queda ningún hueco con esa duración. Prueba otro día o con otra persona."
              />
            ) : huecos ? (
              FRANJAS.map((franja) => {
                const deLaFranja = huecos.filter((slot) => {
                  const minuto = minutosDelDia(slot.inicio, zona);
                  return minuto >= franja.desde && minuto < franja.hasta;
                });
                if (deLaFranja.length === 0) return null;
                return (
                  <div key={franja.clave} className="franja-horas">
                    <span className="etiqueta">
                      {franja.rotulo} · {deLaFranja.length} huecos
                    </span>
                    <div className="horas">
                      {deLaFranja.map((slot) => (
                        <button
                          key={`${slot.inicio}-${slot.profesional_id ?? ''}`}
                          type="button"
                          className="hora"
                          aria-pressed={elegida?.inicio === slot.inicio}
                          onClick={() => setElegida(slot)}
                        >
                          {hora(slot.inicio, zona)}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })
            ) : null}
          </div>
        </section>
      ) : null}

      {/* ── 4 · Confirmar ───────────────────────────────────────────────────────────────── */}
      {elegida ? (
        <section className="seccion--corta aparece" aria-label="Confirmar">
          <div className="titulo-seccion">
            <h2 className="rotulo rotulo--pequeno">4 · Confirmar</h2>
          </div>

          <dl className="resumen">
            <div className="resumen__linea">
              <dt>Qué</dt>
              <dd>{elegidos.map((servicio) => servicio.nombre).join(' + ')}</dd>
            </div>
            <div className="resumen__linea">
              <dt>Con quién</dt>
              <dd>{nombreDeQuien(equipo, profesional, elegida)}</dd>
            </div>
            <div className="resumen__linea">
              <dt>Cuándo</dt>
              <dd>
                {diaLargo(elegida.inicio, zona)}, {hora(elegida.inicio, zona)}
              </dd>
            </div>
            <div className="resumen__linea">
              <dt>Cuánto dura</dt>
              <dd>{duracion(minutos)}</dd>
            </div>
            <div className="resumen__linea">
              <dt>Total</dt>
              <dd>{hayPrecioAConsultar ? `${dinero(total)} + a consultar` : dinero(total)}</dd>
            </div>
          </dl>

          <div className="campo campo--separado">
            <label className="campo__rotulo" htmlFor="nota">
              Algo que deba saber (opcional)
            </label>
            <textarea
              className="campo__caja"
              id="nota"
              name="nota"
              rows={2}
              value={nota}
              onChange={(evento) => setNota(evento.target.value)}
              placeholder="Vengo con el pelo teñido, llego cinco minutos tarde…"
            />
          </div>

          {haySesion === false ? (
            <div className="pila pila--apretada">
              <div className="bloque bloque--aviso relleno" role="note">
                <p>Para coger la hora hay que entrar. Se guarda lo que llevas elegido.</p>
              </div>
              <Link
                className="boton boton--cierra boton--bloque"
                href={`/entrar?volver=${encodeURIComponent(`${camino}?servicio=${servicios[0]}&profesional=${profesional}&dia=${dia}&inicio=${encodeURIComponent(elegida.inicio)}`)}`}
              >
                Entrar y confirmar
              </Link>
            </div>
          ) : (
            <Boton
              tono="cierra"
              bloque
              cargando={enviando}
              rotuloCargando="Cogiendo la hora"
              onClick={() => void confirmar()}
              hijos={`Confirmar ${hora(elegida.inicio, zona)}`}
            />
          )}
        </section>
      ) : null}
    </div>
  );
}

function nombreDeQuien(equipo: ProfesionalDelEquipo[], profesional: string | null, elegida: Slot): string {
  const id = profesional === 'cualquiera' ? elegida.profesional_id : profesional;
  const persona = equipo.find((quien) => quien.id === id);
  if (!persona) return 'Quien esté libre';
  return profesional === 'cualquiera' ? `${persona.nombre} (el primero libre)` : persona.nombre;
}

/** El desfase de la zona del salón ese día, para pedir el rango sin equivocarse de hora. */
function desfaseDe(zona: string, referencia: Date): string {
  const formato = new Intl.DateTimeFormat('en-US', { timeZone: zona, timeZoneName: 'longOffset' });
  const parte = formato.formatToParts(referencia).find((trozo) => trozo.type === 'timeZoneName')?.value ?? 'GMT+00:00';
  return parte.replace('GMT', '') || '+00:00';
}
