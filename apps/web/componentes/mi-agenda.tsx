'use client';

/**
 * El portal del profesional: su día y su ficha.
 *
 * Es **lo contrario del portal del dueño**, y esa diferencia es el encargo: aquí no hay dinero
 * del salón, ni equipo, ni publicidad, ni podio. Hay lo que esta persona necesita para trabajar
 * hoy —a quién atiende, a qué hora y con qué teléfono— y lo que la representa de cara afuera.
 *
 * El teléfono de la clienta **sí sale aquí**, y solo aquí: quien la va a atender puede
 * necesitarlo si se retrasa. En el marketplace no aparece nunca.
 */

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import { Boton } from '@/componentes/boton';
import { Cargando, Roto, Vacio } from '@/componentes/estados';
import { LlevarCita } from '@/componentes/llevar-cita';
import { Seccion } from '@/componentes/piezas';
import { api, comoMensaje, type MiAgenda, type MiPerfilProfesional } from '@/lib/api';
import { conSesion } from '@/lib/sesion';

function hora(cuando: string, zona: string): string {
  return new Intl.DateTimeFormat('es-PA', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: zona }).format(
    new Date(cuando),
  );
}

const ESTADOS: Record<string, string> = {
  pendiente: 'Por confirmar',
  confirmada: 'Confirmada',
  completada: 'Atendida',
  no_show: 'No vino',
  cancelada_cliente: 'La canceló la clienta',
  cancelada_negocio: 'La canceló el salón',
};

/* ── Mi día ───────────────────────────────────────────────────────────────────────────────── */

