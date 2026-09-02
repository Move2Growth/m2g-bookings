"""La garantía nº 2: **no puede existir una doble reserva**.

Estas son las pruebas que el encargo pide explícitamente y que no se pueden escribir de otra
manera: *«Dos clientes confirmando el mismo slot a la vez. Bajo carga, no en teoría. Que no
haya doble reserva es transaccional, no un `if`.»*

Por eso aquí no se llama a ninguna función de Python que decida nada. Se abren **dos
transacciones de verdad contra PostgreSQL**, se hacen chocar, y se comprueba que la base deja
pasar exactamente una. Si algún día alguien reescribe el código de reservas y se le olvida
comprobar la disponibilidad, estas pruebas siguen pasando —y ese es justamente el objetivo del
diseño (ADR-0004): que el error de aplicación no pueda convertirse en dos personas sentadas en
la misma silla.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from pruebas.bd.escenario import (
    URL_DUENO_ASYNC,
    crear_cita,
    manana_a_las,
    montar_escenario,
)

pytestmark = [pytest.mark.bd, pytest.mark.concurrencia]

#: Código de PostgreSQL para «violación de restricción de exclusión». Es el que la API traduce
#: a `SLOT_NO_DISPONIBLE` con HTTP 409.
EXCLUSION_VIOLADA = "23P01"


def es_solape(error: Exception) -> bool:
    return getattr(getattr(error, "orig", None), "sqlstate", None) == EXCLUSION_VIOLADA or (
        EXCLUSION_VIOLADA in str(error)
    )


async def test_dos_clientes_a_la_vez_por_el_mismo_slot_solo_gana_uno():
    """Dos transacciones simultáneas, el mismo profesional, la misma hora.

    No es «una detrás de otra»: las dos abren transacción, las dos insertan, y la segunda se
    queda bloqueada hasta que la primera confirma. Es exactamente lo que pasa cuando un salón
    comparte su enlace por WhatsApp y dos personas tocan «confirmar» en el mismo segundo.
    """
    escenario = await montar_escenario()
    hora = manana_a_las(10)

    motor = create_async_engine(URL_DUENO_ASYNC, poolclass=None)
    try:

        async def intentar() -> str:
            try:
                async with motor.begin() as conexion:
                    await crear_cita(conexion, escenario.cangrejo, inicio=hora)
                return "creada"
            except IntegrityError as error:
                if es_solape(error):
                    return "rechazada"
                raise

        resultados = await asyncio.gather(intentar(), intentar())

        assert sorted(resultados) == ["creada", "rechazada"], (
            f"Las dos transacciones acabaron así: {resultados}. "
            "Si las dos dicen 'creada', hay dos personas citadas a la misma hora."
        )
    finally:
        await motor.dispose()


async def test_la_restriccion_aguanta_diez_intentos_simultaneos():
    """Con diez a la vez sigue habiendo una sola cita. La carrera no se resuelve por suerte."""
    escenario = await montar_escenario()
    hora = manana_a_las(11)

    motor = create_async_engine(URL_DUENO_ASYNC, poolclass=None)
    try:

        async def intentar() -> bool:
            try:
                async with motor.begin() as conexion:
                    await crear_cita(conexion, escenario.cangrejo, inicio=hora)
                return True
            except IntegrityError as error:
                if es_solape(error):
                    return False
                raise

        resultados = await asyncio.gather(*(intentar() for _ in range(10)))

        assert sum(resultados) == 1, f"Se crearon {sum(resultados)} citas para la misma hora."
    finally:
        await motor.dispose()


async def test_los_buffers_tambien_estan_protegidos_por_la_base():
    """Una cita pegada al final de otra viola el buffer, y la base lo impide.

    Es la razón de que la exclusión mire `blocked_from`/`blocked_to` y no `starts_at`/`ends_at`:
    si mirara solo el servicio, al barbero se le juntarían dos personas porque le faltan los
    diez minutos de limpieza, y la base no se habría enterado de nada.
    """
    escenario = await montar_escenario()
    primera = manana_a_las(12)

    motor = create_async_engine(URL_DUENO_ASYNC, poolclass=None)
    try:
        async with motor.begin() as conexion:
            await crear_cita(
                conexion, escenario.cangrejo, inicio=primera, minutos=45, buffer_despues=10
            )

        with pytest.raises(IntegrityError) as error:
            async with motor.begin() as conexion:
                # Empieza a los 45 minutos exactos: el servicio no solapa, pero el buffer sí.
                await crear_cita(
                    conexion, escenario.cangrejo, inicio=primera + timedelta(minutes=45)
                )

        assert es_solape(error.value)
    finally:
        await motor.dispose()


async def test_dos_citas_pegadas_sin_buffer_si_caben():
    """El rango es semiabierto: lo que acaba a las 14:00 y lo que empieza a las 14:00 conviven.

    Es el espejo de la prueba anterior y hace falta: una restricción que rechazara esto haría
    perder un hueco cada hora, y nadie entendería por qué.
    """
    escenario = await montar_escenario()
    primera = manana_a_las(14)

    motor = create_async_engine(URL_DUENO_ASYNC, poolclass=None)
    try:
        async with motor.begin() as conexion:
            await crear_cita(conexion, escenario.cangrejo, inicio=primera, minutos=60)
        async with motor.begin() as conexion:
            await crear_cita(
                conexion, escenario.cangrejo, inicio=primera + timedelta(hours=1), minutos=60
            )
    finally:
        await motor.dispose()


async def test_cancelar_libera_el_hueco_sin_borrar_la_fila():
    """Una cita cancelada deja de ocupar agenda **de inmediato** y su fila se conserva.

    El negocio necesita el historial —y el contador de no-shows del cliente vive de él—, pero
    el hueco tiene que volver a estar disponible en la misma transacción.
    """
    escenario = await montar_escenario()
    hora = manana_a_las(16)

    motor = create_async_engine(URL_DUENO_ASYNC, poolclass=None)
    try:
        async with motor.begin() as conexion:
            ocupacion_id = await crear_cita(conexion, escenario.cangrejo, inicio=hora)

        async with motor.begin() as conexion:
            await conexion.execute(
                text(
                    """
                    UPDATE bookings SET status = 'cancelada_cliente', cancelled_at = now()
                    WHERE id = (SELECT booking_id FROM staff_occupancy WHERE id = :ocupacion)
                    """
                ),
                {"ocupacion": ocupacion_id},
            )

        # El hueco vuelve a estar libre…
        async with motor.begin() as conexion:
            await crear_cita(conexion, escenario.cangrejo, inicio=hora)

        # …y la fila cancelada sigue ahí, con su estado espejado por el disparador.
        async with motor.connect() as conexion:
            estado = (
                await conexion.execute(
                    text("SELECT status FROM staff_occupancy WHERE id = :id"),
                    {"id": ocupacion_id},
                )
            ).scalar_one()

        assert estado == "cancelada_cliente", (
            "La ocupación no siguió al estado de la reserva: el disparador que las mantiene en "
            "espejo no está haciendo su trabajo, y el motor y la base dejarían de estar de "
            "acuerdo sobre qué está ocupado."
        )
    finally:
        await motor.dispose()
