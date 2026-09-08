import Link from 'next/link';
import { Suspense } from 'react';

import { FilaSalon } from '@/componentes/fila-salon';
import { Cargando, Roto, Vacio } from '@/componentes/estados';
import { api, comoMensaje, pedir, type ResultadoDeBusqueda } from '@/lib/api';
import { fechaLocal, sumarDias } from '@/lib/formato';

/**
 * Resultados.
 *
 * Todo el estado de esta pantalla vive **en la URL**: el texto, la zona, la categoría, el
 * cuándo y el orden. Eso hace que se pueda volver atrás, recargar y pasarle el enlace a
 * alguien; y hace que los filtros sean enlaces y no botones con memoria, así que funcionan
 * también con el JavaScript apagado.
 *
 * Cómo ver el estado de error sin apagar la API: añade `?simular=error` a esta ruta. La
 * pantalla pide de verdad una ruta que la API no sirve y enseña el error que devuelva. No hay
 * ningún error de mentira escrito en el componente.
 */

type Consulta = Record<string, string | string[] | undefined>;

export const metadata = { title: 'Buscar' };

export default async function Buscar({ searchParams }: { searchParams: Promise<Consulta> }) {
  const consulta = await searchParams;
  const texto = uno(consulta.texto);
  const categoria = uno(consulta.categoria);
  const zona = uno(consulta.zona);
  const cuando = (uno(consulta.cuando) ?? 'cualquiera') as 'cualquiera' | 'ahora' | 'hoy' | 'fecha';
  const dia = uno(consulta.dia);
  const orden = uno(consulta.orden) ?? 'relevancia';
  const simular = uno(consulta.simular);

  const hoy = fechaLocal(new Date());
  const manana = sumarDias(hoy, 1);

  // El nombre de la categoría se busca en el catálogo en vez de deducirlo del slug: «Spa y
  // masajes» no se saca de «spa-masajes` cambiando guiones por espacios.
  let nombreDeCategoria: string | undefined;
  if (categoria) {
    try {
      nombreDeCategoria = (await api.categorias()).find((una) => una.slug === categoria)?.nombre;
    } catch {
      /* Si el catálogo no responde, el título usa el slug y la pantalla sigue funcionando. */
    }
  }

  const base: Record<string, string | undefined> = { texto, categoria, zona, cuando, dia, orden };

  return (
    <div className="contenido">
      <div className="seccion--corta pila">
        <nav className="migas" aria-label="Dónde estás">
          <Link href="/">Portada</Link>
          <span aria-hidden="true">›</span>
          <span>Resultados</span>
        </nav>

        <h1 className="rotulo rotulo--grande">{titulo(texto, nombreDeCategoria ?? categoria, zona, cuando)}</h1>

        <form className="buscador" action="/buscar">
          <div className="campo">
            <label className="campo__rotulo" htmlFor="texto">
              Qué necesitas
            </label>
            <input
              className="campo__caja"
              id="texto"
              name="texto"
              type="search"
              defaultValue={texto ?? ''}
              placeholder="Corte, uñas, cejas, masaje…"
              autoComplete="off"
            />
          </div>
          {categoria ? <input type="hidden" name="categoria" value={categoria} /> : null}
          {zona ? <input type="hidden" name="zona" value={zona} /> : null}
          {cuando !== 'cualquiera' ? <input type="hidden" name="cuando" value={cuando} /> : null}
          {dia ? <input type="hidden" name="dia" value={dia} /> : null}
          <button className="boton boton--abre" type="submit">
            Buscar
          </button>
        </form>

        <div className="pila pila--apretada">
          <span className="etiqueta">Cuándo</span>
          <div className="opciones">
            <Enlace base={base} cambio={{ cuando: undefined, dia: undefined }} elegida={cuando === 'cualquiera'}>
              Cualquier día
            </Enlace>
            <Enlace base={base} cambio={{ cuando: 'ahora', dia: undefined }} elegida={cuando === 'ahora'}>
              Ahora mismo
            </Enlace>
            <Enlace base={base} cambio={{ cuando: 'hoy', dia: undefined }} elegida={cuando === 'hoy'}>
              Hoy
            </Enlace>
            <Enlace
              base={base}
              cambio={{ cuando: 'fecha', dia: manana }}
              elegida={cuando === 'fecha' && dia === manana}
            >
              Mañana
            </Enlace>
          </div>
        </div>

        {/* El «cuándo» se queda siempre a la vista porque es la pregunta de esta dirección. El
            resto se pliega: a 390 px, tres filas de fichas empujan los resultados fuera de la
            pantalla, y lo que se ha venido a ver es el resultado. Se abre solo si hay algún
            filtro puesto, y funciona sin JavaScript porque es un `details` de verdad. */}
        <details className="plegable" open={Boolean(zona) || orden !== 'relevancia'}>
          <summary className="plegable__tirador">
            Dónde y en qué orden
            {zona || orden !== 'relevancia' ? <span className="marca marca--pagado">Filtrado</span> : null}
          </summary>

          <div className="plegable__cuerpo">
            <div className="pila pila--apretada">
              <span className="etiqueta">Dónde</span>
              <Suspense fallback={<p className="menor">Cargando zonas…</p>}>
                <Zonas base={base} zonaElegida={zona} />
              </Suspense>
            </div>

            <div className="pila pila--apretada">
              <span className="etiqueta">Ordenar por</span>
              <div className="opciones">
                {[
                  ['relevancia', 'Relevancia'],
                  ['rating', 'Mejor valorados'],
                  ['precio', 'Precio'],
                  ['nuevos', 'Nuevos'],
                ].map(([clave, rotulo]) => (
                  <Enlace key={clave} base={base} cambio={{ orden: clave }} elegida={orden === clave}>
                    {rotulo}
                  </Enlace>
                ))}
              </div>
            </div>
          </div>
        </details>

        {texto || categoria || zona || cuando !== 'cualquiera' || orden !== 'relevancia' ? (
          <p>
            <Link className="boton boton--texto" href="/buscar">
              Quitar los filtros
            </Link>
          </p>
        ) : null}
      </div>

      <Suspense
        key={JSON.stringify({ ...base, simular })}
        fallback={<Cargando que="Buscando y calculando la primera hora libre de cada salón" filas={4} />}
      >
        <Resultados
          filtros={{ texto, categoria, zona, cuando, dia, orden }}
          simular={simular}
        />
      </Suspense>
    </div>
  );
}

