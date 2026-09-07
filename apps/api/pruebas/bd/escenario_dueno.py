"""Lo que hace falta montar para probar el portal del dueño.

Se apoya en `escenario_panel`, que ya monta el salón con su equipo, y añade solo lo que aquí se
necesita y allí no existía: un segundo servicio de **otra categoría** —sin él no se puede probar
el filtro del mejor del mes—, citas ya completadas con importe, y un punto en el mapa.

Se inserta con el rol **dueño**, que se salta la seguridad por fila. Es el único sitio donde eso
es correcto: montar el escenario exige crear filas que después, desde el rol de la aplicación,
la prueba tiene que **no** poder ver.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from pruebas.bd.escenario_panel import conexion_de_dueno


async def con_categoria(slug: str, nombre: str) -> uuid.UUID:
    """Una categoría global del catálogo de M2G, creándola si no estaba."""
    async with conexion_de_dueno() as sesion:
        existe = (
            await sesion.execute(
                text("SELECT id FROM service_categories WHERE slug = :slug"), {"slug": slug}
            )
        ).scalar_one_or_none()
        if existe is not None:
            return existe
        return (
            await sesion.execute(
                text(
                    "INSERT INTO service_categories (slug, name) VALUES (:slug, :nombre) "
                    "RETURNING id"
                ),
                {"slug": slug, "nombre": nombre},
            )
        ).scalar_one()


async def con_servicio(
    negocio_id: uuid.UUID,
    *,
    nombre: str,
    minutos: int,
    centavos: int | None,
    categoria_id: uuid.UUID,
    tipo_de_precio: str = "fijo",
) -> uuid.UUID:
    async with conexion_de_dueno() as sesion:
        return (
            await sesion.execute(
                text(
                    """
                    INSERT INTO services (business_id, service_category_id, name, duration_min,
                                          price_kind, price_minor)
                    VALUES (:negocio, :categoria, :nombre, :minutos, :tipo, :centavos)
                    RETURNING id
                    """
                ),
                {
                    "negocio": negocio_id,
                    "categoria": categoria_id,
                    "nombre": nombre,
                    "minutos": minutos,
                    "tipo": tipo_de_precio,
                    "centavos": centavos,
                },
            )
        ).scalar_one()


async def cita_completada(
    negocio_id: uuid.UUID,
    *,
    staff_id: uuid.UUID,
    cliente_id: uuid.UUID,
    servicio_id: uuid.UUID,
    inicio: datetime,
    centavos: int,
    minutos: int = 30,
    nombre_servicio: str = "Servicio",
    tipo_de_precio: str = "fijo",
) -> uuid.UUID:
    """Una cita ya cerrada con su importe **congelado**, como la deja el servicio de reservas.

    No se reutiliza `escenario_panel._cita` porque aquella fija el importe a 18,00 y aquí lo que
    se prueba es justamente que el número que cuenta es el guardado en la cita.
    """
    fin = inicio + timedelta(minutes=minutos)
    async with conexion_de_dueno() as sesion:
        reserva_id = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO bookings (business_id, staff_id, business_client_id, status,
                                          starts_at, ends_at, total_duration_min,
                                          total_amount_minor, source)
                    VALUES (:negocio, :staff, :cliente, 'completada', :inicio, :fin, :minutos,
                            :centavos, 'negocio_manual')
                    RETURNING id
                    """
                ),
                {
                    "negocio": negocio_id,
                    "staff": staff_id,
                    "cliente": cliente_id,
                    "inicio": inicio,
                    "fin": fin,
                    "minutos": minutos,
                    "centavos": centavos,
                },
            )
        ).scalar_one()

        await sesion.execute(
            text(
                """
                INSERT INTO booking_items (business_id, booking_id, position, service_id,
                                           name_snapshot, duration_min_snapshot,
                                           price_kind_snapshot, price_minor_snapshot, currency,
                                           buffer_before_min_snapshot, buffer_after_min_snapshot)
                VALUES (:negocio, :reserva, 1, :servicio, :nombre, :minutos, :tipo,
                        :centavos, 'USD', 0, 0)
                """
            ),
            {
                "negocio": negocio_id,
                "reserva": reserva_id,
                "servicio": servicio_id,
                "nombre": nombre_servicio,
                "minutos": minutos,
                "tipo": tipo_de_precio,
                "centavos": None if tipo_de_precio == "consultar" else centavos,
            },
        )
        # La ocupación de una cita ya pasada se inserta igual: es lo que hace la API, y sin ella
        # el escenario no se parecería al de producción.
        await sesion.execute(
            text(
                """
                INSERT INTO staff_occupancy (business_id, staff_id, kind, status, booking_id,
                                             starts_at, ends_at, buffer_before_min,
                                             buffer_after_min)
                VALUES (:negocio, :staff, 'reserva', 'completada', :reserva, :inicio, :fin, 0, 0)
                """
            ),
            {
                "negocio": negocio_id,
                "staff": staff_id,
                "reserva": reserva_id,
                "inicio": inicio,
                "fin": fin,
            },
        )
    return reserva_id


async def cambiar_precio(negocio_id: uuid.UUID, servicio_id: uuid.UUID, centavos: int) -> None:
    """Sube el precio del catálogo **sin tocar las citas ya hechas**, que es lo normal."""
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("UPDATE services SET price_minor = :centavos WHERE id = :servicio"),
            {"centavos": centavos, "servicio": servicio_id},
        )
        assert negocio_id is not None


async def con_punto(negocio_id: uuid.UUID, *, longitud: float, latitud: float) -> uuid.UUID:
    """Le pone una sede con su punto geográfico. Sin ella el salón no sale en el mapa."""
    async with conexion_de_dueno() as sesion:
        return (
            await sesion.execute(
                text(
                    """
                    INSERT INTO locations (business_id, address_line, geo)
                    VALUES (:negocio, 'Vía España', ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
                    RETURNING id
                    """
                ),
                {"negocio": negocio_id, "lon": longitud, "lat": latitud},
            )
        ).scalar_one()


async def encender_fichaje(negocio_id: uuid.UUID, staff_id: uuid.UUID, activo: bool) -> None:
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text(
                "UPDATE staff_profiles SET clock_in_enabled = :activo "
                "WHERE id = :staff AND business_id = :negocio"
            ),
            {"activo": activo, "staff": staff_id, "negocio": negocio_id},
        )


async def despublicar(negocio_id: uuid.UUID) -> None:
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("UPDATE businesses SET status = 'borrador' WHERE id = :negocio"),
            {"negocio": negocio_id},
        )


def hace(dias: int, *, hora: int = 10) -> datetime:
    """Un instante de hace tantos días, a esa hora UTC. Siempre en el pasado, como una cita
    completada tiene que estar."""
    base = datetime.now(UTC) - timedelta(days=dias)
    return base.replace(hour=hora, minute=0, second=0, microsecond=0)
