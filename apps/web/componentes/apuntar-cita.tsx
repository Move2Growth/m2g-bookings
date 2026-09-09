'use client';

/**
 * Apuntar una cita desde el mostrador o por teléfono (AGD-2).
 *
 * **Sin esto el portal del dueño no sirve para trabajar.** En un salón de Panamá la mayoría de
 * las citas no entran por el marketplace: entran por WhatsApp, por una llamada o porque alguien
 * se asoma a la puerta. Una agenda en la que solo aparecen las que vienen de internet obliga a
 * llevar dos agendas —la del programa y la del cuaderno—, y entonces la de verdad es la del
 * cuaderno.
 *
 * Vive **dentro de la agenda del día** y no en otra pantalla, porque una cita de teléfono se
 * apunta mirando el día: la pregunta que hay que contestar al vuelo es «¿tengo hueco a las
 * cinco?», y esa respuesta está detrás de este panel.
 *
 * ## Lo que decide esta pantalla
 *
 * **La hora se escribe, no se elige de una lista de huecos.** Es deliberado y va contra lo que
 * parece más cómodo: el salón puede saltarse su propia antelación mínima —si la persona ya está
 * en la puerta, decirle que vuelva dentro de una hora es absurdo—, así que una lista de huecos
 * «reservables» le escondería justo las horas que necesita. Lo que no se salta es el choque con
 * otra cita, y de eso se encarga la base; aquí se cuenta cuando ocurre.
 *
 * **El cliente rápido no es un atajo, es el caso normal.** Quien llama casi nunca tiene ficha.
 * Se apunta un nombre y, si lo da, un teléfono; la ficha se crea en el salón y no es una cuenta
 * de la plataforma. Si esa persona se registra algún día, su historial ya está ahí.
 *
 * **Se enseña a qué hora termina** en cuanto hay servicios elegidos. Es el único número que
 * decide si la cita cabe, y calcularlo de cabeza sumando tres duraciones es como se pisan dos
 * citas.
 */

import { useEffect, useMemo, useRef, useState } from 'react';

import { Boton } from '@/componentes/boton';
import {
  api,
  comoMensaje,
  type ClienteDelSalon,
  type ProfesionalEnPanel,
  type ServicioDelPanel,
} from '@/lib/api';
import { duracion, hora, precioDeServicio } from '@/lib/formato';
import { conSesion } from '@/lib/sesion';

/**
 * Una fecha para un `datetime-local`, **en la hora del navegador**.
 *
 * Cortar el ISO a lo bruto parece que funciona y es la trampa: el ISO va en UTC y el campo
 * habla en local, así que en Panamá salen cinco horas de diferencia. Ya costó un fallo mudo en
 * la pantalla de mover la hora, donde el `min` mal calculado dejaba el formulario sin enviarse
 * y sin decir nada.
 */