async function Resultados({
  filtros,
  simular,
}: {
  filtros: { texto?: string; categoria?: string; zona?: string; cuando: 'cualquiera' | 'ahora' | 'hoy' | 'fecha'; dia?: string; orden: string };
  simular?: string;
}) {
  let salones: ResultadoDeBusqueda[];
  try {
    if (simular === 'error') {
      // Una ruta que la API **no** sirve. El error que se pinta es el suyo, no uno inventado.
      salones = await pedir<ResultadoDeBusqueda[]>('/api/v1/publico/negocios/esta-ruta-no-existe-a-proposito');
    } else {
      salones = await api.buscar(filtros);
    }
  } catch (error) {
    return (
      <div className="seccion--corta">
        <Roto
          mensaje={comoMensaje(error)}
          accion={
            <Link className="boton boton--secundario" href="/buscar">
              Volver a la búsqueda
            </Link>
          }
        />
      </div>
    );
  }

  if (salones.length === 0) {
    return (
      <div className="seccion--corta">
        <Vacio
          titulo="Ningún salón cuadra con eso"
          explicacion="Prueba con menos filtros, con otra zona o mirando cualquier día en vez de solo hoy."
          accion={
            <Link className="boton boton--abre" href="/buscar">
              Ver todos los salones
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <section className="seccion--corta" aria-label="Resultados">
      <p className="etiqueta">
        {salones.length} {salones.length === 1 ? 'salón' : 'salones'}
      </p>
      <ul className="lista">
        {salones.map((salon) => (
          <FilaSalon key={salon.negocio_id} salon={salon} />
        ))}
      </ul>
    </section>
  );
}

/** Las zonas salen de los salones publicados: ni una lista escrita a mano. */
async function Zonas({ base, zonaElegida }: { base: Record<string, string | undefined>; zonaElegida?: string }) {
  try {
    const todos = await api.buscar({});
    const zonas = Array.from(new Set(todos.map((salon) => salon.zona).filter((z): z is string => Boolean(z)))).sort();
    if (zonas.length === 0) return <p className="menor">No hay zonas con salones publicados.</p>;
    return (
      <div className="opciones">
        <Enlace base={base} cambio={{ zona: undefined }} elegida={!zonaElegida}>
          Toda la ciudad
        </Enlace>
        {zonas.map((zona) => (
          <Enlace key={zona} base={base} cambio={{ zona: aSlug(zona) }} elegida={zonaElegida === aSlug(zona)}>
            {zona}
          </Enlace>
        ))}
      </div>
    );
  } catch {
    return <p className="menor">No se pudieron cargar las zonas.</p>;
  }
}

function Enlace({
  base,
  cambio,
  elegida,
  children,
}: {
  base: Record<string, string | undefined>;
  cambio: Record<string, string | undefined>;
  elegida: boolean;
  children: React.ReactNode;
}) {
  const parametros = new URLSearchParams();
  const mezcla = { ...base, ...cambio };
  Object.entries(mezcla).forEach(([clave, valor]) => {
    if (valor && !(clave === 'cuando' && valor === 'cualquiera') && !(clave === 'orden' && valor === 'relevancia')) {
      parametros.set(clave, valor);
    }
  });
  const cadena = parametros.toString();
  return (
    <Link className="opcion" data-elegida={elegida ? 'si' : 'no'} href={cadena ? `/buscar?${cadena}` : '/buscar'}>
      {children}
    </Link>
  );
}

function uno(valor: string | string[] | undefined): string | undefined {
  if (Array.isArray(valor)) return valor[0];
  return valor || undefined;
}

function aSlug(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

/** El titular dice lo que se está mirando, en una frase que se pueda leer en voz alta. */
function titulo(texto?: string, categoria?: string, zona?: string, cuando?: string): string {
  const partes: string[] = [];
  if (texto) partes.push(`Salones para «${texto}»`);
  else if (categoria) partes.push(categoria);
  else partes.push('Salones publicados');
  if (zona) partes.push(`en ${zona.replace(/-/g, ' ').replace(/(^|\s)\S/g, (letra) => letra.toUpperCase())}`);
  if (cuando === 'ahora') partes.push('con hueco ahora mismo');
  if (cuando === 'hoy') partes.push('con hueco hoy');
  if (cuando === 'fecha') partes.push('con hueco ese día');
  return partes.join(' ');
}
