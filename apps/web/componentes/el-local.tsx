'use client';

/**
 * El día del salón.
 *
 * **La decisión que separa esta pantalla de cualquier otra agenda:** a 390 px el día NO son
 * seis columnas apretadas. Seis columnas en un móvil son seis rendijas de 55 px donde no cabe
 * ni el nombre de la clienta, y el dueño acaba haciendo zoom para leer una cita. Aquí el día
 * es **un solo riel de horas**, de arriba abajo, con las personas entrelazadas y el nombre de
 * quien atiende dentro de cada bloque. En cuanto la pantalla da de sí —1024 px— el mismo día se
 * abre en columnas, una por persona, que es cuando esa forma sí ayuda.
 *
 * El color de cada bloque es el del estado de la cita, con los tokens `estado-reserva-*`: un
 * estado no es una acción, así que no usa ni el cobalto ni el fucsia de marca.
 */

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import { Boton } from '@/componentes/boton';
import { Cargando, Roto, Vacio } from '@/componentes/estados';
import { Inicial } from '@/componentes/piezas';
import { api, comoMensaje, type DiaEnColumnas, type NegocioDeLaPersona } from '@/lib/api';
import {
  cuandoEsEnMayuscula,
  diaLargo,
  dinero,
  estaCancelada,
  familiaDeEstado,
  fechaLocal,
  hora,
  minutosDelDia,
  rotuloDeEstado,
  sumarDias,
} from '@/lib/formato';
import { conSesion, guardarSesion, leerSesion } from '@/lib/sesion';

