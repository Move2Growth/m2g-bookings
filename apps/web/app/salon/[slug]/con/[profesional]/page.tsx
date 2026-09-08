import Link from 'next/link';
import { Suspense } from 'react';

import { Cargando, Roto, Vacio } from '@/componentes/estados';
import { Inicial, Nota } from '@/componentes/piezas';
import { api, comoMensaje, FalloDeApi, type PerfilDelProfesional } from '@/lib/api';
import { cuandoEs, duracion, fechaLocal, hora, precioDeServicio } from '@/lib/formato';

/**
 * El perfil de una persona del equipo.
 *
 * Aquí está la mitad del encargo del 7 de septiembre: el profesional es una entidad de primera
 * y no una etiqueta dentro del salón. Por eso esta pantalla tiene lo mismo que la del local
 * —años, trabajos, servicios, reseñas y **horas libres de verdad**— y no una versión reducida.
 *
 * Las horas se piden con el primer servicio de su catálogo, que es lo único que se puede
 * suponer sin preguntar: la duración cambia el hueco, así que en cuanto se elige otro servicio
 * en la pantalla de reserva, las horas se vuelven a calcular.
 */

export default async function Persona({ params }: { params: Promise<{ slug: string; profesional: string }> }) {
  const { slug, profesional } = await params;

  let persona: PerfilDelProfesional;
  try {
    persona = await api.profesional(slug, profesional);
  } catch (error) {
    const noExiste = error instanceof FalloDeApi && error.estado === 404;
    return (
      <div className="contenido seccion">
        {noExiste ? (
          <Vacio
            titulo="Esa persona no está en este salón"
            explicacion={comoMensaje(error)}
            accion={
              <Link className="boton boton--abre" href={`/salon/${slug}`}>
                Ver el equipo del salón
              </Link>
            }
          />
        ) : (
          <Roto mensaje={comoMensaje(error)} />
        )}
      </div>
    );
  }

  const redes = [
    { rotulo: 'Instagram', url: persona.redes.instagram_url, usuario: persona.redes.instagram },
    { rotulo: 'Facebook', url: persona.redes.facebook_url, usuario: persona.redes.facebook },
    { rotulo: 'X', url: persona.redes.x_url, usuario: persona.redes.x },
  ].filter((red) => red.url);

  return (
    <div className="contenido">
      <nav className="migas" aria-label="Dónde estás">
        <Link href="/">Portada</Link>
        <span aria-hidden="true">›</span>
        <Link href={`/salon/${slug}`}>{persona.negocio ?? 'El salón'}</Link>
        <span aria-hidden="true">›</span>
        <span>{persona.nombre}</span>
      </nav>

      <div className="bloque bloque--lienzo relleno--grande pila aparece">
        <div className="tira">
          <Inicial texto={persona.nombre} persona grande />
          <div className="pila pila--apretada">
            <h1 className="rotulo rotulo--grande">{persona.nombre}</h1>
            {persona.titular ? <p className="menor">{persona.titular}</p> : null}
            <p className="fila__datos">
              <Nota valor={persona.nota} resenas={persona.numero_resenas} />
              {persona.direccion ? <span>{persona.direccion}</span> : null}
            </p>
          </div>
        </div>

        <div className="datos">
          <div className="dato">
            <span className="dato__cifra">{persona.anos_de_experiencia ?? '—'}</span>
            <span className="etiqueta">Años detrás de la silla</span>
          </div>
          <div className="dato">
            <span className="dato__cifra">{persona.citas_atendidas}</span>
            <span className="etiqueta">Citas atendidas</span>
          </div>
          <div className="dato">
            <span className="dato__cifra">{persona.clientes_atendidos}</span>
            <span className="etiqueta">Clientas distintas</span>
          </div>
        </div>

        {persona.descripcion ? <p className="parrafo">{persona.descripcion}</p> : null}

        {redes.length > 0 ? (
          <div className="pila pila--apretada">
            <span className="etiqueta">Dónde enseña su trabajo</span>
            <div className="opciones">
              {redes.map((red) => (
                <a key={red.rotulo} className="opcion" href={red.url ?? '#'} rel="noreferrer" target="_blank">
                  {red.rotulo}
                  {red.usuario ? ` · ${red.usuario}` : ''}
                </a>
              ))}
            </div>
          </div>
        ) : null}

        <Link className="boton boton--cierra" href={`/reservar/${slug}?profesional=${persona.id}`}>
          Reservar con {persona.nombre.split(' ')[0]}
        </Link>
      </div>

      <section className="seccion">
        <div className="titulo-seccion">
          <h2 className="rotulo rotulo--medio">Sus próximas horas</h2>
          <span className="menor">
            {persona.catalogo.length > 0 ? `Calculadas para «${persona.catalogo[0].nombre}»` : ''}
          </span>
        </div>
        <Suspense fallback={<Cargando que="Calculando sus huecos de la semana" filas={2} />}>
          <ProximasHoras persona={persona} slug={slug} />
        </Suspense>
      </section>

      <section className="seccion">
        <div className="titulo-seccion">
          <h2 className="rotulo rotulo--medio">Lo que hace</h2>
        </div>
        {persona.catalogo.length === 0 ? (
          <Vacio titulo="No tiene servicios asignados" explicacion="Sin servicios asignados no se le puede reservar." />
        ) : (
          <ul className="lista">
            {persona.catalogo.map((servicio) => (
              <li key={servicio.id} className="fila">
                <div className="tira tira--entre">
                  <div className="pila pila--apretada">
                    <span className="fila__titulo">{servicio.nombre}</span>
                    <span className="fila__datos">
                      <span>{duracion(servicio.duracion_minutos)}</span>
                      <span className="cifra">{precioDeServicio(servicio)}</span>
                    </span>
                  </div>
                  <Link
                    className="boton boton--cierra"
                    href={`/reservar/${slug}?profesional=${persona.id}&servicio=${servicio.id}`}
                  >
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
          <h2 className="rotulo rotulo--medio">Su trabajo</h2>
        </div>
        {persona.trabajos.length === 0 && persona.galeria.length === 0 ? (
          <Vacio
            titulo="Todavía no ha subido fotos"
            explicacion="Cuando ate una foto suya a un servicio del salón, se verá aquí y también en la carta, para saber quién hizo qué."
          />
        ) : (
          <ul className="lista">
            {[...persona.trabajos, ...persona.galeria].map((foto) => (
              <li key={foto.id} className="fila">
                <span className="fila__titulo">{foto.servicio ?? 'Trabajo'}</span>
                {foto.descripcion ? <p className="menor">{foto.descripcion}</p> : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="seccion">
        <div className="titulo-seccion">
          <h2 className="rotulo rotulo--medio">Sus reseñas</h2>
          <span className="menor">{persona.numero_resenas} opiniones</span>
        </div>
        {persona.resenas.length === 0 ? (
          <Vacio titulo="Todavía nadie ha opinado de su trabajo" explicacion="Las reseñas se escriben al terminar una cita." />
        ) : (
          <ul>
            {persona.resenas.slice(0, 6).map((resena) => (
              <li key={resena.id} className="resena">
                <p className="fila__datos">
                  <span className="cifra">{resena.nota}/5</span>
                  <span>{resena.autor}</span>
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
        )}
      </section>
    </div>
  );
}

async function ProximasHoras({ persona, slug }: { persona: PerfilDelProfesional; slug: string }) {
  if (persona.catalogo.length === 0) {
    return <Vacio titulo="No se le pueden pedir horas" explicacion="No tiene ningún servicio asignado todavía." />;
  }

  const servicio = persona.catalogo[0];
  const ahora = new Date();
  const dentroDeUnaSemana = new Date(ahora.getTime() + 7 * 86_400_000);

  try {
    const { slots, zona } = await api.horasDelProfesional(
      persona.id,
      [servicio.id],
      ahora.toISOString(),
      dentroDeUnaSemana.toISOString(),
    );

    if (slots.length === 0) {
      return (
        <Vacio
          titulo="No le queda nada libre esta semana"
          explicacion="Su agenda está llena los próximos siete días. Prueba con otra persona del salón."
          accion={
            <Link className="boton boton--abre" href={`/salon/${slug}`}>
              Ver el resto del equipo
            </Link>
          }
        />
      );
    }

    // Los slots vienen cada 15 minutos: para leerlos en el pulgar se agrupan por día y se
    // enseñan los primeros de cada uno. El resto está en la pantalla de reserva.
    const porDia = new Map<string, typeof slots>();
    slots.forEach((slot) => {
      const dia = fechaLocal(new Date(slot.inicio), zona);
      porDia.set(dia, [...(porDia.get(dia) ?? []), slot]);
    });

    return (
      <div className="pila">
        {Array.from(porDia.entries())
          .slice(0, 3)
          .map(([dia, delDia]) => (
            <div key={dia} className="franja-horas">
              <span className="etiqueta">
                {cuandoEs(delDia[0].inicio, zona)} · {delDia.length} huecos
              </span>
              <div className="horas">
                {delDia.slice(0, 8).map((slot) => (
                  <Link
                    key={slot.inicio}
                    className="hora"
                    href={`/reservar/${slug}?profesional=${persona.id}&servicio=${servicio.id}&dia=${dia}&inicio=${encodeURIComponent(slot.inicio)}`}
                  >
                    {hora(slot.inicio, zona)}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        <Link className="boton boton--secundario" href={`/reservar/${slug}?profesional=${persona.id}`}>
          Ver todas sus horas
        </Link>
      </div>
    );
  } catch (error) {
    return <Roto mensaje={comoMensaje(error)} />;
  }
}
