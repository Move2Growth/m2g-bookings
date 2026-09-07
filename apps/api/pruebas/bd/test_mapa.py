"""La vista de mapa: los salones dentro del rectángulo visible (punto 5 del encargo).

Esto es SQL de PostGIS y no se puede probar con objetos falsos: lo que decide si un salón entra
o no es `ST_Intersects` sobre `geography`, y el error clásico —comparar en grados como si fueran
metros, o casar el rectángulo con el tipo equivocado— solo aparece contra una base de verdad.

Se ejecuta con el **rol público**, que es con el que corre: probarlo con el rol del negocio
taparía cualquier permiso que falte y, sobre todo, taparía si algún día se cuela un dato que el
marketplace no debería ver.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.errores import DatoInvalido
from agenda.servicios import mapa as servicio_mapa
from pruebas.bd.conftest import URL_APP
from pruebas.bd.escenario_dueno import con_punto, despublicar
from pruebas.bd.escenario_panel import montar_salon

pytestmark = pytest.mark.bd

URL_PUBLICA = URL_APP.replace("agenda_api:", "agenda_publico:")

#: Un rectángulo alrededor de Ciudad de Panamá, del tamaño de lo que se ve en un móvil.
CIUDAD = {"oeste": -79.60, "sur": 8.93, "este": -79.45, "norte": 9.05}

#: Costa del Este, dentro; y un punto en el Pacífico bien lejos, fuera.
DENTRO = (-79.50, 8.98)
FUERA = (-78.00, 8.98)


@asynccontextmanager
async def _publica() -> AsyncIterator[AsyncSession]:
    motor = create_async_engine(URL_PUBLICA, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    try:
        async with crear() as sesion, sesion.begin():
            yield sesion
    finally:
        await motor.dispose()


async def test_devuelve_lo_que_hay_dentro_del_rectangulo():
    """Y solo eso: el salón de al lado del rectángulo no entra."""
    aqui = await montar_salon()
    alli = await montar_salon()
    await con_punto(aqui.negocio_id, longitud=DENTRO[0], latitud=DENTRO[1])
    await con_punto(alli.negocio_id, longitud=FUERA[0], latitud=FUERA[1])

    async with _publica() as sesion:
        vista = await servicio_mapa.en_el_rectangulo(sesion, **CIUDAD, limite=300)

    encontrados = {s.negocio_id for s in vista.salones}
    assert aqui.negocio_id in encontrados
    assert alli.negocio_id not in encontrados, (
        "Ha entrado un salón que está fuera del rectángulo: la consulta no está filtrando por "
        "el rectángulo o lo está comparando con el tipo equivocado."
    )


async def test_el_punto_devuelto_es_el_del_salon():
    """Longitud y latitud, en ese orden. Invertirlos deja los pines en el mar de China."""
    salon = await montar_salon()
    await con_punto(salon.negocio_id, longitud=DENTRO[0], latitud=DENTRO[1])

    async with _publica() as sesion:
        vista = await servicio_mapa.en_el_rectangulo(sesion, **CIUDAD, limite=300)

    pin = next(s for s in vista.salones if s.negocio_id == salon.negocio_id)
    assert round(pin.longitud, 4) == DENTRO[0]
    assert round(pin.latitud, 4) == DENTRO[1]


async def test_un_salon_despublicado_no_sale_en_el_mapa():
    """Lo decide la política del rol público, no este endpoint."""
    salon = await montar_salon()
    await con_punto(salon.negocio_id, longitud=DENTRO[0], latitud=DENTRO[1])
    await despublicar(salon.negocio_id)

    async with _publica() as sesion:
        vista = await servicio_mapa.en_el_rectangulo(sesion, **CIUDAD, limite=300)

    assert salon.negocio_id not in {s.negocio_id for s in vista.salones}


async def test_el_tope_recorta_y_lo_dice():
    """Un mapa alejado que devuelve el país entero son megabytes en datos móviles.

    Lo que se comprueba no es solo que recorte: es que **avise**. Una muestra silenciosa es
    peor que un recorte, porque la pantalla enseña cuatro salones donde hay cuatrocientos y
    nadie tiene forma de saberlo.
    """
    for _ in range(3):
        salon = await montar_salon()
        await con_punto(salon.negocio_id, longitud=DENTRO[0], latitud=DENTRO[1])

    async with _publica() as sesion:
        recortada = await servicio_mapa.en_el_rectangulo(sesion, **CIUDAD, limite=2)
        holgada = await servicio_mapa.en_el_rectangulo(sesion, **CIUDAD, limite=300)

    assert len(recortada.salones) == 2
    assert recortada.truncado is True
    assert holgada.truncado is False or len(holgada.salones) == 300


async def test_un_rectangulo_al_reves_es_un_error_y_no_una_lista_vacia():
    """Casi siempre significa que quien llama cambió el orden de los parámetros.

    Devolverle cero resultados en silencio le costaría media tarde; el error lo dice en una
    línea.
    """
    async with _publica() as sesion:
        with pytest.raises(DatoInvalido):
            await servicio_mapa.en_el_rectangulo(
                sesion, oeste=-79.45, sur=8.93, este=-79.60, norte=9.05
            )
        with pytest.raises(DatoInvalido):
            await servicio_mapa.en_el_rectangulo(
                sesion, oeste=-79.60, sur=9.05, este=-79.45, norte=8.93
            )


async def test_un_rectangulo_gigante_se_rechaza():
    """Pedir «el mundo» no es un mapa: es una descarga del catálogo con otro nombre."""
    async with _publica() as sesion:
        with pytest.raises(DatoInvalido):
            await servicio_mapa.en_el_rectangulo(sesion, oeste=-180, sur=-80, este=180, norte=80)


async def test_el_mapa_no_puede_llegar_a_un_telefono():
    """Garantía 3. El rol que sirve el mapa **no tiene permiso** sobre las tablas con teléfonos.

    Se comprueba sobre el permiso y no sobre el serializador a propósito: un serializador se
    puede cambiar sin querer; un `GRANT` que no existe no se cambia sin querer.
    """
    async with _publica() as sesion:
        permisos = (
            await sesion.execute(
                text(
                    "SELECT has_table_privilege('agenda_publico', 'business_clients', 'SELECT'), "
                    "       has_table_privilege('agenda_publico', 'bookings', 'SELECT'), "
                    "       has_table_privilege('agenda_publico', 'users', 'SELECT')"
                )
            )
        ).one()
    assert permisos == (
        False,
        False,
        False,
    ), "El rol del marketplace tiene lectura sobre una tabla con datos personales."
