"""Los filtros del marketplace contra la base real (MKT-2).

Estos filtros no se pueden probar con objetos falsos: **PostGIS, el `ILIKE` sobre dos tablas y
la sonda de disponibilidad son SQL**, y la mitad de lo que se rompe aquí solo se rompe en SQL.
De hecho la sonda de disponibilidad ya se rompió una vez de una forma que ninguna prueba pura
habría visto: `min()` no existe para `uuid` en PostgreSQL, así que la consulta que elegía «el
servicio más corto de cada negocio» no llegaba ni a compilar. El motor estaba bien; la consulta
que lo alimentaba, no.

La búsqueda se ejecuta con el **rol público**, que es con el que corre de verdad: probarla con
el rol del negocio taparía cualquier permiso que falte.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, time, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import agenda.bd
from agenda.servicios import busqueda
from pruebas.bd.conftest import URL_APP
from pruebas.bd.escenario_panel import conexion_de_dueno, montar_salon

pytestmark = pytest.mark.bd

URL_PUBLICA = URL_APP.replace("agenda_api:", "agenda_publico:")


@pytest.fixture(autouse=True)
def api_apuntando_a_la_base_de_pruebas(monkeypatch):
    """Redirige el motor **global** de la aplicación a la base de pruebas.

    Hace falta porque el filtro de disponibilidad no se calcula con la sesión que recibe la
    función: llama a `agenda.bd.sesion_de_negocio`, que abre **su propia** conexión para poder
    fijar el tenant de cada salón. Ese motor se construye al importar el módulo, a partir de
    `DATABASE_URL`, y por defecto apunta a la base de **desarrollo**.

    Es un detalle que ya se cobró un rato de depuración: sin esto, la prueba monta el salón en
    `agenda_pruebas`, el filtro lo busca en `agenda` y el motor responde, con toda la razón,
    que ese negocio no existe.
    """
    motor = create_async_engine(URL_APP, poolclass=None)
    monkeypatch.setattr(
        agenda.bd,
        "crear_sesion",
        async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False),
    )
    yield


@asynccontextmanager
async def _sesion_publica() -> AsyncIterator[AsyncSession]:
    motor = create_async_engine(URL_PUBLICA, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    try:
        async with crear() as sesion, sesion.begin():
            yield sesion
    finally:
        await motor.dispose()


async def _con_precio(negocio_id: uuid.UUID, centavos: int) -> None:
    """Le añade al salón un servicio más barato, para poder comparar dos precios distintos."""
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("SELECT set_config('app.current_business_id', :negocio, true)"),
            {"negocio": str(negocio_id)},
        )
        await sesion.execute(
            text(
                """
                INSERT INTO services (business_id, service_category_id, name, duration_min,
                                      price_kind, price_minor)
                SELECT :negocio, service_category_id, 'Flequillo', 15, 'fijo', :centavos
                FROM services WHERE business_id = :negocio LIMIT 1
                """
            ),
            {"negocio": negocio_id, "centavos": centavos},
        )
        await sesion.commit()


async def _con_horario(negocio_id: uuid.UUID, abre: time, cierra: time) -> None:
    """Le pone al salón el mismo horario todos los días, para que el filtro tenga qué mirar."""
    async with conexion_de_dueno() as sesion:
        for dia in range(7):
            await sesion.execute(
                text(
                    """
                    INSERT INTO business_hours (business_id, weekday, opens_at, closes_at)
                    VALUES (:negocio, :dia, :abre, :cierra)
                    """
                ),
                {"negocio": negocio_id, "dia": dia, "abre": abre, "cierra": cierra},
            )


async def _con_jornada_del_equipo(salon) -> None:
    """El horario del profesional, que es lo que el motor interseca con el del negocio."""
    async with conexion_de_dueno() as sesion:
        for staff in (salon.kevin.id, salon.marielys.id):
            for dia in range(7):
                await sesion.execute(
                    text(
                        """
                        INSERT INTO staff_hours (business_id, staff_id, weekday, starts_at,
                                                 ends_at, kind)
                        VALUES (:negocio, :staff, :dia, '00:00', '23:59', 'trabajo')
                        """
                    ),
                    {"negocio": salon.negocio_id, "staff": staff, "dia": dia},
                )


async def test_el_filtro_de_precio_mira_algun_servicio_y_no_todos():
    """Quien filtra hasta 25 dólares quiere salones **donde pueda pagar 25**.

    No salones donde todo cueste menos de 25: una barbería que hace el corte a 18 y el balayage
    a 150 tiene que salir en la búsqueda de quien busca un corte barato.
    """
    salon = await montar_salon()  # su único servicio cuesta 1800
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text(
                """
                INSERT INTO services (business_id, service_category_id, name, duration_min,
                                      price_kind, price_minor)
                SELECT :negocio, service_category_id, 'Balayage', 180, 'fijo', 15000
                FROM services WHERE business_id = :negocio LIMIT 1
                """
            ),
            {"negocio": salon.negocio_id},
        )

    # Se acota por el nombre irrepetible del escenario: la base de pruebas acumula salones de
    # ejecuciones anteriores y sin acotar, este se quedaría fuera de la primera página.
    async with _sesion_publica() as sesion:
        baratos = await busqueda.buscar(sesion, texto=salon.nombre, precio_max=2000)
        caros = await busqueda.buscar(sesion, texto=salon.nombre, precio_min=10000)
        imposible = await busqueda.buscar(sesion, texto=salon.nombre, precio_min=200000)

    ids = {r.negocio_id for r in baratos}
    assert (
        salon.negocio_id in ids
    ), "El salón tiene un servicio de 18 y no sale al filtrar hasta 20."
    assert salon.negocio_id in {r.negocio_id for r in caros}
    assert salon.negocio_id not in {r.negocio_id for r in imposible}


async def test_el_precio_desde_que_se_ensena_es_el_mas_barato():
    salon = await montar_salon()
    async with _sesion_publica() as sesion:
        resultados = await busqueda.buscar(sesion, texto=salon.nombre)
    nuestro = [r for r in resultados if r.negocio_id == salon.negocio_id]
    assert nuestro, "El salón del escenario tiene que salir al buscar por su nombre."
    assert nuestro[0].desde_centavos == 1800


async def test_la_sonda_de_disponibilidad_elige_el_servicio_mas_corto():
    """Regresión del `min(uuid)`: la consulta tiene que **ejecutarse** y devolver un servicio.

    Es la que alimenta el filtro de disponibilidad real. Si vuelve vacía o revienta, el filtro
    deja de encontrar nada y parece que ningún salón tiene huecos.
    """
    salon = await montar_salon()
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text(
                """
                INSERT INTO services (business_id, service_category_id, name, duration_min,
                                      price_kind, price_minor)
                SELECT :negocio, service_category_id, 'Retoque exprés', 15, 'fijo', 500
                FROM services WHERE business_id = :negocio LIMIT 1
                """
            ),
            {"negocio": salon.negocio_id},
        )

    async with _sesion_publica() as sesion:
        sondas = await busqueda._servicio_mas_corto(sesion, [salon.negocio_id])
        duracion = (
            await sesion.execute(
                text("SELECT duration_min FROM services WHERE id = :id"),
                {"id": sondas[salon.negocio_id]},
            )
        ).scalar_one()

    assert duracion == 15, "La sonda tiene que ser el servicio más corto, no uno cualquiera."


async def test_disponibilidad_hoy_usa_el_motor_y_devuelve_la_primera_hora():
    """El filtro se apoya en el **mismo motor** que la reserva, no en una copia (MKT-2).

    Con jornada de 24 horas el salón tiene huecos hoy sí o sí, así que si esto viniera vacío
    sería que el filtro no está preguntándole al motor.
    """
    salon = await montar_salon()
    await _con_horario(salon.negocio_id, time(0, 0), time(23, 59))
    await _con_jornada_del_equipo(salon)

    async with _sesion_publica() as sesion:
        resultados = await busqueda.buscar(sesion, texto=salon.nombre, disponibilidad="hoy")

    nuestro = [r for r in resultados if r.negocio_id == salon.negocio_id]
    assert nuestro, "Un salón abierto todo el día tiene que tener hueco hoy."
    assert nuestro[0].proxima_hora is not None
    assert nuestro[0].proxima_hora > datetime.now(
        UTC
    ), "La próxima hora libre no puede estar en el pasado."


async def test_un_salon_sin_horario_no_sale_al_filtrar_por_disponibilidad():
    """Sin horario no hay huecos, y el motor lo dice: no es un error, es una lista vacía."""
    salon = await montar_salon()  # el escenario no le pone horario a propósito

    async with _sesion_publica() as sesion:
        resultados = await busqueda.buscar(sesion, texto=salon.nombre, disponibilidad="hoy")

    assert salon.negocio_id not in {r.negocio_id for r in resultados}


async def test_abierto_ahora_deja_fuera_al_que_no_tiene_horario():
    """«No lo sé» **no pasa** el filtro: quien lo pulsa pregunta por algo afirmativo."""
    sin_horario = await montar_salon()
    abierto = await montar_salon()
    await _con_horario(abierto.negocio_id, time(0, 0), time(23, 59))

    async with _sesion_publica() as sesion:
        con_horario = await busqueda.buscar(sesion, texto=abierto.nombre, abierto_ahora=True)
        sin = await busqueda.buscar(sesion, texto=sin_horario.nombre, abierto_ahora=True)

    assert abierto.negocio_id in {r.negocio_id for r in con_horario}
    assert sin_horario.negocio_id not in {r.negocio_id for r in sin}


async def test_el_filtro_de_rating_usa_el_bayesiano():
    """Filtrar por la media simple dejaría pasar salones con una sola reseña de cinco (REV-5)."""
    salon = await montar_salon()
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text(
                """
                INSERT INTO business_rating_stats (business_id, reviews_count, rating_sum,
                                                   rating_avg, rating_bayesian)
                VALUES (:negocio, 1, 5, 5.00, 4.36)
                """
            ),
            {"negocio": salon.negocio_id},
        )

    async with _sesion_publica() as sesion:
        exigentes = await busqueda.buscar(sesion, texto=salon.nombre, rating_min=4.8)
        laxos = await busqueda.buscar(sesion, texto=salon.nombre, rating_min=4.0)

    assert salon.negocio_id not in {r.negocio_id for r in exigentes}, (
        "Con una sola reseña de cinco, el negocio no puede colarse en el filtro de 4,8: "
        "su rating publicado es el bayesiano, 4,36."
    )
    assert salon.negocio_id in {r.negocio_id for r in laxos}


async def test_el_orden_por_precio_pone_delante_al_mas_barato():
    """Los órdenes explícitos **dejan la fórmula fuera**: quien pulsa «más baratos» los quiere.

    La prueba monta **dos** salones con precios distintos, y eso no es ceremonia: la versión
    anterior comprobaba que la lista entera estuviera ordenada, y como todos los salones del
    escenario cuestan lo mismo, cualquier orden la pasaba. El fallo real —ordenar antes de que
    `_adornar` rellene el precio, comparando `None` contra `None`— sobrevivió a su propia
    prueba durante toda una tanda.
    """
    marca = f"orden{uuid.uuid4().hex[:6]}"
    caro = await montar_salon(f"{marca}caro")
    barato = await montar_salon(f"{marca}barato")
    await _con_precio(barato.negocio_id, 500)

    async with _sesion_publica() as sesion:
        resultados = await busqueda.buscar(sesion, texto=marca, orden="precio")

    posiciones = {r.negocio_id: i for i, r in enumerate(resultados)}
    assert (
        barato.negocio_id in posiciones and caro.negocio_id in posiciones
    ), "Los dos salones tienen que salir en la búsqueda o no se compara nada."
    assert (
        posiciones[barato.negocio_id] < posiciones[caro.negocio_id]
    ), "El de 5,00 tiene que ir delante del de 18,00."

    precios = [r.desde_centavos for r in resultados if r.desde_centavos is not None]
    assert precios == sorted(precios)


async def test_la_ventana_de_una_fecha_se_calcula_en_la_zona_del_negocio():
    """El día de un salón de Panamá empieza a las 05:00 UTC, no a medianoche UTC.

    Calcularlo en UTC daría medianoches equivocadas para media búsqueda y el filtro «el jueves»
    enseñaría huecos del miércoles por la noche.
    """
    ahora = datetime(2026, 9, 2, 18, 0, tzinfo=UTC)
    desde, hasta = busqueda._ventana_de_agenda(
        "fecha", datetime(2026, 9, 4).date(), "America/Panama", ahora
    )
    assert desde == datetime(2026, 9, 4, 5, 0, tzinfo=UTC)
    assert hasta == desde + timedelta(days=1)
