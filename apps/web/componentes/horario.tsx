'use client';

/**
 * El horario del salón, el de cada persona, y los ratos bloqueados.
 *
 * Las tres cosas viven en la misma pantalla porque son la misma pregunta —**cuándo se puede
 * reservar aquí**— hecha a tres escalas: la semana del local, la semana de quien atiende, y el
 * jueves que alguien no viene. Repartirlas en tres sitios obliga a cruzarlas de cabeza.
 *
 * Y un aviso que va escrito y no en la cabeza de nadie: **cambiar el horario no cancela las
 * citas que se queden fuera**. Es una decisión del motor, no un descuido: que un cambio de
 * horario cancelara citas en silencio sería la peor sorpresa posible un lunes por la mañana. Lo
 * que hace la pantalla es decirlo.
 */

import { useCallback, useEffect, useState } from 'react';

import { Boton } from '@/componentes/boton';
import { Cargando, Roto, Vacio } from '@/componentes/estados';
import { Seccion } from '@/componentes/piezas';
import {
  api,
  comoMensaje,
  type Ausencia,
  type ProfesionalEnPanel,
  type TramoDeHorario,
  type TramoDelProfesional,
} from '@/lib/api';
import { conSesion } from '@/lib/sesion';

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

/** `09:00:00` → `09:00`, que es lo que entiende un `input[type=time]`. */
const corta = (hora: string) => hora.slice(0, 5);

export function Horario() {
  const [quien, setQuien] = useState<'salon' | string>('salon');
  const [equipo, setEquipo] = useState<ProfesionalEnPanel[] | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);

  useEffect(() => {
    conSesion((acceso) => api.profesionalesDelLocal(acceso))
      .then((gente) => setEquipo(gente.filter((p) => p.activo)))
      .catch((error) => setFallo(comoMensaje(error)));
  }, []);

  return (
    <div className="pila">
      <p className="parrafo">
        Aquí se decide cuándo se puede reservar. <strong>Cambiar el horario no toca las citas que
        ya están cogidas</strong>, aunque queden fuera: eso lo decides tú mirándolas, no lo decide
        el sistema por su cuenta.
      </p>

      {/* Un solo carril para elegir de quién es el horario: el del local o el de alguien. */}
      <div className="opciones">
        <button
          type="button"
          className="opcion"
          data-elegida={quien === 'salon' ? 'si' : 'no'}
          aria-pressed={quien === 'salon'}
          onClick={() => setQuien('salon')}
        >
          Todo el local
        </button>
        {(equipo ?? []).map((persona) => (
          <button
            key={persona.id}
            type="button"
            className="opcion"
            data-elegida={quien === persona.id ? 'si' : 'no'}
            aria-pressed={quien === persona.id}
            onClick={() => setQuien(persona.id)}
          >
            {persona.nombre}
          </button>
        ))}
      </div>

      {fallo ? <Roto mensaje={fallo} /> : null}

      {quien === 'salon' ? <HorarioDelSalon /> : <HorarioDeLaPersona profesionalId={quien} />}

      <Bloqueos equipo={equipo ?? []} />
    </div>
  );
}

/* ── La semana del local ──────────────────────────────────────────────────────────────────── */

type DiaAbierto = { abre: string; cierra: string } | null;

function HorarioDelSalon() {
  const [semana, setSemana] = useState<Record<number, DiaAbierto> | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [guardado, setGuardado] = useState(false);

  const traer = useCallback(() => {
    setFallo(null);
    conSesion((acceso) => api.horarioDelSalon(acceso))
      .then((tramos) => {
        const mapa: Record<number, DiaAbierto> = {};
        for (let dia = 0; dia < 7; dia++) mapa[dia] = null;
        for (const tramo of tramos as unknown as { dia: number; abre: string; cierra: string }[]) {
          mapa[tramo.dia] = { abre: corta(tramo.abre), cierra: corta(tramo.cierra) };
        }
        setSemana(mapa);
      })
      .catch((error) => setFallo(comoMensaje(error)));
  }, []);
  useEffect(traer, [traer]);

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    if (!semana) return;
    setGuardando(true);
    setGuardado(false);
    setFallo(null);
    try {
      const tramos = Object.entries(semana)
        .filter(([, t]) => t !== null)
        .map(([dia, t]) => ({ dia: Number(dia), abre: `${t!.abre}:00`, cierra: `${t!.cierra}:00` }));
      await conSesion((acceso) => api.ponerHorario(tramos as unknown as TramoDeHorario[], acceso));
      setGuardado(true);
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setGuardando(false);
    }
  }

  if (fallo && !semana) return <Roto mensaje={fallo} accion={<Boton tono="abre" onClick={traer} hijos="Reintentar" />} />;
  if (!semana) return <Cargando que="Cargando el horario" filas={4} />;

  return (
    <Seccion titulo="Cuándo abre el local">
      <form className="pila" onSubmit={guardar}>
        <ul className="pila pila--apretada">
          {DIAS.map((nombre, dia) => (
            <FilaDeDia
              key={nombre}
              nombre={nombre}
              tramo={semana[dia]}
              alCambiar={(t) => setSemana((s) => ({ ...s!, [dia]: t }))}
            />
          ))}
        </ul>
        {fallo ? (
          <p className="campo__fallo" role="alert">
            {fallo}
          </p>
        ) : null}
        {guardado ? (
          <p className="bloque bloque--exito relleno" role="status">
            Guardado. Las horas nuevas ya se ofrecen.
          </p>
        ) : null}
        <Boton tono="cierra" type="submit" cargando={guardando} rotuloCargando="Guardando" hijos="Guardar el horario" />
      </form>
    </Seccion>
  );
}

