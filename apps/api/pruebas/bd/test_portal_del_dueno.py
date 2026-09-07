"""Las finanzas y el mejor del mes del portal del dueño (punto 6 del encargo).

Estas pruebas no se pueden escribir con objetos falsos: lo que se comprueba es **SQL**. La
agrupación por día en la hora local del negocio la hace `date_trunc(... AT TIME ZONE ...)`, y el
error que se está vigilando —agrupar en UTC y partir el sábado panameño por la mitad— solo
existe dentro de PostgreSQL.

Dos de ellas son de las que hay que poder romper a propósito para creérselas:

* Si el agregado leyera el precio de hoy del servicio en vez del importe guardado en la cita,
  `test_el_importe_es_el_congelado_en_la_cita` falla.
* Si la agrupación fuera en UTC, `test_la_caja_se_agrupa_en_la_hora_local_del_negocio` falla.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agenda.servicios import finanzas as servicio_finanzas
from pruebas.bd.escenario_dueno import (
    cambiar_precio,
    cita_completada,
    con_categoria,
    con_servicio,
    hace,
)
from pruebas.bd.escenario_panel import crear_cita, manana_a_las, montar_salon

pytestmark = pytest.mark.bd

PANAMA = ZoneInfo("America/Panama")


@asynccontextmanager
async def _como(
    motor, negocio_id: uuid.UUID, staff_id: uuid.UUID | None = None
) -> AsyncIterator[AsyncSession]:
    """La misma sesión que abre la API: negocio fijado y, si toca, profesional declarado."""
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


async def test_solo_cuentan_las_citas_completadas(motor):
    """Una cita confirmada es una promesa, no un ingreso.

    Sin esto, el panel de finanzas subiría al reservar y bajaría solo los lunes por la mañana,
    cuando el salón cierra las citas de la semana.
    """
    salon = await montar_salon()
    await cita_completada(
        salon.negocio_id,
        staff_id=salon.kevin.id,
        cliente_id=salon.cliente_de_kevin,
        servicio_id=salon.servicio_id,
        inicio=hace(1),
        centavos=4500,
    )
    # Una confirmada de mañana y una cancelada de ayer: ninguna suma.
    await crear_cita(
        salon.negocio_id,
        salon.kevin.id,
        salon.cliente_de_kevin,
        salon.servicio_id,
        inicio=manana_a_las(15),
        estado="confirmada",
    )
    await crear_cita(
        salon.negocio_id,
        salon.marielys.id,
        salon.cliente_de_marielys,
        salon.servicio_id,
        inicio=hace(1, hora=16),
        estado="cancelada_cliente",
    )

    async with _como(motor, salon.negocio_id) as sesion:
        caja = await servicio_finanzas.resumen(
            sesion,
            negocio_id=salon.negocio_id,
            zona="America/Panama",
            moneda="USD",
            desde=hace(30),
            hasta=datetime.now(UTC) + timedelta(days=30),
        )

    assert caja.citas == 1, "Ha contado citas que no están completadas."
    assert caja.importe_centavos == 4500


async def test_el_importe_es_el_congelado_en_la_cita(motor):
    """Subirle el precio al servicio **no** puede reescribir lo que se facturó en marzo.

    Es la prueba que se rompe si alguien «simplifica» el agregado leyendo `services.price_minor`
    en vez de `bookings.total_amount_minor`: los dos números coinciden hasta el día en que el
    salón sube la tarifa, y entonces el histórico entero cambia solo.
    """
    salon = await montar_salon()
    await cita_completada(
        salon.negocio_id,
        staff_id=salon.kevin.id,
        cliente_id=salon.cliente_de_kevin,
        servicio_id=salon.servicio_id,
        inicio=hace(3),
        centavos=1800,
    )
    await cambiar_precio(salon.negocio_id, salon.servicio_id, 9900)

    async with _como(motor, salon.negocio_id) as sesion:
        caja = await servicio_finanzas.resumen(
            sesion,
            negocio_id=salon.negocio_id,
            zona="America/Panama",
            moneda="USD",
            desde=hace(30),
            hasta=datetime.now(UTC) + timedelta(days=1),
        )

    assert caja.importe_centavos == 1800, (
        "El agregado se ha ido con el precio nuevo del catálogo. Tiene que usar el importe "
        "guardado en la cita."
    )


async def test_la_caja_se_agrupa_en_la_hora_local_del_negocio(motor):
    """Una cita de las nueve de la noche en Panamá es de **ese** día, no del siguiente.

    A las 21:00 en Panamá son las 02:00 UTC del día de después. Agrupar en UTC mandaría esa
    cita —y las cinco últimas horas de cada día— a la casilla equivocada, y el salón vería la
    caja del sábado repartida entre sábado y domingo.
    """
    salon = await montar_salon()
    instante = hace(2, hora=2)  # 02:00 UTC → 21:00 del día anterior en Panamá
    await cita_completada(
        salon.negocio_id,
        staff_id=salon.kevin.id,
        cliente_id=salon.cliente_de_kevin,
        servicio_id=salon.servicio_id,
        inicio=instante,
        centavos=2500,
    )

    async with _como(motor, salon.negocio_id) as sesion:
        caja = await servicio_finanzas.resumen(
            sesion,
            negocio_id=salon.negocio_id,
            zona="America/Panama",
            moneda="USD",
            desde=hace(30),
            hasta=datetime.now(UTC) + timedelta(days=1),
            agrupacion="dia",
        )

    assert len(caja.periodos) == 1
    dia_agrupado = caja.periodos[0].inicio.astimezone(PANAMA).date()
    assert dia_agrupado == instante.astimezone(PANAMA).date(), (
        "La caja se está agrupando en UTC: la cita de las nueve de la noche cayó en el día "
        "siguiente."
    )
    assert (
        caja.periodos[0].inicio.astimezone(PANAMA).hour == 0
    ), "El periodo no empieza a la medianoche local."


async def test_el_ticket_medio_y_las_citas_sin_precio(motor):
    """Un servicio «a consultar» suma cero, y eso **se dice** en vez de esconderse."""
    salon = await montar_salon()
    categoria = await con_categoria("barberia", "Barbería")
    a_consultar = await con_servicio(
        salon.negocio_id,
        nombre="Balayage",
        minutos=180,
        centavos=None,
        categoria_id=categoria,
        tipo_de_precio="consultar",
    )
    await cita_completada(
        salon.negocio_id,
        staff_id=salon.kevin.id,
        cliente_id=salon.cliente_de_kevin,
        servicio_id=salon.servicio_id,
        inicio=hace(2),
        centavos=2000,
    )
    await cita_completada(
        salon.negocio_id,
        staff_id=salon.kevin.id,
        cliente_id=salon.cliente_de_kevin,
        servicio_id=a_consultar,
        inicio=hace(2, hora=14),
        centavos=0,
        tipo_de_precio="consultar",
    )

    async with _como(motor, salon.negocio_id) as sesion:
        caja = await servicio_finanzas.resumen(
            sesion,
            negocio_id=salon.negocio_id,
            zona="America/Panama",
            moneda="USD",
            desde=hace(30),
            hasta=datetime.now(UTC) + timedelta(days=1),
        )

    assert caja.citas == 2
    assert caja.importe_centavos == 2000
    assert caja.ticket_medio_centavos == 1000
    assert (
        caja.citas_sin_precio == 1
    ), "El total parece completo y no lo es: hay que decir cuántas citas iban sin precio."


async def test_las_finanzas_de_un_negocio_no_se_ven_desde_otro(motor):
    """El aislamiento también aplica al dinero, y aquí se comprueba **sin filtrar por negocio**.

    La consulta lleva su `WHERE` en producción; esta prueba lo quita a propósito para ver si lo
    que protege es la política o el `WHERE`.
    """
    uno = await montar_salon()
    otro = await montar_salon()
    await cita_completada(
        otro.negocio_id,
        staff_id=otro.kevin.id,
        cliente_id=otro.cliente_de_kevin,
        servicio_id=otro.servicio_id,
        inicio=hace(1),
        centavos=7700,
    )

    async with _como(motor, uno.negocio_id) as sesion:
        total = (
            await sesion.execute(
                text(
                    "SELECT coalesce(sum(total_amount_minor), 0) FROM bookings "
                    "WHERE status = 'completada'"
                )
            )
        ).scalar_one()

    assert int(total) == 0, "Se ha visto la facturación de otro salón con una consulta sin filtro."


async def test_el_mejor_del_mes_ordena_por_importe_o_por_servicios(motor):
    """Los dos criterios del encargo dan **órdenes distintos**, y por eso hay dos.

    Kevin hace tres cortes baratos y Marielys un balayage caro: por dinero manda ella, por
    número de servicios manda él. Si los dos criterios devolvieran lo mismo, uno de los dos no
    estaría implementado.
    """
    salon = await montar_salon()
    barberia = await con_categoria("barberia", "Barbería")
    color = await con_categoria("color", "Color")
    corte = await con_servicio(
        salon.negocio_id, nombre="Corte", minutos=30, centavos=1500, categoria_id=barberia
    )
    balayage = await con_servicio(
        salon.negocio_id, nombre="Balayage", minutos=180, centavos=12000, categoria_id=color
    )

    for hora in (9, 11, 13):
        await cita_completada(
            salon.negocio_id,
            staff_id=salon.kevin.id,
            cliente_id=salon.cliente_de_kevin,
            servicio_id=corte,
            inicio=hace(2, hora=hora),
            centavos=1500,
            nombre_servicio="Corte",
        )
    await cita_completada(
        salon.negocio_id,
        staff_id=salon.marielys.id,
        cliente_id=salon.cliente_de_marielys,
        servicio_id=balayage,
        inicio=hace(2, hora=15),
        centavos=12000,
        minutos=180,
        nombre_servicio="Balayage",
    )

    desde, hasta = hace(30), datetime.now(UTC) + timedelta(days=1)
    async with _como(motor, salon.negocio_id) as sesion:
        por_dinero = await servicio_finanzas.ranking_del_equipo(
            sesion, negocio_id=salon.negocio_id, desde=desde, hasta=hasta, criterio="importe"
        )
        por_servicios = await servicio_finanzas.ranking_del_equipo(
            sesion, negocio_id=salon.negocio_id, desde=desde, hasta=hasta, criterio="servicios"
        )
        solo_barberia = await servicio_finanzas.ranking_del_equipo(
            sesion,
            negocio_id=salon.negocio_id,
            desde=desde,
            hasta=hasta,
            criterio="importe",
            categoria="barberia",
        )

    assert por_dinero[0].profesional_id == salon.marielys.id
    assert por_dinero[0].importe_centavos == 12000
    assert por_servicios[0].profesional_id == salon.kevin.id
    assert por_servicios[0].servicios == 3

    assert [f.profesional_id for f in solo_barberia] == [
        salon.kevin.id
    ], "El filtro por categoría no ha dejado fuera el balayage."
    assert solo_barberia[0].importe_centavos == 4500
