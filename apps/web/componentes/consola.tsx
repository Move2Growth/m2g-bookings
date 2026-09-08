'use client';

/**
 * La consola interna de M2G.
 *
 * Es **otra superficie**, no una pantalla más del producto: otro sistema de acceso, con segundo
 * factor obligatorio, otra llave de sesión y otro rol de base de datos por debajo. Aquí se
 * suspende un salón y se oculta una reseña, así que la separación no es estética.
 *
 * Todo lo que cambia algo deja fila en la auditoría, y por eso las decisiones piden un motivo:
 * un registro que dice «alguien suspendió esto» y no dice por qué no sirve para nada.
 */

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import { Boton } from '@/componentes/boton';
import { Cargando, Roto, Vacio } from '@/componentes/estados';
import { Seccion } from '@/componentes/piezas';
import {
  api,
  comoMensaje,
  type FotoEnCola,
  type Metricas,
  type NegocioEnConsola,
  type ReporteEnCola,
} from '@/lib/api';
import { conConsola, guardarConsola, leerConsola, salirDeConsola } from '@/lib/consola';

/* ── La puerta ────────────────────────────────────────────────────────────────────────────── */

export function PuertaDeConsola({ children }: { children: React.ReactNode }) {
  const [dentro, setDentro] = useState<boolean | null>(null);
  useEffect(() => setDentro(leerConsola() !== null), []);

  if (dentro === null) return null;
  if (!dentro) return <Entrar alEntrar={() => setDentro(true)} />;

  return (
    <div className="pila">
      <nav className="nav-local" aria-label="Consola">
        <ul className="nav-local__carril">
          {(
            [
              ['/consola', 'Cómo va'],
              ['/consola/negocios', 'Salones'],
              ['/consola/moderacion', 'Moderación'],
            ] as const
          ).map(([ruta, rotulo]) => (
            <li key={ruta}>
              <Link className="nav-local__sitio" href={ruta}>
                {rotulo}
              </Link>
            </li>
          ))}
          <li>
            <button
              type="button"
              className="nav-local__sitio"
              onClick={() => {
                salirDeConsola();
                setDentro(false);
              }}
            >
              Salir
            </button>
          </li>
        </ul>
      </nav>
      {children}
    </div>
  );
}

