"""El fichaje: apagado por defecto, persona a persona y **nunca público** (punto 6 del encargo).

Aquí se prueban tres cosas que solo existen dentro de PostgreSQL y que, si se rompieran, no
harían fallar nada:

1. **El interruptor del dueño está en la política de escritura.** No basta con que la pantalla
   no ofrezca el botón: si `clock_in_enabled` está apagado, la base rechaza la fila. Se prueba
   insertando **a mano**, sin pasar por el servicio, que es lo que haría un endpoint futuro que
   se olvide de mirar el interruptor.
2. **`staff_clock_events` no es pública jamás.** No tiene política para `agenda_publico` y
   además se le revocó el permiso, porque los privilegios por defecto de la base conceden
   `SELECT` al rol público sobre toda tabla nueva.
3. **Es append-only.** El rol de la aplicación no tiene `UPDATE` ni `DELETE`: un registro
   horario que se puede reescribir no prueba nada.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.errores import NoAutorizado
from agenda.servicios import fichaje as servicio_fichaje
from pruebas.bd.conftest import URL_APP
from pruebas.bd.escenario_dueno import encender_fichaje
from pruebas.bd.escenario_panel import montar_salon

pytestmark = pytest.mark.bd

URL_PUBLICA = URL_APP.replace("agenda_api:", "agenda_publico:")


@asynccontextmanager
async def _como(
    motor, negocio_id: uuid.UUID, staff_id: uuid.UUID | None = None
) -> AsyncIterator[AsyncSession]:
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


@asynccontextmanager
async def _publica() -> AsyncIterator[AsyncSession]:
    motor = create_async_engine(URL_PUBLICA, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    try:
        async with crear() as sesion, sesion.begin():
            yield sesion
    finally:
        await motor.dispose()


async def test_el_fichaje_nace_apagado(motor):
    """**Apagado por defecto.** Es la mitad del encargo: lo contrario se lee como vigilancia."""
    salon = await montar_salon()

    async with _como(motor, salon.negocio_id) as sesion:
        encendidos = (
            await sesion.execute(text("SELECT count(*) FROM staff_profiles WHERE clock_in_enabled"))
        ).scalar_one()

    assert encendidos == 0, "Un salón nuevo ha nacido con el fichaje encendido para alguien."


async def test_sin_el_interruptor_la_base_rechaza_el_fichaje(motor):
    """La comprobación de verdad está en la política, no en el servicio.

    Esta inserción es **a mano y sin pasar por el servicio**: es exactamente lo que haría un
    endpoint escrito dentro de seis meses por alguien que no sabe que el interruptor existe. Si
    esta prueba pasa a verde tras quitar el `EXISTS` de la política de la migración 0010, la
    garantía era un `if` disfrazado.
    """
    salon = await montar_salon()

    async with _como(motor, salon.negocio_id) as sesion:
        with pytest.raises((DBAPIError, ProgrammingError)):
            await sesion.execute(
                text(
                    "INSERT INTO staff_clock_events (business_id, staff_id, kind) "
                    "VALUES (:negocio, :staff, 'entrada')"
                ),
                {"negocio": salon.negocio_id, "staff": salon.kevin.id},
            )


async def test_con_el_interruptor_encendido_si_se_ficha(motor):
    """Y encendido funciona, para que la prueba anterior signifique algo."""
    salon = await montar_salon()
    await encender_fichaje(salon.negocio_id, salon.kevin.id, True)

    async with _como(motor, salon.negocio_id, salon.kevin.id) as sesion:
        entrada = await servicio_fichaje.fichar(
            sesion,
            negocio_id=salon.negocio_id,
            profesional_id=salon.kevin.id,
            clase="entrada",
            instante=datetime.now(UTC) - timedelta(hours=3),
        )
        salida = await servicio_fichaje.fichar(
            sesion,
            negocio_id=salon.negocio_id,
            profesional_id=salon.kevin.id,
            clase="salida",
            instante=datetime.now(UTC) - timedelta(hours=1),
        )
        partes = await servicio_fichaje.partes(
            sesion,
            negocio_id=salon.negocio_id,
            desde=datetime.now(UTC) - timedelta(days=1),
            hasta=datetime.now(UTC) + timedelta(hours=1),
        )

    assert entrada.clase == "entrada" and salida.clase == "salida"
    assert len(partes) == 1
    assert partes[0].minutos_trabajados == 120
    assert partes[0].jornada_abierta is False


async def test_el_servicio_avisa_antes_de_que_lo_haga_la_base(motor):
    """El mensaje importa: un `403` de PostgreSQL no explica de quién depende encenderlo."""
    salon = await montar_salon()

    async with _como(motor, salon.negocio_id) as sesion:
        with pytest.raises(NoAutorizado):
            await servicio_fichaje.fichar(
                sesion,
                negocio_id=salon.negocio_id,
                profesional_id=salon.kevin.id,
                clase="entrada",
            )


async def test_un_profesional_no_ve_el_fichaje_de_su_companera(motor):
    """Quién entró y salió cada día es de la persona y del dueño; entre compañeros, no.

    La consulta va **sin filtrar por profesional** a propósito: lo que se comprueba es si la
    base lo impide, no si el endpoint se acuerda de filtrar.
    """
    salon = await montar_salon()
    await encender_fichaje(salon.negocio_id, salon.kevin.id, True)
    await encender_fichaje(salon.negocio_id, salon.marielys.id, True)

    async with _como(motor, salon.negocio_id) as sesion:
        for staff in (salon.kevin.id, salon.marielys.id):
            await sesion.execute(
                text(
                    "INSERT INTO staff_clock_events (business_id, staff_id, kind) "
                    "VALUES (:negocio, :staff, 'entrada')"
                ),
                {"negocio": salon.negocio_id, "staff": staff},
            )

    async with _como(motor, salon.negocio_id, salon.kevin.id) as sesion:
        vistos = {
            fila[0]
            for fila in await sesion.execute(text("SELECT staff_id FROM staff_clock_events"))
        }
    assert vistos <= {salon.kevin.id}, f"Ha visto fichajes ajenos: {vistos}"

    async with _como(motor, salon.negocio_id) as sesion:
        del_dueno = {
            fila[0]
            for fila in await sesion.execute(text("SELECT staff_id FROM staff_clock_events"))
        }
    assert del_dueno == {
        salon.kevin.id,
        salon.marielys.id,
    }, "El dueño tiene que ver el parte entero; si no, la política se pasó de estricta."


async def test_un_profesional_no_puede_fichar_por_otro(motor):
    """Y tampoco es el endpoint quien lo impide: la fila con el identificador de otra persona
    no entra."""
    salon = await montar_salon()
    await encender_fichaje(salon.negocio_id, salon.marielys.id, True)

    async with _como(motor, salon.negocio_id, salon.kevin.id) as sesion:
        with pytest.raises((DBAPIError, ProgrammingError)):
            await sesion.execute(
                text(
                    "INSERT INTO staff_clock_events (business_id, staff_id, kind) "
                    "VALUES (:negocio, :staff, 'entrada')"
                ),
                {"negocio": salon.negocio_id, "staff": salon.marielys.id},
            )


async def test_el_fichaje_no_es_publico_ni_por_permiso_ni_por_politica():
    """**Dato laboral.** Ni una fila para el rol del marketplace, y ni siquiera permiso de lectura.

    Se comprueban las dos cosas por separado porque fallan distinto: sin política, la consulta
    devuelve cero filas y parece que funciona; sin revocar el permiso, la tabla queda a un
    `CREATE POLICY` de distancia de ser pública.
    """
    async with _publica() as sesion:
        permiso = (
            await sesion.execute(
                text("SELECT has_table_privilege('agenda_publico', 'staff_clock_events', 'SELECT')")
            )
        ).scalar_one()
        politicas = (
            await sesion.execute(
                text(
                    "SELECT count(*) FROM pg_policy p "
                    "WHERE p.polrelid = 'staff_clock_events'::regclass "
                    "  AND 'agenda_publico'::regrole = ANY(p.polroles)"
                )
            )
        ).scalar_one()

    assert permiso is False, "El rol del marketplace tiene permiso de lectura sobre el fichaje."
    assert politicas == 0, "Hay una política que le abre el fichaje al rol del marketplace."


async def test_el_fichaje_es_append_only(motor):
    """Ni `UPDATE` ni `DELETE` para el rol de la aplicación, como `booking_events`."""
    async with _como(motor, uuid.uuid4()) as sesion:
        privilegios = (
            await sesion.execute(
                text(
                    "SELECT has_table_privilege('staff_clock_events', 'UPDATE'), "
                    "       has_table_privilege('staff_clock_events', 'DELETE'), "
                    "       has_table_privilege('staff_clock_events', 'INSERT'), "
                    "       has_table_privilege('staff_clock_events', 'SELECT')"
                )
            )
        ).one()

    puede_actualizar, puede_borrar, puede_insertar, puede_leer = privilegios
    assert (
        not puede_actualizar and not puede_borrar
    ), "El fichaje se puede reescribir: entonces no prueba nada."
    assert puede_insertar and puede_leer


async def test_el_fichaje_de_un_salon_no_se_ve_desde_otro(motor):
    """El aislamiento entre negocios también aquí, y con la consulta sin filtro."""
    uno = await montar_salon()
    otro = await montar_salon()
    await encender_fichaje(otro.negocio_id, otro.kevin.id, True)

    async with _como(motor, otro.negocio_id) as sesion:
        await sesion.execute(
            text(
                "INSERT INTO staff_clock_events (business_id, staff_id, kind) "
                "VALUES (:negocio, :staff, 'entrada')"
            ),
            {"negocio": otro.negocio_id, "staff": otro.kevin.id},
        )

    async with _como(motor, uno.negocio_id) as sesion:
        total = (await sesion.execute(text("SELECT count(*) FROM staff_clock_events"))).scalar_one()
    assert total == 0, "Se ha visto el fichaje de otro salón."