export function ElLocal() {
  const [negocios, setNegocios] = useState<NegocioDeLaPersona[] | null>(null);
  const [activo, setActivo] = useState<NegocioDeLaPersona | null>(null);
  const [dia, setDia] = useState<string>(fechaLocal(new Date()));
  const [jornada, setJornada] = useState<DiaEnColumnas | null>(null);
  const [verCanceladas, setVerCanceladas] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [fallo, setFallo] = useState<string | null>(null);
  const [sinSesion, setSinSesion] = useState(false);

  /* Paso 1: en qué salones trabaja esta persona. */
  useEffect(() => {
    let vivo = true;
    (async () => {
      if (leerSesion() === null) {
        setSinSesion(true);
        setCargando(false);
        return;
      }
      try {
        const suyos = await conSesion((acceso) => api.misNegocios(acceso));
        if (!vivo) return;
        setNegocios(suyos);
        setActivo(suyos[0] ?? null);
        if (suyos.length === 0) setCargando(false);
      } catch (error) {
        if (!vivo) return;
        if (leerSesion() === null) setSinSesion(true);
        else setFallo(comoMensaje(error));
        setCargando(false);
      }
    })();
    return () => {
      vivo = false;
    };
  }, []);

  /* Paso 2: cambiar el contexto a ese salón y pedirle el día. */
  const cargarDia = useCallback(
    async (negocio: NegocioDeLaPersona, cual: string) => {
      setCargando(true);
      setFallo(null);
      try {
        const sesion = leerSesion();
        if (!sesion) {
          setSinSesion(true);
          return;
        }
        if (sesion.negocioActivo !== negocio.id) {
          const enModo = await conSesion((acceso) => api.modoNegocio(negocio.id, acceso));
          guardarSesion(enModo);
        }
        const respuesta = await conSesion((acceso) => api.diaEnColumnas(acceso, cual));
        setJornada(respuesta);
      } catch (error) {
        if (leerSesion() === null) setSinSesion(true);
        else setFallo(comoMensaje(error));
        setJornada(null);
      } finally {
        setCargando(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (activo) void cargarDia(activo, dia);
  }, [activo, dia, cargarDia]);

  if (sinSesion) {
    return (
      <div className="contenido" data-superficie="local">
        <div className="seccion">
          <Vacio
            titulo="Esto es la trastienda del salón"
            explicacion="Entra con la cuenta del salón y verás la agenda del día con todo el equipo."
            accion={
              <Link className="boton boton--cierra" href="/entrar?volver=%2Flocal">
                Entrar
              </Link>
            }
          />
        </div>
      </div>
    );
  }

  if (negocios !== null && negocios.length === 0) {
    return (
      <div className="contenido" data-superficie="local">
        <div className="seccion">
          <Vacio
            titulo="No trabajas en ningún salón"
            explicacion="Esta cuenta no tiene ningún local asociado. Si te han invitado a uno, abre el enlace de la invitación."
            accion={
              <Link className="boton boton--abre" href="/mis-citas">
                Ver mis citas como clienta
              </Link>
            }
          />
        </div>
      </div>
    );
  }

  const todasLasCitas = (jornada?.columnas ?? []).flatMap((columna) =>
    columna.citas.map((cita) => ({ ...cita, quien: columna.nombre })),
  );
  /**
   * Las canceladas NO se pintan en el día por defecto.
   *
   * Una cita cancelada no es tiempo ocupado: es tiempo libre. Mezclarlas con las que sí vienen
   * convierte la jornada en una lista donde hay que leer el estado de cada bloque para saber
   * quién entra por la puerta, que es lo único que el salón necesita saber por la mañana. Se
   * pueden encender con un botón, porque saber cuántas se cayeron sí importa a fin de mes.
   */
  const canceladas = todasLasCitas.filter((cita) => estaCancelada(cita.estado));
  const vivas = todasLasCitas.filter((cita) => !estaCancelada(cita.estado));
  const alaVista = verCanceladas ? todasLasCitas : vivas;
  const facturado = vivas
    .filter((cita) => cita.estado !== 'no_show')
    .reduce((suma, cita) => suma + cita.importe_centavos, 0);

  return (
    <div className="contenido" data-superficie="local">
      <div className="seccion--corta pila">
        <span className="etiqueta">La agenda del salón</span>
        <h1 className="rotulo rotulo--grande">{activo?.nombre ?? 'Tu salón'}</h1>

        {negocios && negocios.length > 1 ? (
          <div className="pila pila--apretada">
            <span className="etiqueta">Qué salón</span>
            <div className="opciones">
              {negocios.map((negocio) => (
                <button
                  key={negocio.id}
                  type="button"
                  className="opcion"
                  aria-pressed={activo?.id === negocio.id}
                  onClick={() => setActivo(negocio)}
                >
                  {negocio.nombre}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        <div className="pila pila--apretada">
          <span className="etiqueta">Qué día</span>
          <div className="opciones">
            {[-1, 0, 1, 2].map((salto) => {
              const candidato = sumarDias(fechaLocal(new Date()), salto);
              return (
                <button
                  key={candidato}
                  type="button"
                  className="opcion"
                  aria-pressed={candidato === dia}
                  onClick={() => setDia(candidato)}
                >
                  {salto === -1 ? 'Ayer' : cuandoEsEnMayuscula(`${candidato}T12:00:00Z`, 'UTC')}
                </button>
              );
            })}
          </div>
        </div>

        <p className="menor">{diaLargo(`${dia}T12:00:00Z`, 'UTC')}</p>
      </div>

      {cargando ? (
        <Cargando que="Abriendo la agenda del salón" filas={3} />
      ) : fallo ? (
        <div className="seccion--corta">
          <Roto
            mensaje={fallo}
            accion={
              <Boton
                tono="secundario"
                onClick={() => activo && void cargarDia(activo, dia)}
                hijos="Volver a intentarlo"
              />
            }
          />
        </div>
      ) : jornada ? (
        <>
          <div className="datos seccion--corta">
            <div className="dato">
              <span className="dato__cifra">{vivas.length}</span>
              <span className="etiqueta">Citas del día</span>
            </div>
            <div className="dato">
              <span className="dato__cifra">{jornada.columnas.length}</span>
              <span className="etiqueta">Personas trabajando</span>
            </div>
            <div className="dato">
              <span className="dato__cifra">{dinero(facturado)}</span>
              <span className="etiqueta">Se factura hoy</span>
            </div>
          </div>

          {canceladas.length > 0 ? (
            <p className="tira">
              <button
                type="button"
                className="opcion"
                aria-pressed={verCanceladas}
                onClick={() => setVerCanceladas((antes) => !antes)}
              >
                {verCanceladas ? 'Esconder' : 'Ver'} las {canceladas.length} canceladas
              </button>
            </p>
          ) : null}

          {alaVista.length === 0 ? (
            <div className="seccion--corta">
              <Vacio
                titulo={vivas.length === 0 && canceladas.length > 0 ? 'Todo lo de este día se canceló' : 'Este día está en blanco'}
                explicacion={
                  vivas.length === 0 && canceladas.length > 0
                    ? `Hay ${canceladas.length} citas canceladas y ninguna en pie. Enciéndelas arriba si quieres verlas.`
                    : 'Nadie tiene citas ese día. Mira otro día o revisa el horario del salón.'
                }
              />
            </div>
          ) : (
            <>
              <RielDelDia jornada={jornada} soloVivas={!verCanceladas} />
              <ColumnasDelDia jornada={jornada} soloVivas={!verCanceladas} />
            </>
          )}
        </>
      ) : null}
    </div>
  );
}

/** A 390 px: una sola columna de horas con todo el equipo entrelazado. */
function RielDelDia({ jornada, soloVivas }: { jornada: DiaEnColumnas; soloVivas: boolean }) {
  const citas = jornada.columnas
    .flatMap((columna) => columna.citas.map((cita) => ({ ...cita, quien: columna.nombre })))
    .filter((cita) => !soloVivas || !estaCancelada(cita.estado))
    .sort((una, otra) => new Date(una.inicio).getTime() - new Date(otra.inicio).getTime());

  const horas = rangoDeHoras(citas.map((cita) => minutosDelDia(cita.inicio, jornada.zona)));

  return (
    <section className="riel" aria-label="El día, hora a hora">
      {horas.map((h) => {
        const deEsaHora = citas.filter((cita) => Math.floor(minutosDelDia(cita.inicio, jornada.zona) / 60) === h);
        return (
          <div key={h} style={{ display: 'contents' }}>
            <div className="riel__hora">{String(h).padStart(2, '0')}</div>
            <div className="riel__celda">
              {deEsaHora.length === 0 ? (
                <span className="riel__vacio">Libre</span>
              ) : (
                deEsaHora.map((cita) => (
                  <article key={cita.id} className="cita" data-estado={familiaDeEstado(cita.estado)}>
                    <div className="cita__linea">
                      <span className="cita__hora">
                        {hora(cita.inicio, jornada.zona)}–{hora(cita.fin, jornada.zona)}
                      </span>
                      <span className="estado" data-estado={familiaDeEstado(cita.estado)}>
                        {rotuloDeEstado(cita.estado)}
                      </span>
                    </div>
                    <p className="cita__quien">
                      {cita.cliente} · con {cita.quien}
                    </p>
                    <p className="cita__que">
                      {cita.servicios.join(' + ')} · {dinero(cita.importe_centavos)}
                    </p>
                  </article>
                ))
              )}
            </div>
          </div>
        );
      })}
    </section>
  );
}

/** A partir de 1024 px: el mismo día, una columna por persona. */
function ColumnasDelDia({ jornada, soloVivas }: { jornada: DiaEnColumnas; soloVivas: boolean }) {
  return (
    <section className="columnas" aria-label="El día por persona">
      {jornada.columnas.map((columna) => {
        const citas = columna.citas.filter((cita) => !soloVivas || !estaCancelada(cita.estado));
        return (
        <div key={columna.profesional_id}>
          <h2 className="columna__nombre">
            <Inicial texto={columna.nombre} persona />
            {columna.nombre}
          </h2>
          <div className="columna__citas">
            {citas.length === 0 ? (
              <p className="menor">Sin citas hoy</p>
            ) : (
              citas.map((cita) => (
                <article key={cita.id} className="cita" data-estado={familiaDeEstado(cita.estado)}>
                  <div className="cita__linea">
                    <span className="cita__hora">
                      {hora(cita.inicio, jornada.zona)}–{hora(cita.fin, jornada.zona)}
                    </span>
                    <span className="estado" data-estado={familiaDeEstado(cita.estado)}>
                      {rotuloDeEstado(cita.estado)}
                    </span>
                  </div>
                  <p className="cita__quien">{cita.cliente}</p>
                  <p className="cita__que">
                    {cita.servicios.join(' + ')} · {dinero(cita.importe_centavos)}
                  </p>
                </article>
              ))
            )}
            {columna.bloqueos.map((bloqueo) => (
              <p key={bloqueo.id} className="menor">
                Bloqueado {hora(bloqueo.inicio, jornada.zona)}–{hora(bloqueo.fin, jornada.zona)}
                {bloqueo.motivo ? ` · ${bloqueo.motivo}` : ''}
              </p>
            ))}
          </div>
        </div>
        );
      })}
    </section>
  );
}

/** De la primera cita a la última, con una hora de aire por arriba y por abajo. */
function rangoDeHoras(minutos: number[]): number[] {
  if (minutos.length === 0) return [];
  const primera = Math.max(0, Math.floor(Math.min(...minutos) / 60) - 1);
  const ultima = Math.min(23, Math.floor(Math.max(...minutos) / 60) + 1);
  return Array.from({ length: ultima - primera + 1 }, (_, indice) => primera + indice);
}