function paraElCampo(cuando: Date): string {
  return new Date(cuando.getTime() - cuando.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export function ApuntarCita({
  dia,
  zona,
  alApuntar,
}: {
  /** El día que se está mirando, `AAAA-MM-DD`. La hora se propone dentro de ese día. */
  dia: string;
  zona: string;
  alApuntar: () => void;
}) {
  const [abierto, setAbierto] = useState(false);
  const [equipo, setEquipo] = useState<ProfesionalEnPanel[] | null>(null);
  const [carta, setCarta] = useState<ServicioDelPanel[] | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [hecha, setHecha] = useState<{ inicio: string; cliente: string } | null>(null);

  const [quien, setQuien] = useState('');
  const [elegidos, setElegidos] = useState<string[]>([]);
  const [cuando, setCuando] = useState('');
  const [nota, setNota] = useState('');

  /* El cliente: o una ficha que ya existe, o un nombre suelto. Nunca las dos. */
  const [buscando, setBuscando] = useState('');
  const [encontrados, setEncontrados] = useState<ClienteDelSalon[] | null>(null);
  const [ficha, setFicha] = useState<ClienteDelSalon | null>(null);
  const [nombre, setNombre] = useState('');
  const [telefono, setTelefono] = useState('');

  const intento = useRef<{ firma: string; clave: string } | null>(null);

  /* El equipo y la carta se piden al abrir, no al cargar la agenda: quien solo mira su día no
     tiene por qué pagar dos peticiones que no va a usar. */
  useEffect(() => {
    if (!abierto || equipo !== null) return;
    let vivo = true;
    (async () => {
      try {
        const [gente, servicios] = await Promise.all([
          conSesion((acceso) => api.profesionalesDelLocal(acceso)),
          conSesion((acceso) => api.serviciosDelLocal(acceso)),
        ]);
        if (!vivo) return;
        setEquipo(gente.filter((persona) => persona.activo));
        setCarta(servicios);
      } catch (error) {
        if (vivo) setFallo(comoMensaje(error));
      }
    })();
    return () => {
      vivo = false;
    };
  }, [abierto, equipo]);

  /* La hora arranca en el día que se está mirando, a las diez. Cambiar de día la vuelve a
     poner: apuntar el martes una cita del lunes es el error que nadie ve hasta el lunes. */
  useEffect(() => {
    if (abierto) setCuando(`${dia}T10:00`);
  }, [abierto, dia]);

  /* Buscar una ficha, con freno: cada tecla no es una consulta. */
  useEffect(() => {
    if (!abierto) return;
    const texto = buscando.trim();
    if (texto.length < 2) {
      setEncontrados(null);
      return;
    }
    const freno = setTimeout(async () => {
      try {
        setEncontrados(await conSesion((acceso) => api.clientesDelLocal(acceso, texto)));
      } catch {
        setEncontrados([]);
      }
    }, 350);
    return () => clearTimeout(freno);
  }, [buscando, abierto]);

  const minutos = useMemo(
    () =>
      (carta ?? [])
        .filter((servicio) => elegidos.includes(servicio.id))
        .reduce((suma, servicio) => suma + servicio.duracion_minutos, 0),
    [carta, elegidos],
  );

  const termina = useMemo(() => {
    if (!cuando || minutos === 0) return null;
    const empieza = new Date(cuando);
    if (Number.isNaN(empieza.getTime())) return null;
    return new Date(empieza.getTime() + minutos * 60000);
  }, [cuando, minutos]);

  const bloqueada = ficha?.bloqueado === true;
  const listo = quien !== '' && elegidos.length > 0 && cuando !== '' && (ficha !== null || nombre.trim() !== '') && !bloqueada;

  function limpiar() {
    setElegidos([]);
    setNota('');
    setFicha(null);
    setBuscando('');
    setEncontrados(null);
    setNombre('');
    setTelefono('');
    intento.current = null;
  }

  /** La clave del **intento**: la misma mientras no cambie nada, nueva en cuanto cambia. */
  function llaveDelIntento(): string {
    const firma = `${quien}|${[...elegidos].sort().join(',')}|${cuando}|${ficha?.id ?? nombre.trim()}`;
    if (intento.current?.firma !== firma) intento.current = { firma, clave: crypto.randomUUID() };
    return intento.current.clave;
  }

  async function apuntar(evento: React.FormEvent) {
    evento.preventDefault();
    if (!listo) return;
    setGuardando(true);
    setFallo(null);
    try {
      const cita = await conSesion((acceso) =>
        api.apuntarCita(
          {
            profesional_id: quien,
            servicios: elegidos,
            // El campo da hora local sin zona; se manda con la del navegador, que es la del
            // salón para quien está de pie dentro de él.
            inicio: new Date(cuando).toISOString(),
            cliente_id: ficha?.id ?? null,
            cliente_nombre: ficha ? null : nombre.trim(),
            cliente_telefono: ficha ? null : telefono.trim() || null,
            nota: nota.trim() || null,
          },
          acceso,
          llaveDelIntento(),
        ),
      );
      setHecha({ inicio: cita.inicio, cliente: cita.cliente ?? nombre.trim() });
      limpiar();
      alApuntar();
    } catch (error) {
      // El intento se olvida al fallar: lo que venga después ya es otra cosa.
      intento.current = null;
      setFallo(comoMensaje(error));
    } finally {
      setGuardando(false);
    }
  }

  if (!abierto) {
    return (
      <p className="seccion--corta">
        <Boton
          tono="abre"
          onClick={() => {
            setAbierto(true);
            setHecha(null);
          }}
          hijos="Apuntar una cita"
        />
      </p>
    );
  }

  return (
    <section className="seccion--corta pila apuntar" aria-label="Apuntar una cita">
      <div className="apuntar__cabeza">
        <span className="etiqueta">Por teléfono o en el mostrador</span>
        <Boton
          tono="texto"
          onClick={() => {
            setAbierto(false);
            limpiar();
            setFallo(null);
          }}
          hijos="Cerrar"
        />
      </div>

      {hecha ? (
        <p className="bloque bloque--exito relleno" role="status">
          Apuntada: {hecha.cliente} a las {hora(hecha.inicio, zona)}.
        </p>
      ) : null}

      {equipo === null || carta === null ? (
        <p className="menor cargando">Abriendo la carta y el equipo…</p>
      ) : (
        <form className="pila" onSubmit={apuntar} noValidate>
          <div className="pila pila--apretada">
            <span className="etiqueta">Quién atiende</span>
            <div className="opciones">
              {equipo.map((persona) => (
                <button
                  key={persona.id}
                  type="button"
                  className="opcion"
                  aria-pressed={quien === persona.id}
                  onClick={() => setQuien(persona.id)}
                >
                  {persona.nombre}
                </button>
              ))}
            </div>
            {equipo.length === 0 ? (
              <p className="menor">No hay nadie activo en el equipo. Añade a alguien antes de apuntar citas.</p>
            ) : null}
          </div>

          <div className="pila pila--apretada">
            <span className="etiqueta">Qué se hace</span>
            <div className="opciones">
              {carta.map((servicio) => (
                <button
                  key={servicio.id}
                  type="button"
                  className="opcion"
                  aria-pressed={elegidos.includes(servicio.id)}
                  onClick={() =>
                    setElegidos((antes) =>
                      antes.includes(servicio.id)
                        ? antes.filter((uno) => uno !== servicio.id)
                        : [...antes, servicio.id],
                    )
                  }
                >
                  {servicio.nombre} · {duracion(servicio.duracion_minutos)} · {precioDeServicio(servicio)}
                </button>
              ))}
            </div>
            {/* El único número que decide si la cita cabe. Sumar tres duraciones de cabeza es
                como se pisan dos citas. */}
            {minutos > 0 ? (
              <p className="menor" role="status">
                {duracion(minutos)} en total
                {termina ? `, termina a las ${hora(termina.toISOString(), zona)}` : ''}.
              </p>
            ) : null}
          </div>

          <div className="campo">
            <label className="campo__rotulo" htmlFor="apuntar-cuando">
              Cuándo
            </label>
            <input
              className="campo__caja campo__caja--hora"
              id="apuntar-cuando"
              type="datetime-local"
              value={cuando}
              onChange={(e) => setCuando(e.target.value)}
            />
            {/* Que el salón pueda apuntar hacia atrás no es un descuido: se apunta lo que ya
                pasó cuando alguien entró sin cita y se atendió. */}
            <p className="campo__pista">
              El salón no tiene antelación mínima: si la persona está en la puerta, se apunta ya.
            </p>
          </div>

          <div className="pila pila--apretada">
            <span className="etiqueta">Para quién</span>
            {ficha ? (
              <p className="tira">
                <span className="ficha-elegida">
                  {ficha.nombre}
                  {ficha.ausencias > 0 ? ` · ${ficha.ausencias} ausencias` : ''}
                </span>
                <Boton tono="texto" onClick={() => setFicha(null)} hijos="Cambiar" />
              </p>
            ) : (
              <>
                <div className="campo">
                  <label className="campo__rotulo" htmlFor="apuntar-buscar">
                    Buscar en tus clientes
                  </label>
                  <input
                    className="campo__caja"
                    id="apuntar-buscar"
                    type="search"
                    value={buscando}
                    placeholder="Nombre o cuatro dígitos del teléfono"
                    onChange={(e) => setBuscando(e.target.value)}
                  />
                </div>
                {encontrados !== null ? (
                  encontrados.length === 0 ? (
                    <p className="menor">Nadie con eso. Apúntalo abajo como cliente nuevo.</p>
                  ) : (
                    <ul className="pila pila--apretada">
                      {encontrados.slice(0, 6).map((cliente) => (
                        <li key={cliente.id}>
                          <button type="button" className="opcion" onClick={() => setFicha(cliente)}>
                            {cliente.nombre}
                            {cliente.completadas > 0 ? ` · ${cliente.completadas} citas` : ' · sin citas'}
                            {cliente.bloqueado ? ' · bloqueado' : ''}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )
                ) : null}

                {/* El caso normal de una llamada: no tiene ficha. Se apunta y ya. */}
                <div className="campo">
                  <label className="campo__rotulo" htmlFor="apuntar-nombre">
                    O apunta a quien llama
                  </label>
                  <input
                    className="campo__caja"
                    id="apuntar-nombre"
                    value={nombre}
                    placeholder="Nombre"
                    onChange={(e) => setNombre(e.target.value)}
                  />
                </div>
                <div className="campo">
                  <label className="campo__rotulo" htmlFor="apuntar-telefono">
                    Su teléfono, si lo da
                  </label>
                  <input
                    className="campo__caja"
                    id="apuntar-telefono"
                    type="tel"
                    inputMode="tel"
                    value={telefono}
                    placeholder="+507 6000-0000"
                    onChange={(e) => setTelefono(e.target.value)}
                  />
                  <p className="campo__pista">Sirve para avisarle si hay que mover la cita.</p>
                </div>
              </>
            )}
            {bloqueada ? (
              <p className="bloque bloque--aviso relleno menor" role="alert">
                Esa persona está bloqueada en tu salón{ficha?.motivo_bloqueo ? `: ${ficha.motivo_bloqueo}` : ''}.
                Quítale el bloqueo desde su ficha si quieres volver a atenderla.
              </p>
            ) : null}
          </div>

          <div className="campo">
            <label className="campo__rotulo" htmlFor="apuntar-nota">
              Una nota, si hace falta
            </label>
            <input
              className="campo__caja"
              id="apuntar-nota"
              value={nota}
              placeholder="Viene con su hija · quiere el mismo color"
              onChange={(e) => setNota(e.target.value)}
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
            bloque
            disabled={!listo}
            cargando={guardando}
            rotuloCargando="Apuntando"
            hijos="Apuntar la cita"
          />
        </form>
      )}
    </section>
  );
}
