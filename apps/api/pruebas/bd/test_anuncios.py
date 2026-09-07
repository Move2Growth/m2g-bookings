"""La publicidad flash del salón y su política pública (patrón B de ADR-0002).

Lo que se vigila aquí es que la **vigencia viva en la política**, no en el serializador. Es la
diferencia entre un anuncio caducado que ya no se puede leer y uno que sigue en la base
esperando a que un endpoint distraído lo saque. Por eso las consultas de estas pruebas se
escriben **sin filtrar por fechas**: si la política no filtra, la prueba lo enseña.

Y una regla de forma: **un anuncio activo a la vez**. Lo impone la misma herramienta que la no
doble reserva —una restricción de exclusión sobre el rango de vigencia—, así que dos anuncios
que se pisan los rechaza PostgreSQL y no un `if`.
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

from agenda.errores import YaExiste
from agenda.servicios import anuncios as servicio_anuncios
from pruebas.bd.conftest import URL_APP
from pruebas.bd.escenario_dueno import despublicar
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


async def _ve_el_publico(negocio_id: uuid.UUID) -> list[str]:
    """Lo que el marketplace puede leer, **sin filtrar nada** en la consulta."""
    async with _publica() as sesion:
        return [
            fila[0]
            for fila in await sesion.execute(
                text("SELECT message FROM business_banners WHERE business_id = :negocio"),
                {"negocio": negocio_id},
            )
        ]


async def test_el_anuncio_vigente_se_ve_en_la_ficha_publica(motor):
    salon = await montar_salon()
    async with _como(motor, salon.negocio_id) as sesion:
        await servicio_anuncios.crear(
            sesion, negocio_id=salon.negocio_id, texto="2x1 en color hasta el domingo"
        )

    assert await _ve_el_publico(salon.negocio_id) == ["2x1 en color hasta el domingo"]


async def test_un_anuncio_caducado_no_lo_ve_el_publico(motor):
    """La vigencia la cumple **la política**, no el serializador.

    La consulta de esta prueba no filtra por fechas a propósito: si el anuncio caducado
    apareciera, significaría que lo único que lo escondía era el `WHERE` de la aplicación.
    """
    salon = await montar_salon()
    ayer = datetime.now(UTC) - timedelta(days=2)
    async with _como(motor, salon.negocio_id) as sesion:
        await servicio_anuncios.crear(
            sesion,
            negocio_id=salon.negocio_id,
            texto="Promo de la semana pasada",
            desde=ayer,
            hasta=ayer + timedelta(days=1),
        )

    assert await _ve_el_publico(salon.negocio_id) == []


async def test_un_anuncio_que_todavia_no_empieza_tampoco(motor):
    """Programarlo para el viernes no puede enseñarlo el martes."""
    salon = await montar_salon()
    async with _como(motor, salon.negocio_id) as sesion:
        await servicio_anuncios.crear(
            sesion,
            negocio_id=salon.negocio_id,
            texto="Rebajas del viernes",
            desde=datetime.now(UTC) + timedelta(days=3),
        )

    assert await _ve_el_publico(salon.negocio_id) == []


async def test_un_anuncio_retirado_tampoco(motor):
    salon = await montar_salon()
    async with _como(motor, salon.negocio_id) as sesion:
        anuncio = await servicio_anuncios.crear(
            sesion, negocio_id=salon.negocio_id, texto="Abrimos los domingos"
        )
        await servicio_anuncios.retirar(sesion, negocio_id=salon.negocio_id, anuncio_id=anuncio.id)

    assert await _ve_el_publico(salon.negocio_id) == []


async def test_despublicar_el_salon_apaga_su_anuncio(motor):
    """La política se ata al negocio publicado, no al anuncio suelto.

    Es la razón de ser del patrón B: despublicar un salón tiene que apagar su perfil entero de
    una vez, y no tabla a tabla desde la aplicación.
    """
    salon = await montar_salon()
    async with _como(motor, salon.negocio_id) as sesion:
        await servicio_anuncios.crear(
            sesion, negocio_id=salon.negocio_id, texto="Corte + barba por 15"
        )
    assert await _ve_el_publico(salon.negocio_id) != []

    await despublicar(salon.negocio_id)
    assert (
        await _ve_el_publico(salon.negocio_id) == []
    ), "El anuncio de un salón despublicado sigue siendo legible por el marketplace."


async def test_el_anuncio_de_un_salon_no_se_ve_desde_otro(motor):
    """El aislamiento entre negocios, con la consulta sin filtro."""
    uno = await montar_salon()
    otro = await montar_salon()
    async with _como(motor, otro.negocio_id) as sesion:
        await servicio_anuncios.crear(sesion, negocio_id=otro.negocio_id, texto="Solo mío")

    async with _como(motor, uno.negocio_id) as sesion:
        total = (await sesion.execute(text("SELECT count(*) FROM business_banners"))).scalar_one()
    assert total == 0


async def test_no_caben_dos_anuncios_activos_que_se_pisen(motor):
    """Lo impide la restricción de exclusión, igual que dos citas en el mismo hueco."""
    salon = await montar_salon()
    ahora = datetime.now(UTC)
    async with _como(motor, salon.negocio_id) as sesion:
        await servicio_anuncios.crear(
            sesion,
            negocio_id=salon.negocio_id,
            texto="Primero",
            desde=ahora,
            hasta=ahora + timedelta(days=7),
        )
        with pytest.raises(YaExiste):
            await servicio_anuncios.crear(
                sesion,
                negocio_id=salon.negocio_id,
                texto="Segundo, encima del primero",
                desde=ahora + timedelta(days=1),
                hasta=ahora + timedelta(days=3),
            )


async def test_dos_anuncios_seguidos_sin_solaparse_si_caben(motor):
    """Para que la prueba anterior signifique «que se pisen» y no «dos anuncios»."""
    salon = await montar_salon()
    ahora = datetime.now(UTC)
    async with _como(motor, salon.negocio_id) as sesion:
        await servicio_anuncios.crear(
            sesion,
            negocio_id=salon.negocio_id,
            texto="Esta semana",
            desde=ahora,
            hasta=ahora + timedelta(days=7),
        )
        segundo = await servicio_anuncios.crear(
            sesion,
            negocio_id=salon.negocio_id,
            texto="La que viene",
            desde=ahora + timedelta(days=7),
            hasta=ahora + timedelta(days=14),
        )
    assert segundo.vigente is False


async def test_un_profesional_no_puede_escribir_el_anuncio(motor):
    """El anuncio es configuración del salón: lo lee, no lo toca (STF-3).

    Y quien lo impide es la política restrictiva, no el `exigir_dueno` del endpoint: la
    inserción de aquí no pasa por ningún endpoint.
    """
    salon = await montar_salon()

    async with _como(motor, salon.negocio_id, salon.kevin.id) as sesion:
        with pytest.raises((DBAPIError, ProgrammingError)):
            await sesion.execute(
                text(
                    "INSERT INTO business_banners (business_id, message) "
                    "VALUES (:negocio, 'Lo escribo yo')"
                ),
                {"negocio": salon.negocio_id},
            )


async def test_un_profesional_si_puede_leer_el_anuncio(motor):
    """Necesita saber qué se está anunciando cuando la clienta llega preguntando por el 2x1."""
    salon = await montar_salon()
    async with _como(motor, salon.negocio_id) as sesion:
        await servicio_anuncios.crear(sesion, negocio_id=salon.negocio_id, texto="2x1 en color")

    async with _como(motor, salon.negocio_id, salon.kevin.id) as sesion:
        visto = (await sesion.execute(text("SELECT count(*) FROM business_banners"))).scalar_one()
    assert visto == 1
