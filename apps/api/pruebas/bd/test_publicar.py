"""Quién puede devolver un salón al marketplace.

Suspender es una decisión de moderación: se toma en la consola, con un motivo escrito y dejando
fila en la auditoría. Publicar, en cambio, era un `UPDATE` a «publicado» que no miraba de dónde
se venía, así que **el salón suspendido se reactivaba solo con que su dueño pulsara el botón de
siempre**. Reproducido contra el entorno local: se suspende el Spa Costa del Este desde la
consola, la ficha pública pasa a 404, el dueño llama a `POST /negocio/publicar` y responde 200
con estado «publicado». La fila quedaba además diciendo dos cosas a la vez —estado «publicado»
con `suspended_at` y motivo puestos—, que es justo lo que después lee la consola.

Para creerse estas dos pruebas hay que poder romperlas: quitando la comprobación de
`onboarding.publicar`, `test_el_dueno_no_levanta_una_suspension_de_la_plataforma` pasa a
devolver el salón publicado y falla. Por eso el escenario cumple **entero** el mínimo de D11
—servicio, horario, ubicación y foto—: si no, el salón no se publicaría de todas formas y la
prueba pasaría por el motivo equivocado.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.api import onboarding as api_onboarding
from agenda.api.dependencias import Identidad
from agenda.errores import FaltaMinimoParaPublicar, SuspendidoPorLaPlataforma
from pruebas.bd.conftest import URL_APP
from pruebas.bd.escenario_panel import conexion_de_dueno, montar_salon

pytestmark = pytest.mark.bd


@asynccontextmanager
async def como_dueno(
    negocio_id: uuid.UUID, usuario_id: uuid.UUID
) -> AsyncIterator[tuple[AsyncSession, Identidad]]:
    """La sesión de `/negocio/…`, con el tenant fijado como lo fija `dependencias.py`."""
    motor = create_async_engine(URL_APP, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    identidad = Identidad(usuario_id=usuario_id, negocio_id=negocio_id, rol="dueno")
    try:
        async with crear() as sesion, sesion.begin():
            await sesion.execute(
                text("SELECT set_config('app.current_business_id', :negocio, true)"),
                {"negocio": str(negocio_id)},
            )
            yield sesion, identidad
    finally:
        await motor.dispose()


async def completar_el_minimo(negocio_id: uuid.UUID) -> None:
    """Horario, ubicación y foto: lo que le falta al escenario para cumplir D11."""
    async with conexion_de_dueno() as sesion:
        for dia in range(5):
            await sesion.execute(
                text(
                    """
                    INSERT INTO business_hours (business_id, weekday, opens_at, closes_at)
                    VALUES (:negocio, :dia, '09:00', '18:00')
                    """
                ),
                {"negocio": negocio_id, "dia": dia},
            )
        await sesion.execute(
            text(
                """
                INSERT INTO locations (business_id, address_line, geo)
                VALUES (:negocio, 'Calle 47, El Cangrejo',
                        ST_SetSRID(ST_MakePoint(-79.52, 8.98), 4326))
                """
            ),
            {"negocio": negocio_id},
        )
        await sesion.execute(
            text(
                """
                INSERT INTO business_media (business_id, storage_key, kind, moderation_status)
                VALUES (:negocio, '/fotos/spa.webp', 'portada', 'aprobada')
                """
            ),
            {"negocio": negocio_id},
        )


async def poner_estado(negocio_id: uuid.UUID, estado: str, motivo: str | None = None) -> None:
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text(
                """
                UPDATE businesses
                   SET status = :estado,
                       suspended_at = CASE WHEN :estado = 'suspendido' THEN now() END,
                       suspension_reason = :motivo
                 WHERE id = :negocio
                """
            ),
            {"negocio": negocio_id, "estado": estado, "motivo": motivo},
        )


async def estado_de(negocio_id: uuid.UUID) -> tuple[str, bool]:
    """El estado y si le queda rastro de suspensión encima."""
    async with conexion_de_dueno() as sesion:
        fila = (
            await sesion.execute(
                text("SELECT status, suspended_at FROM businesses WHERE id = :negocio"),
                {"negocio": negocio_id},
            )
        ).one()
    return fila[0], fila[1] is not None


@pytest.mark.asyncio
async def test_el_dueno_no_levanta_una_suspension_de_la_plataforma() -> None:
    salon = await montar_salon()
    await completar_el_minimo(salon.negocio_id)
    await poner_estado(salon.negocio_id, "suspendido", "Denuncias de clientas")

    async with como_dueno(salon.negocio_id, salon.dueno_user_id) as (sesion, identidad):
        with pytest.raises(SuspendidoPorLaPlataforma) as fallo:
            await api_onboarding.publicar((sesion, identidad))

    # El motivo va en el mensaje: una puerta cerrada que no dice por qué es una puerta que la
    # gente aporrea, y aquí además el dueño necesita saber de qué le hablan al escribirnos.
    assert "Denuncias de clientas" in str(fallo.value.mensaje)
    assert await estado_de(salon.negocio_id) == ("suspendido", True)


@pytest.mark.asyncio
async def test_un_borrador_que_cumple_el_minimo_si_se_publica() -> None:
    """La comprobación nueva va delante del checklist: no puede haber roto el camino normal."""
    salon = await montar_salon()
    await completar_el_minimo(salon.negocio_id)
    await poner_estado(salon.negocio_id, "borrador")

    async with como_dueno(salon.negocio_id, salon.dueno_user_id) as (sesion, identidad):
        publicado = await api_onboarding.publicar((sesion, identidad))

    assert publicado.estado == "publicado"
    assert await estado_de(salon.negocio_id) == ("publicado", False)


@pytest.mark.asyncio
async def test_al_borrador_al_que_le_falta_algo_se_le_dice_qué_falta() -> None:
    """Sin foto ni horario ni ubicación: el error nombra lo que falta, no «no se pudo»."""
    salon = await montar_salon()
    await poner_estado(salon.negocio_id, "borrador")

    async with como_dueno(salon.negocio_id, salon.dueno_user_id) as (sesion, identidad):
        with pytest.raises(FaltaMinimoParaPublicar) as fallo:
            await api_onboarding.publicar((sesion, identidad))

    assert "el horario" in fallo.value.mensaje
    assert "una foto" in fallo.value.mensaje
    assert await estado_de(salon.negocio_id) == ("borrador", False)


@pytest.mark.asyncio
async def test_un_servicio_que_no_presta_nadie_no_deja_publicar() -> None:
    """Un salón **sin nadie en el equipo** no puede salir al marketplace.

    Salió usando el producto: el mínimo de D11 se cumplía con un servicio activo aunque no
    hubiera un solo profesional. El salón aparecía en la búsqueda y en el mapa, y al abrir su
    ficha no había ni una hora libre — porque un servicio sin nadie asignado **no se puede
    reservar** (STF-1). La persona se cree que está lleno y se va a otro; el salón no se entera
    nunca.

    No es un requisito nuevo sobre D11: es que «un servicio activo» signifique lo que dice.
    """
    salon = await montar_salon()
    await completar_el_minimo(salon.negocio_id)
    await poner_estado(salon.negocio_id, "borrador")

    # Se deja al salón sin nadie que preste nada, que es como nace uno recién dado de alta.
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("DELETE FROM staff_services WHERE business_id = :negocio"),
            {"negocio": salon.negocio_id},
        )

    async with como_dueno(salon.negocio_id, salon.dueno_user_id) as (sesion, identidad):
        with pytest.raises(FaltaMinimoParaPublicar) as fallo:
            await api_onboarding.publicar((sesion, identidad))

    assert "que alguien preste" in fallo.value.mensaje
    assert await estado_de(salon.negocio_id) == ("borrador", False)
