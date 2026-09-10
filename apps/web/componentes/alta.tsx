'use client';

/**
 * El alta de un local, en tres pasos (encargo §4).
 *
 * Tres pasos y no un formulario largo, por una razón que se ve en cuanto alguien lo usa de pie
 * en su salón: **cada paso guarda al terminarlo**. Si el teléfono se queda sin batería en el
 * tercero, el local existe y la gente está invitada; solo faltan los servicios, y se sigue
 * desde donde se quedó.
 *
 * El paso de las personas **se salta**. Un salón de una persona es el caso normal en Panamá y
 * obligar a invitar a alguien para poder seguir es pedirle a la dueña que se invite a sí misma.
 *
 * Y el precio del servicio es **opcional**: hay servicios cuyo precio no se sabe de antemano —un
 * color, un tratamiento— y obligar a poner uno hace que se invente. Por eso «A consultar» es una
 * opción de primera y no una casilla escondida.
 */

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

import { Boton } from '@/componentes/boton';
import { SubirFoto } from '@/componentes/subir-foto';
import { Seccion } from '@/componentes/piezas';
import { api, comoMensaje, type CategoriaGlobal, type Checklist, type TramoDeHorario } from '@/lib/api';
import { conSesion, guardarSesion, leerSesion } from '@/lib/sesion';

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

/** El centro de Ciudad de Panamá. Es un punto de partida honesto mientras no hay mapa aquí. */
const PANAMA = { latitud: 8.9824, longitud: -79.5199 };

type Paso = 1 | 2 | 3 | 4;

