'use client';

/**
 * Dejar una reseña, desde la cita que la permite.
 *
 * **Solo puede opinar quien vino de verdad**, y eso no lo decide esta pantalla: lo decide el
 * servidor con `se_puede_resenar`, que mira que la cita esté atendida, dentro del plazo del
 * salón y sin reseña previa. Aquí no se recalcula: dos relojes distintos darían dos respuestas.
 *
 * La nota es obligatoria y el texto no. La mayoría de la gente puntúa y no escribe, y exigir un
 * texto no consigue textos: consigue que no se puntúe.
 *
 * Y se puede puntuar aparte a la persona que atendió, porque un salón puede estar bien y quien
 * te tocó ese día no —o al revés—, y meter las dos cosas en un número las esconde.
 */

import { useState } from 'react';

import { Boton } from '@/componentes/boton';
import { api, comoMensaje, type MiCita } from '@/lib/api';
import { conSesion } from '@/lib/sesion';

const CARAS = [
  [1, 'Muy mal'],
  [2, 'Mal'],
  [3, 'Normal'],
  [4, 'Bien'],
  [5, 'Muy bien'],
] as const;

export function Opinar({ cita, alGuardar }: { cita: MiCita; alGuardar: () => void }) {
  const [nota, setNota] = useState<number | null>(null);
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    if (nota === null) return;
    setEnviando(true);
    setFallo(null);
    try {
      await conSesion((acceso) => api.opinar(cita.id, { nota, texto: texto.trim() || null }, acceso));
      alGuardar();
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="bloque relleno pila pila--apretada" onSubmit={enviar} noValidate>
      <p className="rotulo rotulo--pequeno">¿Qué tal fue en {cita.negocio}?</p>

      <fieldset className="campo">
        <legend className="campo__rotulo">Tu nota</legend>
        <div className="opciones">
          {CARAS.map(([valor, rotulo]) => (
            <button
              key={valor}
              type="button"
              className="opcion"
              data-elegida={nota === valor ? 'si' : 'no'}
              aria-pressed={nota === valor}
              onClick={() => setNota(valor)}
            >
              <span className="cifras">{valor}</span> · {rotulo}
            </button>
          ))}
        </div>
      </fieldset>

      <div className="campo">
        <label className="campo__rotulo" htmlFor={`texto-${cita.id}`}>
          Y si quieres, cuéntalo
        </label>
        <textarea
          className="campo__caja"
          id={`texto-${cita.id}`}
          rows={3}
          maxLength={1000}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Qué te hicieron, qué tal te trataron, si volverías."
        />
        <p className="campo__pista">Opcional. Con la nota basta.</p>
      </div>

      {fallo ? (
        <p className="campo__fallo" role="alert">
          {fallo}
        </p>
      ) : null}

      <Boton
        tono="cierra"
        type="submit"
        cargando={enviando}
        rotuloCargando="Enviando"
        disabled={nota === null}
        hijos={nota === null ? 'Elige una nota' : 'Enviar mi opinión'}
      />
    </form>
  );
}
