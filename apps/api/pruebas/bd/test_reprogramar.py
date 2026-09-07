"""Mover una cita de hora, y **a quién** se le pasa.

Crear una cita ya comprobaba que el profesional siguiera activo; moverla no. Se podía asignar una
cita a alguien que ya no trabaja en el salón: el día de la cita no habría nadie, y esa persona ni
siquiera puede verla, porque al darla de baja se le revoca la membresía.

Se llegaba justo siguiendo el consejo que da la propia baja forzada —«muévelas»— y eligiendo mal.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.errores import ServicioNoDisponible
from agenda.modelos.reservas import Booking
from agenda.servicios import reservas as servicio_reservas
from agenda.servicios.reservas import Actor
from pruebas.bd.conftest import URL_APP
from pruebas.bd.escenario_panel import conexion_de_dueno, manana_a_las, montar_salon

pytestmark = pytest.mark.bd


@asynccontextmanager
async def transaccion_del_negocio(motor, negocio_id) -> AsyncIterator[AsyncSession]:
    """Una transacción con el tenant fijado.

    El `set_config` va **dentro** de la transacción y no antes: `true` en el tercer argumento
    significa «solo para esta transacción», y ejecutarlo suelto abre una implícita que después
    impide abrir la de verdad.
    """
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    async with crear() as sesion, sesion.begin():
        await sesion.execute(
            text("SELECT set_config('app.current_business_id', :negocio, true)"),
            {"negocio": str(negocio_id)},
        )
        yield sesion


async def test_no_se_le_puede_pasar_una_cita_a_quien_esta_de_baja():
    salon = await montar_salon()

    async with conexion_de_dueno() as duenno:
        # Marielys se va del salón: baja lógica, como la que hace el panel.
        await duenno.execute(
            text(
                "UPDATE staff_profiles SET active = false, visible_in_marketplace = false,"
                " deleted_at = now() WHERE id = :id"
            ),
            {"id": salon.marielys.id},
        )

    motor = create_async_engine(URL_APP, poolclass=None)
    try:
        with pytest.raises(ServicioNoDisponible):
            async with transaccion_del_negocio(motor, salon.negocio_id) as sesion:
                cita = await sesion.get(Booking, salon.cita_de_kevin)
                await servicio_reservas.reprogramar(
                    sesion,
                    cita,
                    nuevo_inicio=manana_a_las(12),
                    nuevo_staff_id=salon.marielys.id,
                    actor=Actor.NEGOCIO,
                )

        # Y lo que importa de verdad: la cita **no se movió**. Un rechazo que deja la mitad
        # hecha es peor que no rechazar.
        async with transaccion_del_negocio(motor, salon.negocio_id) as sesion:
            sin_tocar = await sesion.get(Booking, salon.cita_de_kevin)
            assert sin_tocar.staff_id == salon.kevin.id
    finally:
        await motor.dispose()


async def test_moverla_a_alguien_que_si_trabaja_ahi_funciona():
    """La otra mitad: el rechazo no puede haberse llevado por delante el camino bueno."""
    salon = await montar_salon()
    motor = create_async_engine(URL_APP, poolclass=None)
    nueva_hora = manana_a_las(16)
    try:
        async with transaccion_del_negocio(motor, salon.negocio_id) as sesion:
            cita = await sesion.get(Booking, salon.cita_de_kevin)
            await servicio_reservas.reprogramar(
                sesion,
                cita,
                nuevo_inicio=nueva_hora,
                nuevo_staff_id=salon.marielys.id,
                actor=Actor.NEGOCIO,
            )

        async with transaccion_del_negocio(motor, salon.negocio_id) as sesion:
            movida = await sesion.get(Booking, salon.cita_de_kevin)
            assert movida.staff_id == salon.marielys.id
            assert movida.starts_at == nueva_hora
            # La ocupación tiene que haberse movido con ella, o la hora vieja se queda cogida
            # para siempre y la nueva libre para que alguien se cuele encima.
            ocupada = (
                await sesion.execute(
                    text("SELECT staff_id, starts_at FROM staff_occupancy WHERE booking_id = :id"),
                    {"id": str(movida.id)},
                )
            ).one()
            assert ocupada[0] == salon.marielys.id
            assert ocupada[1] == nueva_hora
    finally:
        await motor.dispose()