export function AltaDeLocal() {
  const router = useRouter();
  const [paso, setPaso] = useState<Paso>(1);
  const [creado, setCreado] = useState<{ id: string; slug: string } | null>(null);
  const [sinSesion, setSinSesion] = useState(false);

  useEffect(() => {
    if (!leerSesion()) setSinSesion(true);
  }, []);

  if (sinSesion) {
    return (
      <div className="contenido" data-superficie="local">
        <div className="seccion pila aparece">
          <span className="etiqueta">Dar de alta un local</span>
          <h1 className="rotulo rotulo--grande">Primero entra con tu cuenta.</h1>
          <p className="parrafo">
            El local queda a tu nombre, así que hace falta saber quién eres. Si no tienes cuenta, se crea al entrar.
          </p>
          <Link className="boton boton--abre" href={`/entrar?volver=${encodeURIComponent('/local/alta')}`}>
            Entrar y seguir
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="contenido" data-superficie="local">
      <div className="seccion pila aparece">
        <span className="etiqueta">Dar de alta un local</span>
        {paso < 4 ? (
          <>
            <h1 className="rotulo rotulo--grande">
              {paso === 1 ? 'Tu local.' : paso === 2 ? '¿Trabaja alguien contigo?' : '¿Qué ofreces?'}
            </h1>
            {/* El paso se dice con palabras. Tres bolitas no le dicen a nadie cuánto falta. */}
            <p className="parrafo">
              Paso {paso} de 3 · {paso === 1 ? 'el local' : paso === 2 ? 'las personas' : 'los servicios'}
            </p>
          </>
        ) : null}

        {paso === 1 ? (
          <PasoDelLocal
            alTerminar={(local) => {
              setCreado(local);
              setPaso(2);
            }}
          />
        ) : null}
        {paso === 2 ? <PasoDeLasPersonas alSeguir={() => setPaso(3)} /> : null}
        {paso === 3 ? <PasoDeLosServicios alSeguir={() => setPaso(4)} /> : null}
        {paso === 4 && creado ? <Final slug={creado.slug} alPanel={() => router.push('/local')} /> : null}
      </div>
    </div>
  );
}

/* ── Paso 1 · El local ────────────────────────────────────────────────────────────────────── */

function PasoDelLocal({ alTerminar }: { alTerminar: (local: { id: string; slug: string }) => void }) {
  const [categorias, setCategorias] = useState<CategoriaGlobal[] | null>(null);
  const [nombre, setNombre] = useState('');
  const [categoria, setCategoria] = useState('');
  const [direccion, setDireccion] = useState('');
  const [horario, setHorario] = useState<Record<number, { abre: string; cierra: string } | null>>({
    0: { abre: '09:00', cierra: '18:00' },
    1: { abre: '09:00', cierra: '18:00' },
    2: { abre: '09:00', cierra: '18:00' },
    3: { abre: '09:00', cierra: '18:00' },
    4: { abre: '09:00', cierra: '18:00' },
    5: { abre: '09:00', cierra: '14:00' },
    6: null,
  });
  const [enviando, setEnviando] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);

  useEffect(() => {
    api
      .categorias()
      .then((lista) => {
        setCategorias(lista);
        setCategoria((actual) => actual || lista[0]?.slug || '');
      })
      .catch((error) => setFallo(comoMensaje(error)));
  }, []);

  async function crear(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setFallo(null);
    try {
      const local = await conSesion((acceso) =>
        api.crearNegocio({ nombre: nombre.trim(), categoria, direccion: direccion.trim(), ...PANAMA }, acceso),
      );
      // **Se entra en modo salón aquí mismo.** Los pasos dos y tres tocan la agenda de un
      // negocio concreto: sin esto irían al salón anterior de esta persona, si tenía otro.
      const enModo = await conSesion((acceso) => api.modoNegocio(local.id, acceso));
      guardarSesion(enModo);

      const tramos: TramoDeHorario[] = Object.entries(horario)
        .filter(([, t]) => t !== null)
        .map(([dia, t]) => ({ dia: Number(dia), abre: `${t!.abre}:00`, cierra: `${t!.cierra}:00` }));
      await conSesion((acceso) => api.ponerHorario(tramos, acceso));

      alTerminar({ id: local.id, slug: local.slug });
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="pila" onSubmit={crear} noValidate>
      <div className="campo">
        <label className="campo__rotulo" htmlFor="nombre">
          Cómo se llama
        </label>
        <input
          className="campo__caja"
          id="nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Barbería El Cangrejo"
          required
          minLength={2}
        />
      </div>

      <div className="campo">
        <label className="campo__rotulo" htmlFor="categoria">
          A qué se dedica
        </label>
        <select
          className="campo__caja"
          id="categoria"
          value={categoria}
          onChange={(e) => setCategoria(e.target.value)}
          disabled={!categorias}
        >
          {(categorias ?? []).map((c) => (
            <option key={c.slug} value={c.slug}>
              {c.nombre}
            </option>
          ))}
        </select>
      </div>

      <div className="campo">
        <label className="campo__rotulo" htmlFor="direccion">
          Dónde está
        </label>
        <input
          className="campo__caja"
          id="direccion"
          value={direccion}
          onChange={(e) => setDireccion(e.target.value)}
          placeholder="Calle 47 con Vía Argentina, El Cangrejo"
          required
        />
        <p className="campo__pista">
          El punto en el mapa se coloca en el centro de la ciudad y se afina después: pedirte coordenadas ahora sería
          pedirte que sepas las tuyas.
        </p>
      </div>

      <Seccion titulo="Cuándo abres">
        <ul className="pila pila--apretada">
          {DIAS.map((nombreDia, dia) => {
            const tramo = horario[dia];
            return (
              <li key={nombreDia} className="horario__fila">
                <label className="horario__dia">
                  <input
                    type="checkbox"
                    checked={tramo !== null}
                    onChange={(e) =>
                      setHorario((h) => ({ ...h, [dia]: e.target.checked ? { abre: '09:00', cierra: '18:00' } : null }))
                    }
                  />
                  <span>{nombreDia}</span>
                </label>
                {tramo ? (
                  <span className="horario__horas">
                    <input
                      className="campo__caja campo__caja--hora"
                      type="time"
                      value={tramo.abre}
                      aria-label={`${nombreDia}, abre`}
                      onChange={(e) => setHorario((h) => ({ ...h, [dia]: { ...tramo, abre: e.target.value } }))}
                    />
                    <span aria-hidden="true">a</span>
                    <input
                      className="campo__caja campo__caja--hora"
                      type="time"
                      value={tramo.cierra}
                      aria-label={`${nombreDia}, cierra`}
                      onChange={(e) => setHorario((h) => ({ ...h, [dia]: { ...tramo, cierra: e.target.value } }))}
                    />
                  </span>
                ) : (
                  <span className="tenue">Cerrado</span>
                )}
              </li>
            );
          })}
        </ul>
      </Seccion>

      {fallo ? (
        <p className="campo__fallo" role="alert">
          {fallo}
        </p>
      ) : null}

      <Boton
        tono="cierra"
        bloque
        type="submit"
        cargando={enviando}
        rotuloCargando="Creando el local"
        disabled={!categoria || !nombre.trim() || !direccion.trim()}
        hijos={categorias ? 'Crear el local y seguir' : 'Cargando el catálogo…'}
      />
    </form>
  );
}

/* ── Paso 2 · Las personas ────────────────────────────────────────────────────────────────── */

function PasoDeLasPersonas({ alSeguir }: { alSeguir: () => void }) {
  const [correo, setCorreo] = useState('');
  const [rol, setRol] = useState<'profesional' | 'dueno'>('profesional');
  const [invitadas, setInvitadas] = useState<{ correo: string; rol: string; enlace: string | null }[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);
  const caja = useRef<HTMLInputElement>(null);

  async function invitar(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setFallo(null);
    try {
      const creada = await conSesion((acceso) => api.invitar({ correo: correo.trim(), rol }, acceso));
      setInvitadas((previas) => [...previas, { correo: correo.trim(), rol, enlace: creada.enlace_de_desarrollo }]);
      setCorreo('');
      caja.current?.focus();
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="pila">
      <p className="parrafo">
        Quien trabaje contigo entra con su propio correo y ve lo que le toca. <strong>Si trabajas sola, salta este
        paso</strong>: no hace falta invitar a nadie.
      </p>

      <form className="pila" onSubmit={invitar} noValidate>
        <div className="campo">
          <label className="campo__rotulo" htmlFor="correo-invitado">
            Su correo
          </label>
          <input
            className="campo__caja"
            id="correo-invitado"
            type="email"
            ref={caja}
            value={correo}
            onChange={(e) => setCorreo(e.target.value)}
            placeholder="nombre@correo.com"
          />
        </div>

        <fieldset className="campo">
          <legend className="campo__rotulo">Qué papel tiene</legend>
          <div className="opciones">
            <button
              type="button"
              className="opcion"
              data-elegida={rol === 'profesional' ? 'si' : 'no'}
              aria-pressed={rol === 'profesional'}
              onClick={() => setRol('profesional')}
            >
              Profesional
            </button>
            <button
              type="button"
              className="opcion"
              data-elegida={rol === 'dueno' ? 'si' : 'no'}
              aria-pressed={rol === 'dueno'}
              onClick={() => setRol('dueno')}
            >
              Dueño
            </button>
          </div>
          <p className="campo__pista">
            {rol === 'profesional'
              ? 'Ve su propia agenda y su horario, nada más.'
              : 'Ve y cambia todo el local, como tú.'}
          </p>
        </fieldset>

        {fallo ? (
          <p className="campo__fallo" role="alert">
            {fallo}
          </p>
        ) : null}

        <Boton tono="abre" type="submit" cargando={enviando} rotuloCargando="Invitando" disabled={!correo.trim()} hijos="Invitar" />
      </form>

      {invitadas.length > 0 ? (
        <Seccion titulo={`Invitadas (${invitadas.length})`}>
          <ul className="pila pila--apretada">
            {invitadas.map((i) => (
              <li key={i.correo} className="bloque bloque--exito relleno">
                <p>
                  <strong>{i.correo}</strong> · {i.rol === 'dueno' ? 'dueño' : 'profesional'}
                </p>
                {/* En local no hay correo de verdad: el enlace se enseña aquí y se dice por qué. */}
                {i.enlace ? (
                  <p className="tenue">
                    Todavía no hay proveedor de correo, así que el enlace no sale de aquí:{' '}
                    <a href={i.enlace}>{i.enlace}</a>
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        </Seccion>
      ) : null}

      <div className="tira">
        <Boton
          tono="cierra"
          onClick={alSeguir}
          hijos={invitadas.length > 0 ? 'Seguir con los servicios' : 'Trabajo sola, seguir'}
        />
      </div>
    </div>
  );
}

/* ── Paso 3 · Los servicios ───────────────────────────────────────────────────────────────── */

function PasoDeLosServicios({ alSeguir }: { alSeguir: () => void }) {
  const [categorias, setCategorias] = useState<CategoriaGlobal[] | null>(null);
  const [nombre, setNombre] = useState('');
  const [categoria, setCategoria] = useState('');
  const [duracion, setDuracion] = useState(30);
  const [tipo, setTipo] = useState<'fijo' | 'desde' | 'consultar'>('fijo');
  const [precio, setPrecio] = useState('');
  const [creados, setCreados] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [fallo, setFallo] = useState<string | null>(null);

  useEffect(() => {
    api
      .categorias()
      .then((lista) => {
        setCategorias(lista);
        setCategoria((actual) => actual || lista[0]?.slug || '');
      })
      .catch((error) => setFallo(comoMensaje(error)));
  }, []);

  async function crear(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setFallo(null);
    try {
      await conSesion((acceso) =>
        api.crearServicio(
          {
            nombre: nombre.trim(),
            categoria,
            duracion_minutos: duracion,
            tipo_de_precio: tipo,
            // «A consultar» va sin importe **y la API lo exige así**: mandar un precio con
            // «consultar» es lo que antes devolvía un 500 en vez de una frase.
            precio_centavos: tipo === 'consultar' ? null : Math.round(Number(precio.replace(',', '.')) * 100),
          },
          acceso,
        ),
      );
      setCreados((previos) => [...previos, nombre.trim()]);
      setNombre('');
      setPrecio('');
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="pila">
      <form className="pila" onSubmit={crear} noValidate>
        <div className="campo">
          <label className="campo__rotulo" htmlFor="servicio">
            Cómo se llama
          </label>
          <input
            className="campo__caja"
            id="servicio"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            placeholder="Corte clásico"
            required
          />
        </div>

        <div className="campo">
          <label className="campo__rotulo" htmlFor="categoria-servicio">
            De qué tipo
          </label>
          <select
            className="campo__caja"
            id="categoria-servicio"
            value={categoria}
            onChange={(e) => setCategoria(e.target.value)}
            disabled={!categorias}
          >
            {(categorias ?? []).map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.nombre}
              </option>
            ))}
          </select>
        </div>

        <div className="campo">
          <label className="campo__rotulo" htmlFor="duracion">
            Cuánto dura
          </label>
          <select
            className="campo__caja"
            id="duracion"
            value={duracion}
            onChange={(e) => setDuracion(Number(e.target.value))}
          >
            {[15, 20, 30, 45, 60, 90, 120, 180].map((m) => (
              <option key={m} value={m}>
                {m < 60 ? `${m} min` : `${m / 60} h${m % 60 ? ` ${m % 60} min` : ''}`}
              </option>
            ))}
          </select>
        </div>

        <fieldset className="campo">
          <legend className="campo__rotulo">Cuánto cuesta</legend>
          <div className="opciones">
            {(
              [
                ['fijo', 'Precio fijo'],
                ['desde', 'Desde'],
                ['consultar', 'A consultar'],
              ] as const
            ).map(([valor, rotulo]) => (
              <button
                key={valor}
                type="button"
                className="opcion"
                data-elegida={tipo === valor ? 'si' : 'no'}
                aria-pressed={tipo === valor}
                onClick={() => setTipo(valor)}
              >
                {rotulo}
              </button>
            ))}
          </div>
          {tipo === 'consultar' ? (
            <p className="campo__pista">
              Sale en la carta sin importe. Es lo honesto cuando el precio depende del pelo que tenga delante.
            </p>
          ) : (
            <input
              className="campo__caja"
              inputMode="decimal"
              value={precio}
              onChange={(e) => setPrecio(e.target.value)}
              placeholder="12.00"
              aria-label="Importe en dólares"
              required
            />
          )}
        </fieldset>

        {fallo ? (
          <p className="campo__fallo" role="alert">
            {fallo}
          </p>
        ) : null}

        <Boton
          tono="abre"
          type="submit"
          cargando={enviando}
          rotuloCargando="Guardando"
          disabled={!nombre.trim() || !categoria || (tipo !== 'consultar' && !precio.trim())}
          hijos={categorias ? 'Añadir servicio' : 'Cargando el catálogo…'}
        />
      </form>

      {creados.length > 0 ? (
        <Seccion titulo={`En tu carta (${creados.length})`}>
          <ul className="pila pila--apretada">
            {creados.map((s) => (
              <li key={s} className="bloque bloque--exito relleno">
                {s}
              </li>
            ))}
          </ul>
        </Seccion>
      ) : null}

      <Boton
        tono="cierra"
        bloque
        onClick={alSeguir}
        disabled={creados.length === 0}
        hijos={creados.length === 0 ? 'Añade al menos un servicio' : 'Terminar'}
      />
    </div>
  );
}

/* ── Paso 4 · Qué falta para que lo vea alguien ───────────────────────────────────────────── */

function Final({ slug, alPanel }: { slug: string; alPanel: () => void }) {
  const [checklist, setChecklist] = useState<Checklist | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [publicando, setPublicando] = useState(false);
  const [publicado, setPublicado] = useState(false);

  /** Se vuelve a mirar al subir la foto: es lo que enciende el botón de publicar. */
  const mirarChecklist = useCallback(() => {
    conSesion((acceso) => api.checklist(acceso))
      .then(setChecklist)
      .catch((error) => setFallo(comoMensaje(error)));
  }, []);

  useEffect(mirarChecklist, [mirarChecklist]);

  async function publicar() {
    setPublicando(true);
    setFallo(null);
    try {
      await conSesion((acceso) => api.publicar(acceso));
      setPublicado(true);
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setPublicando(false);
    }
  }

  const puntos: [string, boolean][] = checklist
    ? [
        ['Un servicio que alguien preste', checklist.tiene_servicio_activo],
        ['El horario', checklist.tiene_horario],
        ['Dónde estás', checklist.tiene_ubicacion],
        ['Una foto', checklist.tiene_foto],
      ]
    : [];

  return (
    <div className="pila">
      <h1 className="rotulo rotulo--grande">{publicado ? 'Tu salón ya se ve.' : 'Tu local está creado.'}</h1>

      {publicado ? (
        <p className="parrafo">
          Se puede encontrar y reservar. Este es el enlace que va en tu bio de Instagram:{' '}
          <Link href={`/salon/${slug}`}>/salon/{slug}</Link>
        </p>
      ) : (
        <p className="parrafo">
          Ya puedes agendar citas desde tu panel. Para que además <strong>lo encuentre alguien</strong>, falta esto:
        </p>
      )}

      {!publicado ? (
        <ul className="pila pila--apretada">
          {puntos.map(([texto, hecho]) => (
            <li key={texto} className={hecho ? 'bloque bloque--exito relleno' : 'bloque relleno'}>
              <span aria-hidden="true">{hecho ? '✓' : '○'}</span> {texto}
              <span className="solo-lectores">{hecho ? ' — hecho' : ' — pendiente'}</span>
            </li>
          ))}
        </ul>
      ) : null}

      {/* La foto es lo último que separa a un salón de publicarse, así que se sube **aquí
          mismo** y no en otra pantalla: mandar a alguien a buscar dónde subirla, justo en el
          paso en el que ya casi está, es donde se abandona un alta. */}
      {!publicado && checklist && !checklist.tiene_foto ? (
        <div className="pila pila--apretada">
          <p className="parrafo">
            Solo falta <strong>una foto</strong>. Es la que se ve en la búsqueda y en el mapa: con el escaparate o la
            silla recién ordenada basta.
          </p>
          <SubirFoto clase="portada" rotulo="Subir la portada" alSubir={() => void mirarChecklist()} />
        </div>
      ) : null}

      {fallo ? (
        <p className="campo__fallo" role="alert">
          {fallo}
        </p>
      ) : null}

      <div className="tira">
        {!publicado && checklist?.listo_para_publicar ? (
          <Boton tono="cierra" onClick={publicar} cargando={publicando} rotuloCargando="Publicando" hijos="Publicar mi salón" />
        ) : null}
        <Boton tono="abre" onClick={alPanel} hijos="Ir a mi agenda" />
      </div>
    </div>
  );
}