/** Una fila: el día con su casilla y, si abre, sus dos horas. */
function FilaDeDia({
  nombre,
  tramo,
  alCambiar,
}: {
  nombre: string;
  tramo: DiaAbierto;
  alCambiar: (tramo: DiaAbierto) => void;
}) {
  return (
    <li className="horario__fila">
      <label className="horario__dia">
        <input
          type="checkbox"
          checked={tramo !== null}
          onChange={(e) => alCambiar(e.target.checked ? { abre: '09:00', cierra: '18:00' } : null)}
        />
        <span>{nombre}</span>
      </label>
      {tramo ? (
        <span className="horario__horas">
          <input
            className="campo__caja campo__caja--hora"
            type="time"
            value={tramo.abre}
            aria-label={`${nombre}, abre`}
            onChange={(e) => alCambiar({ ...tramo, abre: e.target.value })}
          />
          <span aria-hidden="true">a</span>
          <input
            className="campo__caja campo__caja--hora"
            type="time"
            value={tramo.cierra}
            aria-label={`${nombre}, cierra`}
            onChange={(e) => alCambiar({ ...tramo, cierra: e.target.value })}
          />
        </span>
      ) : (
        <span className="tenue">Cerrado</span>
      )}
    </li>
  );
}

/* ── La semana de una persona ─────────────────────────────────────────────────────────────── */

function HorarioDeLaPersona({ profesionalId }: { profesionalId: string }) {
  const [tramos, setTramos] = useState<TramoDelProfesional[] | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [guardado, setGuardado] = useState(false);

  const traer = useCallback(() => {
    setFallo(null);
    setTramos(null);
    conSesion((acceso) => api.horarioDeLaPersona(profesionalId, acceso))
      .then(setTramos)
      .catch((error) => setFallo(comoMensaje(error)));
  }, [profesionalId]);
  useEffect(traer, [traer]);

  function cambiar(indice: number, campo: 'desde' | 'hasta', valor: string) {
    setTramos((lista) => (lista ?? []).map((t, i) => (i === indice ? { ...t, [campo]: `${valor}:00` } : t)));
  }

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    if (!tramos) return;
    setGuardando(true);
    setGuardado(false);
    setFallo(null);
    try {
      await conSesion((acceso) => api.ponerHorarioDeLaPersona(profesionalId, tramos, acceso));
      setGuardado(true);
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setGuardando(false);
    }
  }

  if (fallo && !tramos) return <Roto mensaje={fallo} accion={<Boton tono="abre" onClick={traer} hijos="Reintentar" />} />;
  if (!tramos) return <Cargando que="Cargando su horario" filas={4} />;

  return (
    <Seccion titulo="Su jornada">
      {tramos.length === 0 ? (
        <Vacio
          titulo="No tiene jornada puesta"
          explicacion="Sin jornada no se le puede reservar nada. La jornada se le pone al darla de alta en el equipo."
        />
      ) : (
        <form className="pila" onSubmit={guardar}>
          {/* Se enseñan los tramos tal cual vienen —trabajo y descanso— porque el almuerzo es un
              tramo de verdad y esconderlo hace que las horas del mediodía parezcan un fallo. */}
          <ul className="pila pila--apretada">
            {tramos.map((tramo, indice) => (
              <li key={`${tramo.dia}-${tramo.clase}-${indice}`} className="horario__fila">
                <span className="horario__dia">
                  {DIAS[tramo.dia]}
                  <span className="sello sello--apagado">{tramo.clase}</span>
                </span>
                <span className="horario__horas">
                  <input
                    className="campo__caja campo__caja--hora"
                    type="time"
                    value={corta(tramo.desde)}
                    aria-label={`${DIAS[tramo.dia]}, ${tramo.clase}, desde`}
                    onChange={(e) => cambiar(indice, 'desde', e.target.value)}
                  />
                  <span aria-hidden="true">a</span>
                  <input
                    className="campo__caja campo__caja--hora"
                    type="time"
                    value={corta(tramo.hasta)}
                    aria-label={`${DIAS[tramo.dia]}, ${tramo.clase}, hasta`}
                    onChange={(e) => cambiar(indice, 'hasta', e.target.value)}
                  />
                </span>
              </li>
            ))}
          </ul>
          {fallo ? (
            <p className="campo__fallo" role="alert">
              {fallo}
            </p>
          ) : null}
          {guardado ? (
            <p className="bloque bloque--exito relleno" role="status">
              Guardado.
            </p>
          ) : null}
          <Boton tono="cierra" type="submit" cargando={guardando} rotuloCargando="Guardando" hijos="Guardar su jornada" />
        </form>
      )}
    </Seccion>
  );
}