function Entrar({ alEntrar }: { alEntrar: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [codigo, setCodigo] = useState('');
  const [fallo, setFallo] = useState<string | null>(null);
  const [entrando, setEntrando] = useState(false);

  async function entrar(evento: React.FormEvent) {
    evento.preventDefault();
    setEntrando(true);
    setFallo(null);
    try {
      const sesion = await api.entrarEnConsola(email.trim(), password, codigo.trim());
      guardarConsola(sesion);
      alEntrar();
    } catch (error) {
      setFallo(comoMensaje(error));
      setPassword('');
      setCodigo('');
    } finally {
      setEntrando(false);
    }
  }

  return (
    <form className="pila" onSubmit={entrar} noValidate>
      <p className="parrafo">
        Esta es la consola de M2G. <strong>No es la cuenta con la que reservas</strong>: es otra, con segundo factor
        obligatorio.
      </p>
      <div className="campo">
        <label className="campo__rotulo" htmlFor="email">
          Correo
        </label>
        <input className="campo__caja" id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      </div>
      <div className="campo">
        <label className="campo__rotulo" htmlFor="password">
          Contraseña
        </label>
        <input
          className="campo__caja"
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      <div className="campo">
        <label className="campo__rotulo" htmlFor="codigo">
          Código del segundo factor
        </label>
        <input
          className="campo__caja"
          id="codigo"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          value={codigo}
          onChange={(e) => setCodigo(e.target.value)}
        />
      </div>
      {/* Los tres fallan con el mismo mensaje a propósito: decir cuál falló le dice a quien
          prueba a ciegas cuándo va por buen camino. */}
      {fallo ? (
        <p className="campo__fallo" role="alert">
          {fallo}
        </p>
      ) : null}
      <Boton tono="cierra" type="submit" cargando={entrando} rotuloCargando="Entrando" hijos="Entrar en la consola" />
    </form>
  );
}

/* ── Cómo va la plataforma ────────────────────────────────────────────────────────────────── */

export function ComoVa() {
  const [datos, setDatos] = useState<Metricas | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);

  const traer = useCallback(() => {
    setFallo(null);
    conConsola((acceso) => api.metricas(acceso))
      .then(setDatos)
      .catch((error) => setFallo(comoMensaje(error)));
  }, []);
  useEffect(traer, [traer]);

  if (fallo) return <Roto mensaje={fallo} accion={<Boton tono="abre" onClick={traer} hijos="Volver a intentarlo" />} />;
  if (!datos) return <Cargando que="Contando la plataforma" filas={3} />;

  const tope = Math.max(1, ...datos.reservas_por_dia.map((d) => d.valor));

  return (
    <div className="pila">
      <ul className="cifras-grandes">
        <li>
          <span className="cifras-grandes__valor">{datos.negocios_publicados}</span>
          <span className="cifras-grandes__que">salones publicados</span>
        </li>
        <li>
          <span className="cifras-grandes__valor">{datos.negocios_totales}</span>
          <span className="cifras-grandes__que">dados de alta</span>
        </li>
        <li>
          <span className="cifras-grandes__valor">{datos.negocios_suspendidos}</span>
          <span className="cifras-grandes__que">suspendidos</span>
        </li>
        <li>
          <span className="cifras-grandes__valor">{datos.reportes_abiertos}</span>
          <span className="cifras-grandes__que">reportes sin ver</span>
        </li>
      </ul>

      {datos.reportes_abiertos > 0 ? (
        <p className="bloque bloque--cobalto relleno">
          Hay {datos.reportes_abiertos} {datos.reportes_abiertos === 1 ? 'reporte' : 'reportes'} esperando.{' '}
          <Link href="/consola/moderacion">Verlos</Link>
        </p>
      ) : null}

      <Seccion titulo="Reservas por día">
        {datos.reservas_por_dia.length === 0 ? (
          <Vacio titulo="Todavía no hay reservas" explicacion="En cuanto entre la primera, aparece aquí." />
        ) : (
          <ul className="barras">
            {datos.reservas_por_dia.map((d) => (
              <li key={d.dia} className="barras__fila">
                <span className="barras__cuando cifras">{d.dia.slice(5)}</span>
                <span className="barras__pista">
                  <span className="barras__relleno" style={{ inlineSize: `${Math.round((d.valor / tope) * 100)}%` }} />
                </span>
                <span className="barras__cuanto cifras">{d.valor}</span>
              </li>
            ))}
          </ul>
        )}
      </Seccion>

      {/* **Las impresiones y los clics del marketplace están a cero y se dice.** Es el dato que
          sostiene el negocio —el posicionamiento pagado— y enseñar un cero sin explicarlo hace
          pensar que la plataforma no la usa nadie. */}
      {datos.impresiones_por_dia.length === 0 ? (
        <p className="menor tenue">
          Sin impresiones registradas todavía: eso lo empieza a contar el marketplace cuando haya tráfico de verdad.
        </p>
      ) : null}
    </div>
  );
}

/* ── Los salones ──────────────────────────────────────────────────────────────────────────── */