export function MiDia() {
  const [dia, setDia] = useState(() => new Date().toISOString().slice(0, 10));
  const [agenda, setAgenda] = useState<MiAgenda | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);

  const traer = useCallback(() => {
    setFallo(null);
    setAgenda(null);
    const siguiente = new Date(`${dia}T00:00:00`);
    siguiente.setDate(siguiente.getDate() + 1);
    conSesion((acceso) => api.miAgenda(acceso, `${dia}T00:00:00`, `${siguiente.toISOString().slice(0, 10)}T00:00:00`))
      .then(setAgenda)
      .catch((error) => setFallo(comoMensaje(error)));
  }, [dia]);
  useEffect(traer, [traer]);

  function mover(dias: number) {
    const d = new Date(`${dia}T00:00:00`);
    d.setDate(d.getDate() + dias);
    setDia(d.toISOString().slice(0, 10));
  }

  const hoy = new Date().toISOString().slice(0, 10);
  const vivas = (agenda?.citas ?? []).filter((c) => c.estado === 'confirmada' || c.estado === 'pendiente');

  return (
    <div className="pila">
      {/* Tres días y no un calendario: quien trabaja mira hoy, y de vez en cuando mañana. */}
      <div className="opciones">
        <button type="button" className="opcion" onClick={() => mover(-1)}>
          ← Ayer
        </button>
        <button
          type="button"
          className="opcion"
          data-elegida={dia === hoy ? 'si' : 'no'}
          aria-pressed={dia === hoy}
          onClick={() => setDia(hoy)}
        >
          Hoy
        </button>
        <button type="button" className="opcion" onClick={() => mover(1)}>
          Mañana →
        </button>
      </div>

      <p className="menor tenue">
        {new Intl.DateTimeFormat('es-PA', { weekday: 'long', day: 'numeric', month: 'long' }).format(
          new Date(`${dia}T00:00:00`),
        )}
      </p>

      {fallo ? <Roto mensaje={fallo} accion={<Boton tono="abre" onClick={traer} hijos="Volver a intentarlo" />} /> : null}
      {!agenda && !fallo ? <Cargando que="Cargando tu día" filas={3} /> : null}

      {agenda ? (
        <>
          <ul className="cifras-grandes">
            <li>
              <span className="cifras-grandes__valor">{vivas.length}</span>
              <span className="cifras-grandes__que">citas por atender</span>
            </li>
            <li>
              <span className="cifras-grandes__valor">
                {vivas.reduce((suma, c) => suma + c.duracion_minutos, 0)} min
              </span>
              <span className="cifras-grandes__que">de silla ocupada</span>
            </li>
          </ul>

          {agenda.citas.length === 0 ? (
            <Vacio
              titulo="No tienes nada este día"
              explicacion="Ni citas ni bloqueos. Si esperabas alguna, mira que sea el día correcto."
            />
          ) : (
            <ul className="pila pila--apretada">
              {agenda.citas.map((cita) => (
                <li key={cita.id} className="cita-mia" data-cita={cita.id} data-estado={cita.estado}>
                  <span className="cita-mia__hora cifras">
                    {hora(cita.inicio, agenda.zona_horaria)}
                    <span className="cita-mia__fin">{hora(cita.fin, agenda.zona_horaria)}</span>
                  </span>
                  <span className="pila pila--apretada">
                    <span className="rotulo rotulo--pequeno">{cita.cliente ?? 'Sin nombre'}</span>
                    <span className="menor">{cita.servicios.join(' · ')}</span>
                    <span className="menor tenue">
                      {ESTADOS[cita.estado] ?? cita.estado} · {cita.duracion_minutos} min
                    </span>
                    {cita.nota_del_cliente ? <span className="menor">«{cita.nota_del_cliente}»</span> : null}
                  </span>
                  {/* **El teléfono, solo aquí.** Quien atiende puede necesitarlo si se retrasa;
                      en el marketplace no sale nunca. */}
                  {cita.telefono ? (
                    <a className="boton boton--texto" href={`tel:${cita.telefono}`}>
                      Llamar
                    </a>
                  ) : null}
                  {/* **Su día también se lleva, no solo se mira.** Quien atiende es quien sabe
                      si la clienta vino, y hacerle pedirle al dueño que cierre cada cita es
                      convertir el trabajo de dos en el de tres. */}
                  <LlevarCita citaId={cita.id} estado={cita.estado} inicio={cita.inicio} alCambiar={traer} />
                </li>
              ))}
            </ul>
          )}

          {agenda.bloqueos.length > 0 ? (
            <Seccion titulo="Bloqueos de este día">
              <ul className="pila pila--apretada">
                {agenda.bloqueos.map((b) => (
                  <li key={b.inicio} className="menor tenue">
                    {hora(b.inicio, agenda.zona_horaria)} a {hora(b.fin, agenda.zona_horaria)}
                    {b.motivo ? ` · ${b.motivo}` : ''}
                  </li>
                ))}
              </ul>
            </Seccion>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

/* ── Mi ficha, la que ve la clienta ───────────────────────────────────────────────────────── */

export function MiFicha() {
  const [perfil, setPerfil] = useState<MiPerfilProfesional | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);
  const [guardado, setGuardado] = useState(false);
  const [borrador, setBorrador] = useState<Partial<MiPerfilProfesional>>({});
  /** El salón, para poder enlazar la ficha pública: el perfil trae el nombre, no el slug. */
  const [salon, setSalon] = useState<string | null>(null);

  const traer = useCallback(() => {
    setFallo(null);
    conSesion((acceso) => api.misNegocios(acceso))
      .then((negocios) => setSalon(negocios[0]?.slug ?? null))
      .catch(() => setSalon(null));
    conSesion((acceso) => api.miPerfilProfesional(acceso))
      .then((p) => {
        setPerfil(p);
        setBorrador({
          titular: p.titular ?? '',
          descripcion: p.descripcion ?? '',
          anos_de_experiencia: p.anos_de_experiencia,
          instagram: p.instagram ?? '',
          facebook: p.facebook ?? '',
          x: p.x ?? '',
        });
      })
      .catch((error) => setFallo(comoMensaje(error)));
  }, []);
  useEffect(traer, [traer]);

  async function guardar(evento: React.FormEvent) {
    evento.preventDefault();
    setGuardando(true);
    setGuardado(false);
    setFallo(null);
    try {
      const nuevo = await conSesion((acceso) => api.cambiarMiPerfilProfesional(borrador, acceso));
      setPerfil(nuevo);
      setGuardado(true);
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setGuardando(false);
    }
  }

  if (fallo && !perfil)
    return <Roto mensaje={fallo} accion={<Boton tono="abre" onClick={traer} hijos="Volver a intentarlo" />} />;
  if (!perfil) return <Cargando que="Cargando tu ficha" />;

  return (
    <div className="pila">
      <ul className="cifras-grandes">
        <li>
          <span className="cifras-grandes__valor">{perfil.citas_atendidas}</span>
          <span className="cifras-grandes__que">citas atendidas</span>
        </li>
        <li>
          <span className="cifras-grandes__valor">{perfil.clientes_atendidos}</span>
          <span className="cifras-grandes__que">personas distintas</span>
        </li>
      </ul>

      {perfil.slug && salon ? (
        <p className="menor">
          Así te ven:{' '}
          <Link href={`/salon/${salon}/con/${perfil.slug}`}>tu ficha pública</Link>, con tu nombre, tus años, lo que
          haces y tus reseñas.
        </p>
      ) : null}

      <form className="pila" onSubmit={guardar} noValidate>
        <div className="campo">
          <label className="campo__rotulo" htmlFor="titular">
            Tu oficio en una línea
          </label>
          <input
            className="campo__caja"
            id="titular"
            value={borrador.titular ?? ''}
            onChange={(e) => setBorrador((b) => ({ ...b, titular: e.target.value }))}
            placeholder="Barbero. Fades y perfilado de barba"
            maxLength={120}
          />
        </div>

        <div className="campo">
          <label className="campo__rotulo" htmlFor="descripcion">
            Quién eres
          </label>
          <textarea
            className="campo__caja"
            id="descripcion"
            rows={4}
            maxLength={600}
            value={borrador.descripcion ?? ''}
            onChange={(e) => setBorrador((b) => ({ ...b, descripcion: e.target.value }))}
            placeholder="Dónde aprendiste, qué se te da mejor, cómo trabajas."
          />
        </div>

        <div className="campo">
          <label className="campo__rotulo" htmlFor="anos">
            Años detrás de la silla
          </label>
          <input
            className="campo__caja"
            id="anos"
            type="number"
            min={0}
            max={70}
            value={borrador.anos_de_experiencia ?? ''}
            onChange={(e) =>
              setBorrador((b) => ({ ...b, anos_de_experiencia: e.target.value === '' ? null : Number(e.target.value) }))
            }
          />
        </div>

        <Seccion titulo="Tus redes">
          {/* Solo el usuario, sin la dirección entera: la API compone el enlace, y así nadie
              pega media URL y se queda con un enlace roto en su ficha. */}
          {(
            [
              ['instagram', 'Instagram'],
              ['facebook', 'Facebook'],
              ['x', 'X'],
            ] as const
          ).map(([campo, rotulo]) => (
            <div className="campo" key={campo}>
              <label className="campo__rotulo" htmlFor={campo}>
                {rotulo}
              </label>
              <input
                className="campo__caja"
                id={campo}
                value={(borrador[campo] as string | null) ?? ''}
                onChange={(e) => setBorrador((b) => ({ ...b, [campo]: e.target.value }))}
                placeholder="tu usuario, sin la dirección entera"
              />
            </div>
          ))}
        </Seccion>

        {/* **Salir o no en la búsqueda de personas no lo decide quien trabaja, lo decide el
            salón**: la API solo se lo deja al dueño. La pantalla lo ofrecía igual y al guardar
            contestaba «visible_en_marketplace sobra», que es verdad y desconcierta. Aquí se dice
            cómo está y quién lo cambia. */}
        <p className="bloque relleno menor" role="note">
          {perfil.visible_en_marketplace
            ? 'Ahora mismo sales en la búsqueda de personas del marketplace.'
            : 'Ahora mismo no sales en la búsqueda de personas.'}{' '}
          Eso lo decide quien lleva el salón.
        </p>

        {fallo ? (
          <p className="campo__fallo" role="alert">
            {fallo}
          </p>
        ) : null}
        {guardado ? (
          <p className="bloque bloque--exito relleno" role="status">
            Guardado. Tu ficha pública ya lo dice.
          </p>
        ) : null}

        <Boton tono="cierra" type="submit" cargando={guardando} rotuloCargando="Guardando" hijos="Guardar mi ficha" />
      </form>
    </div>
  );
}
