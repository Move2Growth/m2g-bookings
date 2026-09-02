"""Un profesional ve su agenda y **solo** su agenda (STF-3, migración 0006).

Esta es la hermana pequeña de la prueba de aislamiento entre negocios, y se rompe igual de
callada: dentro de un mismo salón, un profesional que ve las citas de su compañera no hace
saltar ningún error — devuelve de más y nadie se entera hasta que alguien lo cuenta.

Lo que se comprueba aquí **no es el `WHERE` del endpoint**: es si la base de datos deja ver lo
ajeno cuando el filtro del código no está. Por eso todas las consultas se escriben a propósito
sin filtrar por profesional. Si estas pruebas pasan, un endpoint nuevo que se olvide de
comprobar el rol sigue sin poder filtrar la agenda de nadie.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pruebas.bd.escenario_panel import manana_a_las, montar_salon

pytestmark = pytest.mark.bd


@asynccontextmanager
async def _como_profesional(
    motor, negocio_id: uuid.UUID, staff_id: uuid.UUID | None
) -> AsyncIterator[AsyncSession]:
    """Abre la sesión igual que la dependencia de la API: negocio y, si toca, profesional.

    `staff_id` a `None` es el dueño: declara el negocio y nada más, y por eso las políticas
    restrictivas no le estorban.
    """
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    async with crear() as sesion, sesion.begin():
        await sesion.execute(
            text("SELECT set_config('app.current_business_id', :negocio, true)"),
            {"negocio": str(negocio_id)},
        )
        if staff_id is not None:
            await sesion.execute(
                text("SELECT set_config('app.current_staff_id', :staff, true)"),
                {"staff": str(staff_id)},
            )
        yield sesion


async def test_un_select_sin_where_solo_ve_las_citas_propias(motor):
    """El caso que motiva todo: alguien escribe la consulta y se olvida de filtrar por staff."""
    salon = await montar_salon()

    async with _como_profesional(motor, salon.negocio_id, salon.kevin.id) as sesion:
        vistos = {fila[0] for fila in await sesion.execute(text("SELECT staff_id FROM bookings"))}

    assert vistos <= {salon.kevin.id}, (
        "Un profesional ha visto citas de otro con una consulta sin filtro. "
        f"Vistos: {vistos}; esperado como mucho: {salon.kevin.id}."
    )


async def test_pedir_la_cita_ajena_por_su_identificador_tampoco_la_ensena(motor):
    """Ni nombrando el identificador: la política no es un filtro sugerido."""
    salon = await montar_salon()

    async with _como_profesional(motor, salon.negocio_id, salon.kevin.id) as sesion:
        total = (
            await sesion.execute(
                text("SELECT count(*) FROM bookings WHERE id = :cita"),
                {"cita": salon.cita_de_marielys},
            )
        ).scalar_one()

    assert total == 0, "La cita de otra profesional es visible pidiéndola por su identificador."


async def test_el_dueno_si_ve_la_agenda_entera(motor):
    """La restricción es del profesional, no del salón: el dueño sigue viéndolo todo.

    Sin esta prueba, una política demasiado estricta dejaría al dueño sin panel y el fallo se
    descubriría al abrir la agenda un lunes por la mañana.
    """
    salon = await montar_salon()

    async with _como_profesional(motor, salon.negocio_id, None) as sesion:
        vistos = {fila[0] for fila in await sesion.execute(text("SELECT staff_id FROM bookings"))}

    assert vistos == {salon.kevin.id, salon.marielys.id}


async def test_la_ocupacion_ajena_tampoco_se_ve(motor):
    """`staff_occupancy` es donde vive de verdad la agenda: si se ve, se ve todo.

    Es la tabla que consulta el motor de disponibilidad, así que dejarla abierta contaría a
    quien mira cuándo está ocupada su compañera aunque las citas estuvieran tapadas.
    """
    salon = await montar_salon()

    async with _como_profesional(motor, salon.negocio_id, salon.marielys.id) as sesion:
        vistos = {
            fila[0] for fila in await sesion.execute(text("SELECT staff_id FROM staff_occupancy"))
        }

    assert vistos <= {salon.marielys.id}


async def test_el_detalle_de_la_cita_ajena_tampoco_se_ve(motor):
    """`booking_items` cuelga de la reserva y hereda su dueño.

    Sin esto, la cita no se vería pero sí qué servicio se hizo y cuánto costó, que es justo el
    dato por el que alguien miraría la agenda de otro.
    """
    salon = await montar_salon()

    async with _como_profesional(motor, salon.negocio_id, salon.kevin.id) as sesion:
        total = (
            await sesion.execute(
                text("SELECT count(*) FROM booking_items WHERE booking_id = :cita"),
                {"cita": salon.cita_de_marielys},
            )
        ).scalar_one()

    assert total == 0


async def test_un_profesional_no_puede_mover_la_cita_de_otro(motor):
    """No basta con no verla: tampoco se puede escribir sobre ella «a ciegas».

    Un `UPDATE` sin `SELECT` previo es exactamente lo que haría un endpoint mal escrito, y con
    la política puesta no toca ninguna fila en vez de mover la cita de la compañera.
    """
    salon = await montar_salon()

    async with _como_profesional(motor, salon.negocio_id, salon.kevin.id) as sesion:
        resultado = await sesion.execute(
            text("UPDATE bookings SET starts_at = starts_at + interval '1 hour' WHERE id = :cita"),
            {"cita": salon.cita_de_marielys},
        )
        assert resultado.rowcount == 0

    # Y la cita sigue donde estaba, comprobado desde fuera de la sesión del profesional.
    async with _como_profesional(motor, salon.negocio_id, None) as sesion:
        hora = (
            await sesion.execute(
                text("SELECT starts_at FROM bookings WHERE id = :cita"),
                {"cita": salon.cita_de_marielys},
            )
        ).scalar_one()
    assert hora == manana_a_las(11)


async def test_un_profesional_no_puede_agendarse_una_cita_a_nombre_de_otro(motor):
    """La escritura también está acotada: `WITH CHECK` mira la fila **que entra**.

    Sin esta mitad, un profesional no vería la agenda ajena pero podría llenarla, que es peor:
    aparecen citas que nadie sabe de dónde salieron.
    """
    salon = await montar_salon()

    async with _como_profesional(motor, salon.negocio_id, salon.kevin.id) as sesion:
        with pytest.raises(DBAPIError) as fallo:
            await sesion.execute(
                text(
                    """
                    INSERT INTO bookings (business_id, staff_id, business_client_id, status,
                                          starts_at, ends_at, total_duration_min, source)
                    VALUES (:negocio, :staff, :cliente, 'confirmada', :inicio, :fin, 45,
                            'negocio_manual')
                    """
                ),
                {
                    "negocio": salon.negocio_id,
                    "staff": salon.marielys.id,
                    "cliente": salon.cliente_de_marielys,
                    "inicio": manana_a_las(16),
                    "fin": manana_a_las(17),
                },
            )
    assert "row-level security" in str(fallo.value).lower()


async def test_un_profesional_no_puede_cambiar_el_precio_de_un_servicio(motor):
    """La configuración es del dueño (STF-3). Leer sí; escribir, no.

    Leer hace falta —el profesional tiene que saber de qué es la cita de las diez— y por eso la
    política restrictiva solo cierra `INSERT`, `UPDATE` y `DELETE`.
    """
    salon = await montar_salon()

    async with _como_profesional(motor, salon.negocio_id, salon.kevin.id) as sesion:
        # Leer: sí.
        precio = (
            await sesion.execute(
                text("SELECT price_minor FROM services WHERE id = :servicio"),
                {"servicio": salon.servicio_id},
            )
        ).scalar_one()
        assert precio == 1800

        # Escribir: la fila no existe para él, así que el UPDATE no toca nada.
        resultado = await sesion.execute(
            text("UPDATE services SET price_minor = 9900 WHERE id = :servicio"),
            {"servicio": salon.servicio_id},
        )
        assert resultado.rowcount == 0


async def test_un_profesional_no_ve_las_facturas_del_salon(motor):
    """Las finanzas no se recortan: se cierran. Ni lectura (STF-3)."""
    salon = await montar_salon()

    async with _como_profesional(motor, salon.negocio_id, salon.kevin.id) as sesion:
        total = (await sesion.execute(text("SELECT count(*) FROM invoices"))).scalar_one()
        suscripciones = (
            await sesion.execute(text("SELECT count(*) FROM subscriptions"))
        ).scalar_one()

    assert total == 0
    assert suscripciones == 0


async def test_un_profesional_solo_ve_las_fichas_de_sus_clientes(motor):
    """«Su agenda y sus clientes» (STF-3): suyo = te ha reservado alguna vez.

    Las notas que el barbero escribe sobre una clienta son de esa relación, no del salón
    entero; y el teléfono de la clienta de la compañera no tiene por qué estar a un `SELECT`
    de distancia.
    """
    salon = await montar_salon()

    async with _como_profesional(motor, salon.negocio_id, salon.kevin.id) as sesion:
        vistos = {fila[0] for fila in await sesion.execute(text("SELECT id FROM business_clients"))}

    assert salon.cliente_de_kevin in vistos
    assert salon.cliente_de_marielys not in vistos
