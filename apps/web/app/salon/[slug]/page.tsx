import Link from 'next/link';
import { Suspense } from 'react';

import { Cargando, Roto, Vacio } from '@/componentes/estados';
import { Abierto, Inicial, Nota } from '@/componentes/piezas';
import { api, BASE_API, comoMensaje, FalloDeApi, type PerfilPublico } from '@/lib/api';
import { duracion, precioDeServicio } from '@/lib/formato';

/**
 * La ficha del salón.
 *
 * Orden a propósito: primero **quién atiende** y después la carta de servicios. En el encargo
 * del 7 de septiembre la clienta elige antes a la persona que al local, y la API lo respalda:
 * una reserva sin `profesional_id` la rechaza. Poner el equipo debajo de los precios sería
 * pintar lo contrario de lo que hace el producto.
 *
 * El equipo y las reseñas van cada uno en su `Suspense`: la cabecera del salón se ve enseguida
 * y lo lento llega después, con su estado de carga a la vista.
 */

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

export default async function Ficha({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;

  let salon: PerfilPublico;
  try {
    salon = await api.ficha(slug);
  } catch (error) {
    const noExiste = error instanceof FalloDeApi && error.estado === 404;
    return (
      <div className="contenido seccion">
        {noExiste ? (
          <Vacio
            titulo="Este salón no está publicado"
            explicacion={comoMensaje(error)}
            accion={
              <Link className="boton boton--abre" href="/buscar">
                Ver los salones que sí lo están
              </Link>
            }
          />
        ) : (
          <Roto
            mensaje={comoMensaje(error)}
            accion={
              <Link className="boton boton--secundario" href="/buscar">
                Volver a la búsqueda
              </Link>
            }
          />
        )}
      </div>
    );
  }

  return (
    <div className="contenido">
      <nav className="migas" aria-label="Dónde estás">
        <Link href="/">Portada</Link>
        <span aria-hidden="true">›</span>
        <Link href="/buscar">Resultados</Link>
        <span aria-hidden="true">›</span>
        <span>{salon.nombre}</span>
      </nav>

      <div className="bloque bloque--lienzo relleno--grande pila aparece">
        <div className="tira">
          <Inicial texto={salon.nombre} grande />
          <div className="pila pila--apretada">
            <h1 className="rotulo rotulo--grande">{salon.nombre}</h1>
            <p className="fila__datos">
              {salon.direccion ? <span>{salon.direccion}</span> : null}
              <Nota valor={salon.rating} resenas={salon.numero_reviews} />
              <Abierto abierto={salon.abierto_ahora} />
            </p>
          </div>
        </div>

        {salon.descripcion ? <p className="parrafo">{salon.descripcion}</p> : null}

        {/* Los atributos NO son fichas tocables: pintarlos como una `opcion` haría que la
            gente los pulsara esperando filtrar. Van con la marca, que no se toca. */}
        {salon.atributos.length > 0 ? (
          <ul className="tira">
            {salon.atributos.map((atributo) => (
              <li key={atributo} className="marca marca--cerrado">
                {atributo}
              </li>
            ))}
          </ul>
        ) : null}

        <div className="tira">
          <Link className="boton boton--cierra" href={`/reservar/${salon.slug}`}>
            Reservar una hora
          </Link>
          {salon.tiene_whatsapp ? (
            <a
              className="boton boton--secundario"
              href={`${BASE_API}/api/v1/publico/negocios/${salon.slug}/chat`}
              rel="noreferrer"
            >
              Escribir por WhatsApp
            </a>
          ) : null}
        </div>
      </div>

      {/* La publicidad flash del salón. Amarillo: avisa, y solo como superficie. */}
      {salon.anuncio ? (
        <div className="bloque bloque--aviso relleno seccion--corta" role="note">
          <span className="etiqueta">Del salón</span>
          <p>{salon.anuncio.texto}</p>
        </div>
      ) : null}

      <section className="seccion">
        <div className="titulo-seccion">
          <h2 className="rotulo rotulo--medio">¿Con quién quieres ir?</h2>
        </div>
        <Suspense fallback={<Cargando que="Cargando el equipo" filas={2} />}>
          <Equipo slug={salon.slug} />
        </Suspense>
      </section>

      <section className="seccion">
        <div className="titulo-seccion">
          <h2 className="rotulo rotulo--medio">La carta</h2>
          <span className="menor">{salon.servicios.length} servicios</span>
        </div>
        {salon.servicios.length === 0 ? (
          <Vacio titulo="Todavía no hay servicios" explicacion="Este salón aún no ha dado de alta su carta." />
        ) : (
          <ul className="lista">
            {salon.servicios.map((servicio) => (
              <li key={servicio.id} className="fila">
                <div className="tira tira--entre">
                  <div className="pila pila--apretada">
                    <span className="fila__titulo">{servicio.nombre}</span>
                    <span className="fila__datos">
                      <span>{duracion(servicio.duracion_minutos)}</span>
                      <span className="cifra">{precioDeServicio(servicio)}</span>
                    </span>
                  </div>
                  <Link className="boton boton--cierra" href={`/reservar/${salon.slug}?servicio=${servicio.id}`}>
                    Elegir hora
                  </Link>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="seccion">
        <div className="titulo-seccion">
          <h2 className="rotulo rotulo--medio">Horario</h2>
        </div>
        {salon.horario.length === 0 ? (
          <p className="parrafo">Este salón no ha publicado su horario.</p>
        ) : (
          <dl className="resumen">
            {DIAS.map((nombre, indice) => {
              const tramos = salon.horario.filter((tramo) => tramo.dia === indice);
              return (
                <div key={nombre} className="resumen__linea">
                  <dt>{nombre}</dt>
                  <dd>
                    {tramos.length === 0
                      ? 'Cerrado'
                      : tramos.map((tramo) => `${tramo.abre.slice(0, 5)}–${tramo.cierra.slice(0, 5)}`).join(' · ')}
                  </dd>
                </div>
              );
            })}
          </dl>
        )}
      </section>

      <section className="seccion">
        <div className="titulo-seccion">
          <h2 className="rotulo rotulo--medio">Lo que dicen</h2>
        </div>
        <Suspense fallback={<Cargando que="Cargando las opiniones" filas={2} />}>
          <Resenas slug={salon.slug} />
        </Suspense>
      </section>
    </div>
  );
}

async function Equipo({ slug }: { slug: string }) {
  try {
    const equipo = await api.equipo(slug);
    if (equipo.length === 0) {
      return (
        <Vacio
          titulo="Este salón no ha publicado su equipo"
          explicacion="Sin personas publicadas no se puede elegir con quién, y sin eso no hay reserva."
        />
      );
    }
    return (
      <ul className="lista">
        {equipo.map((persona) => (
          <li key={persona.id} className="fila fila--resultado">
            <Inicial texto={persona.nombre} persona />
            <div className="fila__cuerpo">
              <Link className="fila__titulo" href={`/salon/${slug}/con/${persona.slug ?? persona.id}`}>
                {persona.nombre}
              </Link>
              {persona.titular ? <p className="menor">{persona.titular}</p> : null}
              <p className="fila__datos">
                {persona.anos_de_experiencia ? <span>{persona.anos_de_experiencia} años</span> : null}
                <Nota valor={persona.nota} resenas={persona.numero_resenas} />
                <span>{persona.citas_atendidas} citas atendidas</span>
              </p>
              <div className="fila__pie">
                <Link className="boton boton--cierra" href={`/reservar/${slug}?profesional=${persona.id}`}>
                  Ver sus horas
                </Link>
                <Link className="boton boton--texto" href={`/salon/${slug}/con/${persona.slug ?? persona.id}`}>
                  Su perfil
                </Link>
              </div>
            </div>
          </li>
        ))}
      </ul>
    );
  } catch (error) {
    return <Roto mensaje={comoMensaje(error)} />;
  }
}

async function Resenas({ slug }: { slug: string }) {
  try {
    const { resumen, resenas } = await api.resenas(slug);
    if (resenas.length === 0) {
      return <Vacio titulo="Todavía nadie ha opinado" explicacion="Cuando alguien termine una cita aquí, podrá opinar." />;
    }
    const mayor = Math.max(...Object.values(resumen.reparto), 1);
    return (
      <div className="pila">
        <div className="reparto">
          {[5, 4, 3, 2, 1].map((estrellas) => {
            const cuantas = resumen.reparto[String(estrellas)] ?? 0;
            return (
              <div key={estrellas} style={{ display: 'contents' }}>
                <span>{estrellas}</span>
                <span className="reparto__barra">
                  <span className="reparto__parte" style={{ width: `${(cuantas / mayor) * 100}%` }} />
                </span>
                <span>{cuantas}</span>
              </div>
            );
          })}
        </div>

        <ul>
          {resenas.slice(0, 6).map((resena) => (
            <li key={resena.id} className="resena">
              <p className="fila__datos">
                <span className="cifra">{resena.nota}/5</span>
                <span>{resena.autor}</span>
                {resena.profesional ? <span>con {resena.profesional}</span> : null}
              </p>
              {resena.texto ? <p className="parrafo">{resena.texto}</p> : null}
              {resena.respuesta ? (
                <p className="resena__respuesta">
                  <strong>Respuesta del salón: </strong>
                  {resena.respuesta.texto}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
    );
  } catch (error) {
    return <Roto mensaje={comoMensaje(error)} />;
  }
}
