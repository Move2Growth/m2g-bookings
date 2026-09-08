import Link from 'next/link';
import { Suspense } from 'react';

import { FilaSalon } from '@/componentes/fila-salon';
import { Cargando, Roto, Vacio } from '@/componentes/estados';
import { Seccion } from '@/componentes/piezas';
import { api, comoMensaje } from '@/lib/api';
import { fechaLocal, sumarDias } from '@/lib/formato';

/**
 * La portada.
 *
 * En esta dirección lo primero que se pregunta no es «¿qué salón?» sino **«¿cuándo puedes?»**.
 * Una clienta en Panamá no navega un catálogo: tiene un hueco —hoy después del trabajo, el
 * sábado por la mañana— y quiere saber quién la puede atender dentro de ese hueco. Por eso el
 * bloque cobalto de arriba es un reloj y no un escaparate, y por eso lo que se lista debajo no
 * son salones sino **horas que ya se pueden coger**, cada una con su nombre y su precio.
 *
 * Se pinta en el servidor y contra la API de verdad. Lo que tarda va dentro de un `Suspense`
 * con su estado de carga, para que la pantalla se vea antes de que la agenda termine de
 * calcularse: la primera hora libre de cada salón cuesta una consulta por salón.
 */

export default function Portada() {
  const hoy = fechaLocal(new Date());
  const manana = sumarDias(hoy, 1);

  return (
    <>
      <div className="bloque bloque--cobalto">
        <div className="contenido seccion aparece">
          <div className="pila">
            <span className="etiqueta etiqueta--clara">Ciudad de Panamá</span>
            <h1 className="rotulo rotulo--cartel">Dime cuándo puedes y te digo con quién.</h1>

            <form className="buscador" action="/buscar">
              <div className="campo">
                <label className="campo__rotulo etiqueta--clara" htmlFor="texto">
                  Qué necesitas
                </label>
                <input
                  className="campo__caja"
                  id="texto"
                  name="texto"
                  type="search"
                  placeholder="Corte, uñas, cejas, masaje…"
                  autoComplete="off"
                />
              </div>
              <button className="boton boton--secundario" type="submit">
                Buscar
              </button>
            </form>

            <div className="pila pila--apretada">
              <span className="etiqueta etiqueta--clara">O dime cuándo</span>
              <div className="opciones">
                <Link className="opcion" href="/buscar?cuando=ahora">
                  Ahora mismo
                </Link>
                <Link className="opcion" href="/buscar?cuando=hoy">
                  Hoy
                </Link>
                <Link className="opcion" href={`/buscar?cuando=fecha&dia=${manana}`}>
                  Mañana
                </Link>
                <Link className="opcion" href="/buscar">
                  Cualquier día
                </Link>
              </div>
            </div>

            {/* **El mapa va aquí y no en un menú.** Es la tercera forma de buscar lo mismo: quien
                no sabe el nombre de nada pero sabe por dónde va a pasar. Escondido no lo
                encuentra nadie. */}
            <p className="menor">
              <Link href="/mapa">O míralo en el mapa, por dónde te queda</Link>
            </p>
          </div>
        </div>
      </div>

      <div className="contenido">
        <Seccion
          titulo="Turnos que salen hoy"
          extra={
            <Link className="boton boton--texto" href="/buscar?cuando=hoy">
              Ver todos
            </Link>
          }
        >
          <Suspense fallback={<Cargando que="Mirando la agenda de hoy" filas={3} />}>
            <TurnosDeHoy />
          </Suspense>
        </Seccion>

        <Seccion titulo="Por lo que necesitas">
          <Suspense fallback={<Cargando que="Cargando el catálogo" filas={1} />}>
            <Categorias />
          </Suspense>
        </Seccion>
      </div>

      <div className="bloque bloque--arena">
        <div className="contenido seccion--corta">
          <div className="tira tira--entre">
            <div className="pila pila--apretada">
              <span className="etiqueta">Para el salón</span>
              <p className="rotulo rotulo--pequeno">¿Trabajas aquí dentro?</p>
              <p className="menor">
                La agenda del día, con todo el equipo, en una sola columna. Y si todavía no tienes local, se da de
                alta en tres pasos y es gratis.
              </p>
            </div>
            {/* Dos puertas, y la de crear va primero: quien todavía no tiene salón es quien
                necesita que se lo digan, porque el que ya lo tiene sabe volver solo. */}
            <span className="tira">
              <Link className="boton boton--cierra" href="/local/alta">
                Dar de alta mi salón
              </Link>
              <Link className="boton boton--secundario" href="/local">
                Entrar a mi salón
              </Link>
            </span>
          </div>
        </div>
      </div>
    </>
  );
}

async function TurnosDeHoy() {
  try {
    const salones = await api.buscar({ cuando: 'hoy' });
    const conHora = salones.filter((salon) => salon.proxima_hora !== null);

    if (conHora.length === 0) {
      return (
        <Vacio
          titulo="Hoy ya no queda nada libre"
          explicacion="Los salones publicados tienen la agenda llena para lo que resta del día. Prueba mañana o mira sin filtro de fecha."
          accion={
            <Link className="boton boton--abre" href="/buscar">
              Ver todos los salones
            </Link>
          }
        />
      );
    }

    return (
      <ul className="lista">
        {conHora.slice(0, 6).map((salon) => (
          <FilaSalon key={salon.negocio_id} salon={salon} />
        ))}
      </ul>
    );
  } catch (error) {
    return (
      <Roto
        mensaje={comoMensaje(error)}
        accion={
          <Link className="boton boton--secundario" href="/">
            Volver a intentarlo
          </Link>
        }
      />
    );
  }
}

async function Categorias() {
  try {
    const categorias = await api.categorias();
    if (categorias.length === 0) {
      return <Vacio titulo="Todavía no hay categorías" explicacion="El catálogo de la plataforma está vacío." />;
    }
    return (
      <div className="opciones">
        {categorias.map((categoria) => (
          <Link key={categoria.id} className="opcion" href={`/buscar?categoria=${categoria.slug}`}>
            {categoria.nombre}
          </Link>
        ))}
      </div>
    );
  } catch (error) {
    return <Roto mensaje={comoMensaje(error)} />;
  }
}