export function Salones() {
  const [texto, setTexto] = useState('');
  const [lista, setLista] = useState<NegocioEnConsola[] | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [tocando, setTocando] = useState<string | null>(null);
  const [motivo, setMotivo] = useState<Record<string, string>>({});

  const traer = useCallback(
    (buscar?: string) => {
      setFallo(null);
      conConsola((acceso) => api.negociosEnConsola(acceso, buscar))
        .then(setLista)
        .catch((error) => setFallo(comoMensaje(error)));
    },
    [],
  );
  useEffect(() => traer(), [traer]);

  async function suspender(negocio: NegocioEnConsola) {
    const porQue = (motivo[negocio.id] ?? '').trim();
    if (!porQue) return;
    setTocando(negocio.id);
    try {
      await conConsola((acceso) => api.suspender(negocio.id, porQue, acceso));
      setMotivo((m) => ({ ...m, [negocio.id]: '' }));
      traer(texto || undefined);
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setTocando(null);
    }
  }

  async function reactivar(negocio: NegocioEnConsola) {
    setTocando(negocio.id);
    try {
      await conConsola((acceso) => api.reactivar(negocio.id, acceso));
      traer(texto || undefined);
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setTocando(null);
    }
  }

  return (
    <div className="pila">
      <form
        className="buscador"
        onSubmit={(e) => {
          e.preventDefault();
          traer(texto || undefined);
        }}
      >
        <input
          className="campo__caja"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          placeholder="Nombre o dirección web"
          aria-label="Buscar un salón"
        />
        <Boton tono="abre" type="submit" hijos="Buscar" />
      </form>

      {fallo ? <Roto mensaje={fallo} accion={<Boton tono="abre" onClick={() => traer()} hijos="Reintentar" />} /> : null}
      {!lista && !fallo ? <Cargando que="Buscando salones" filas={4} /> : null}
      {lista && lista.length === 0 ? <Vacio titulo="Ningún salón con eso" explicacion="Prueba con otra palabra." /> : null}

      {lista && lista.length > 0 ? (
        <ul className="pila pila--apretada">
          {lista.map((negocio) => (
            <li key={negocio.id} className="ficha-persona">
              <div className="pila pila--apretada">
                <p className="rotulo rotulo--pequeno">
                  {negocio.nombre} <span className="sello sello--apagado">{negocio.estado}</span>
                </p>
                <p className="menor tenue">
                  {negocio.reservas} reservas · {negocio.clientes} clientas · {negocio.reviews} reseñas
                  {negocio.rating ? ` · ${negocio.rating.toFixed(2)}` : ''}
                </p>
                {negocio.motivo_suspension ? (
                  <p className="menor">Suspendido por: {negocio.motivo_suspension}</p>
                ) : null}
                <Link className="menor" href={`/salon/${negocio.slug}`}>
                  Ver su ficha
                </Link>
              </div>

              <div className="pila pila--apretada">
                {negocio.estado === 'suspendido' ? (
                  <Boton
                    tono="abre"
                    onClick={() => reactivar(negocio)}
                    cargando={tocando === negocio.id}
                    rotuloCargando="Reactivando"
                    hijos="Reactivar"
                  />
                ) : (
                  <>
                    {/* **El motivo es obligatorio.** Suspender sin decir por qué deja una fila
                        de auditoría que no sirve para nada, y a un salón sin manera de saber
                        qué hizo mal. */}
                    <input
                      className="campo__caja"
                      value={motivo[negocio.id] ?? ''}
                      onChange={(e) => setMotivo((m) => ({ ...m, [negocio.id]: e.target.value }))}
                      placeholder="Por qué se suspende"
                      aria-label={`Motivo para suspender ${negocio.nombre}`}
                    />
                    <Boton
                      tono="riesgo"
                      onClick={() => suspender(negocio)}
                      disabled={!(motivo[negocio.id] ?? '').trim()}
                      cargando={tocando === negocio.id}
                      rotuloCargando="Suspendiendo"
                      hijos="Suspender"
                    />
                  </>
                )}
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

/* ── Moderación: reseñas reportadas y fotos por revisar ───────────────────────────────────── */

export function Moderacion() {
  const [resenas, setResenas] = useState<ReporteEnCola[] | null>(null);
  const [fotos, setFotos] = useState<FotoEnCola[] | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [tocando, setTocando] = useState<string | null>(null);

  const traer = useCallback(() => {
    setFallo(null);
    conConsola((acceso) => api.resenasReportadas(acceso))
      .then(setResenas)
      .catch((error) => setFallo(comoMensaje(error)));
    conConsola((acceso) => api.fotosEnCola(acceso))
      .then(setFotos)
      .catch((error) => setFallo(comoMensaje(error)));
  }, []);
  useEffect(traer, [traer]);

  async function resolver(reporte: ReporteEnCola, accion: 'ocultar' | 'mantener') {
    setTocando(reporte.reporte_id);
    try {
      await conConsola((acceso) => api.resolverReporte(reporte.reporte_id, accion, null, acceso));
      traer();
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setTocando(null);
    }
  }

  async function decidirFoto(foto: FotoEnCola, accion: 'aprobar' | 'rechazar') {
    setTocando(foto.foto_id);
    try {
      await conConsola((acceso) => api.decidirFoto(foto.foto_id, accion, null, acceso));
      traer();
    } catch (error) {
      setFallo(comoMensaje(error));
    } finally {
      setTocando(null);
    }
  }

  return (
    <div className="pila">
      {fallo ? <Roto mensaje={fallo} accion={<Boton tono="abre" onClick={traer} hijos="Reintentar" />} /> : null}

      <Seccion titulo={`Reseñas reportadas${resenas ? ` (${resenas.length})` : ''}`}>
        {!resenas ? <Cargando que="Buscando reportes" filas={2} /> : null}
        {resenas && resenas.length === 0 ? (
          <Vacio titulo="Nada que moderar" explicacion="No hay ninguna reseña reportada esperando." />
        ) : null}
        {resenas && resenas.length > 0 ? (
          <ul className="pila pila--apretada">
            {resenas.map((reporte) => (
              <li key={reporte.reporte_id} className="anuncio">
                <p className="menor tenue">
                  {reporte.negocio} · {reporte.nota} estrellas · lo reportó {reporte.reportado_por} por «
                  {reporte.motivo}»
                </p>
                <p>{reporte.texto ?? 'Sin texto: solo puntuación.'}</p>
                {/* **Mantener devuelve la reseña al perfil**, no solo descarta el reporte: si
                    un reporte anterior la había ocultado, vuelve a contar en la media. */}
                <div className="tira">
                  <Boton
                    tono="riesgo"
                    onClick={() => resolver(reporte, 'ocultar')}
                    cargando={tocando === reporte.reporte_id}
                    rotuloCargando="Ocultando"
                    hijos="Ocultarla"
                  />
                  <Boton
                    tono="secundario"
                    onClick={() => resolver(reporte, 'mantener')}
                    cargando={tocando === reporte.reporte_id}
                    rotuloCargando="Manteniendo"
                    hijos="Mantenerla"
                  />
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </Seccion>

      <Seccion titulo={`Fotos por revisar${fotos ? ` (${fotos.length})` : ''}`}>
        {!fotos ? <Cargando que="Buscando fotos" filas={2} /> : null}
        {fotos && fotos.length === 0 ? (
          <Vacio titulo="Ninguna foto en cola" explicacion="Cuando alguien suba una, se revisa aquí antes de salir." />
        ) : null}
        {fotos && fotos.length > 0 ? (
          <ul className="pila pila--apretada">
            {fotos.map((foto) => (
              <li key={foto.foto_id} className="anuncio">
                <p className="menor tenue">
                  {foto.profesional} · {foto.negocio} · {foto.estado}
                </p>
                <p className="menor">{foto.descripcion ?? 'Sin descripción'}</p>
                {/* La imagen no se puede cargar todavía —no hay almacén decidido— así que se
                    enseña su clave en vez de un recuadro roto. */}
                <p className="menor cifras">{foto.url}</p>
                <div className="tira">
                  <Boton
                    tono="abre"
                    onClick={() => decidirFoto(foto, 'aprobar')}
                    cargando={tocando === foto.foto_id}
                    rotuloCargando="Aprobando"
                    hijos="Aprobar"
                  />
                  <Boton
                    tono="riesgo"
                    onClick={() => decidirFoto(foto, 'rechazar')}
                    cargando={tocando === foto.foto_id}
                    rotuloCargando="Rechazando"
                    hijos="Rechazar"
                  />
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </Seccion>
    </div>
  );
}
