'use client';

/**
 * Lo que se puede hacer con una cita desde dentro del salón.
 *
 * Hasta ahora las dos agendas —la del dueño y la del profesional— solo se miraban. Eso es la
 * diferencia entre **ver** la agenda y **llevarla**: el trabajo de verdad es confirmar la que
 * está pendiente, cerrar la que ya se atendió, marcar a quien no vino y mover la que se cambia
 * por teléfono. Todo eso existía en la API desde el principio y no tenía botón.
 *
 * **Qué se puede hacer depende del estado, y no lo decide esta pantalla**: lo decide el dominio
 * —de `pendiente` se confirma o se cancela; de `confirmada` se completa, se marca no-show o se
 * cancela; lo terminal no se toca—. Aquí solo se ofrece lo que existe, para no enseñar un botón
 * que la API va a rechazar.
 *
 * Dos cosas piden confirmación y las dos por el mismo motivo: **no tienen vuelta**. Marcar un
 * no-show le cuenta al cliente para bloquearlo, y cancelar suelta la hora para quien la pida
 * después. Confirmar y completar no preguntan: se hacen cincuenta veces al día.
 */

import { useState } from 'react';

import { Boton } from '@/componentes/boton';
import { api, comoMensaje } from '@/lib/api';
import { conSesion } from '@/lib/sesion';

type Accion = 'confirmada' | 'completada' | 'no_show' | 'cancelada_negocio';

const ROTULO: Record<Accion, string> = {
  confirmada: 'Confirmar',
  completada: 'Atendida',
  no_show: 'No vino',
  cancelada_negocio: 'Cancelar',
};

const HACIENDO: Record<Accion, string> = {
  confirmada: 'Confirmando',
  completada: 'Cerrando',
  no_show: 'Marcando',
  cancelada_negocio: 'Cancelando',
};

/** Lo que el salón puede hacer desde cada estado. Copia la tabla del dominio, no la inventa. */
function acciones(estado: string): Accion[] {
  if (estado === 'pendiente') return ['confirmada', 'cancelada_negocio'];
  if (estado === 'confirmada') return ['completada', 'no_show', 'cancelada_negocio'];
  return [];
}

/** Las que no tienen vuelta y por eso preguntan antes. */
const PREGUNTAN: Accion[] = ['no_show', 'cancelada_negocio'];

const AVISO: Record<string, string> = {
  no_show: 'Marcar que no vino le cuenta a esa clienta, y el salón puede acabar bloqueándola. No se puede deshacer.',
  cancelada_negocio: 'La hora queda libre para quien la pida después, y a la clienta se le avisa. No se puede deshacer.',
};

/**
 * Una fecha para un `datetime-local`: **en la hora del navegador, no en UTC**.
 *
 * Cortar el ISO a lo bruto —`inicio.slice(0, 16)`— parece que funciona y es la trampa: el ISO va
 * en UTC y el campo habla en local, así que en Panamá salían cinco horas de diferencia. Puesto
 * como `min`, el navegador daba por inválida cualquier hora anterior y **el formulario no se
 * enviaba, sin decir nada**: se elegía una hora, se pulsaba «Mover» y no pasaba absolutamente
 * nada. Se cazó mirando que no salía ni una petición.
 */
function paraElCampo(cuando: Date): string {
  return new Date(cuando.getTime() - cuando.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export function LlevarCita({
  citaId,
  estado,
  inicio,
  alCambiar,
}: {
  citaId: string;
  estado: string;
  /** El inicio actual, en ISO. Se usa para proponer el mismo día al mover la hora. */
  inicio: string;
  alCambiar: () => void;
}) {
  const [haciendo, setHaciendo] = useState<Accion | null>(null);
  const [preguntando, setPreguntando] = useState<Accion | null>(null);
  const [moviendo, setMoviendo] = useState(false);
  const [nuevaHora, setNuevaHora] = useState('');
  const [fallo, setFallo] = useState<string | null>(null);

  const posibles = acciones(estado);
  if (posibles.length === 0 && !fallo) return null;

  async function hacer(accion: Accion) {
    setHaciendo(accion);
    setFallo(null);
    try {
      await conSesion((acceso) => api.cambiarEstado(citaId, accion, null, acceso));
      setPreguntando(null);
      alCambiar();
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setHaciendo(null);
    }
  }

  async function mover(evento: React.FormEvent) {
    evento.preventDefault();
    if (!nuevaHora) return;
    // Se dice aquí en vez de dejarlo en manos del `min`, que rechaza en silencio.
    if (new Date(nuevaHora).getTime() < Date.now()) {
      setFallo('Esa hora ya pasó. Elige una por delante.');
      return;
    }
    setMoviendo(true);
    setFallo(null);
    try {
      // El campo da hora local sin zona; se manda con la del navegador, que es la del salón
      // para quien está dentro de él.
      await conSesion((acceso) => api.reprogramarCita(citaId, new Date(nuevaHora).toISOString(), acceso));
      setNuevaHora('');
      alCambiar();
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setMoviendo(false);
    }
  }

  if (preguntando) {
    return (
      <div className="llevar llevar--pregunta" role="group" aria-label="Confirmar la acción">
        <p className="menor">{AVISO[preguntando]}</p>
        <div className="tira">
          <Boton
            tono="riesgo"
            onClick={() => void hacer(preguntando)}
            cargando={haciendo === preguntando}
            rotuloCargando={HACIENDO[preguntando]}
            hijos={`Sí, ${ROTULO[preguntando].toLowerCase()}`}
          />
          <Boton tono="secundario" onClick={() => setPreguntando(null)} hijos="No" />
        </div>
      </div>
    );
  }

  return (
    <div className="llevar">
      <div className="tira">
        {posibles.map((accion) => (
          <Boton
            key={accion}
            tono={accion === 'confirmada' || accion === 'completada' ? 'abre' : 'riesgo-suave'}
            onClick={() => (PREGUNTAN.includes(accion) ? setPreguntando(accion) : void hacer(accion))}
            cargando={haciendo === accion}
            rotuloCargando={HACIENDO[accion]}
            hijos={ROTULO[accion]}
          />
        ))}
      </div>

      {/* Mover la hora es lo que más se hace por teléfono: «¿me la pasas a las cinco?». Va aquí
          y no en otra pantalla porque se decide mirando el día. */}
      {estado === 'confirmada' || estado === 'pendiente' ? (
        <form className="llevar__mover" onSubmit={mover} noValidate>
          <label className="solo-lectores" htmlFor={`mover-${citaId}`}>
            Nueva hora
          </label>
          <input
            className="campo__caja campo__caja--hora"
            id={`mover-${citaId}`}
            type="datetime-local"
            value={nuevaHora}
            /* El suelo es **ahora**, no la hora que tenía: una cita se adelanta tanto como se
               retrasa, y lo único que no se puede es mandarla al pasado. */
            min={paraElCampo(new Date())}
            onChange={(e) => setNuevaHora(e.target.value)}
          />
          <Boton
            tono="secundario"
            type="submit"
            disabled={!nuevaHora}
            cargando={moviendo}
            rotuloCargando="Moviendo"
            hijos="Mover"
          />
        </form>
      ) : null}

      {fallo ? (
        <p className="campo__fallo" role="alert">
          {fallo}
        </p>
      ) : null}
    </div>
  );
}
