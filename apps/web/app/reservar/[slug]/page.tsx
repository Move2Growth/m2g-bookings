import Link from 'next/link';

import { Roto, Vacio } from '@/componentes/estados';
import { Reserva } from '@/componentes/reserva';
import { api, comoMensaje, FalloDeApi, type PerfilPublico, type ProfesionalDelEquipo } from '@/lib/api';

/**
 * Reservar.
 *
 * La carta del salón y el equipo se piden en el servidor —son estables y no dependen de quién
 * mire—; lo que cambia con cada toque —las horas libres, la sesión, el envío— lo lleva
 * `<Reserva>` en el navegador, porque una agenda pedida en el servidor y cacheada es una
 * agenda mentirosa.
 */

export const metadata = { title: 'Reservar' };

export default async function PantallaDeReserva({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { slug } = await params;
  const consulta = await searchParams;

  let salon: PerfilPublico;
  let equipo: ProfesionalDelEquipo[];
  try {
    [salon, equipo] = await Promise.all([api.ficha(slug), api.equipo(slug)]);
  } catch (error) {
    const noExiste = error instanceof FalloDeApi && error.estado === 404;
    return (
      <div className="contenido seccion">
        {noExiste ? (
          <Vacio
            titulo="Aquí no se puede reservar"
            explicacion={comoMensaje(error)}
            accion={
              <Link className="boton boton--abre" href="/buscar">
                Buscar otro salón
              </Link>
            }
          />
        ) : (
          <Roto mensaje={comoMensaje(error)} />
        )}
      </div>
    );
  }

  if (salon.servicios.length === 0 || equipo.length === 0) {
    return (
      <div className="contenido seccion">
        <Vacio
          titulo="Este salón todavía no acepta reservas"
          explicacion={
            salon.servicios.length === 0
              ? 'No ha dado de alta ningún servicio, así que no hay nada que reservar.'
              : 'No tiene a nadie publicado en el equipo, y una cita siempre es con alguien.'
          }
          accion={
            <Link className="boton boton--abre" href={`/salon/${slug}`}>
              Volver a la ficha
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <Reserva
      salon={salon}
      equipo={equipo}
      inicial={{
        servicio: uno(consulta.servicio),
        profesional: uno(consulta.profesional),
        dia: uno(consulta.dia),
        inicio: uno(consulta.inicio),
      }}
    />
  );
}

function uno(valor: string | string[] | undefined): string | undefined {
  if (Array.isArray(valor)) return valor[0];
  return valor || undefined;
}