/* ── Bloquear un rato ─────────────────────────────────────────────────────────────────────── */

function Bloqueos({ equipo }: { equipo: ProfesionalEnPanel[] }) {
  const [lista, setLista] = useState<Ausencia[] | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [quien, setQuien] = useState('');
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const [motivo, setMotivo] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [levantando, setLevantando] = useState<string | null>(null);

  const traer = useCallback(() => {
    setFallo(null);
    const hoy = new Date();
    const dentro = new Date(hoy.getTime() + 60 * 86400e3);
    conSesion((acceso) => api.ausencias(acceso, hoy.toISOString(), dentro.toISOString()))
      .then(setLista)
      .catch((error) => setFallo(comoMensaje(error)));
  }, []);
  useEffect(traer, [traer]);

  async function bloquear(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setFallo(null);
    try {
      await conSesion((acceso) =>
        api.bloquear(
          {
            desde: new Date(desde).toISOString(),
            hasta: new Date(hasta).toISOString(),
            motivo: motivo.trim() || null,
            profesional_id: quien || null,
          },
          acceso,
        ),
      );
      setDesde('');
      setHasta('');
      setMotivo('');
      traer();
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setEnviando(false);
    }
  }

  async function levantar(ausencia: Ausencia) {
    setLevantando(ausencia.id);
    try {
      await conSesion((acceso) => api.levantarBloqueo(ausencia.id, acceso));
      traer();
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setLevantando(null);
    }
  }

  return (
    <Seccion titulo="Ratos bloqueados">
      <p className="menor tenue">
        Un curso, una tarde libre, vacaciones. Sin nadie elegido se bloquea a <strong>todo el
        equipo</strong>, que es como se cierra el salón un día. Si dentro del rato ya hay citas,{' '}
        <strong>no se bloquea nada</strong> y se dice cuántas son: primero se mueven.
      </p>

      <form className="pila" onSubmit={bloquear}>
        <div className="campo">
          <label className="campo__rotulo" htmlFor="quien-bloqueo">
            A quién
          </label>
          <select
            className="campo__caja"
            id="quien-bloqueo"
            value={quien}
            onChange={(e) => setQuien(e.target.value)}
          >
            <option value="">Todo el equipo</option>
            {equipo.map((persona) => (
              <option key={persona.id} value={persona.id}>
                {persona.nombre}
              </option>
            ))}
          </select>
        </div>

        <div className="campo">
          <label className="campo__rotulo" htmlFor="desde-bloqueo">
            Desde
          </label>
          <input
            className="campo__caja campo__caja--hora"
            id="desde-bloqueo"
            type="datetime-local"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
          />
        </div>

        <div className="campo">
          <label className="campo__rotulo" htmlFor="hasta-bloqueo">
            Hasta
          </label>
          <input
            className="campo__caja campo__caja--hora"
            id="hasta-bloqueo"
            type="datetime-local"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
          />
        </div>

        <div className="campo">
          <label className="campo__rotulo" htmlFor="motivo-bloqueo">
            Por qué (opcional)
          </label>
          <input
            className="campo__caja"
            id="motivo-bloqueo"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            placeholder="Curso de colorimetría"
          />
        </div>

        {fallo ? (
          <p className="campo__fallo" role="alert">
            {fallo}
          </p>
        ) : null}

        <Boton
          tono="cierra"
          type="submit"
          disabled={!desde || !hasta}
          cargando={enviando}
          rotuloCargando="Bloqueando"
          hijos="Bloquear ese rato"
        />
      </form>

      {!lista ? <Cargando que="Buscando bloqueos" filas={2} /> : null}
      {lista && lista.length === 0 ? (
        <p className="menor tenue">No hay ningún rato bloqueado en los próximos dos meses.</p>
      ) : null}
      {lista && lista.length > 0 ? (
        <ul className="pila pila--apretada">
          {lista.map((ausencia) => (
            <li key={ausencia.id} className="ficha-persona">
              <div className="pila pila--apretada">
                <p className="rotulo rotulo--pequeno">{ausencia.profesional}</p>
                <p className="menor tenue">
                  {new Intl.DateTimeFormat('es-PA', { dateStyle: 'medium', timeStyle: 'short' }).format(
                    new Date(ausencia.desde),
                  )}{' '}
                  a{' '}
                  {new Intl.DateTimeFormat('es-PA', { timeStyle: 'short' }).format(new Date(ausencia.hasta))}
                  {ausencia.motivo ? ` · ${ausencia.motivo}` : ''}
                </p>
              </div>
              <div className="ficha-persona__acciones">
                <Boton
                  tono="secundario"
                  onClick={() => void levantar(ausencia)}
                  cargando={levantando === ausencia.id}
                  rotuloCargando="Levantando"
                  hijos="Levantar"
                />
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </Seccion>
  );
}
