"""La garantía nº 1: **ninguna consulta devuelve datos de otro negocio**.

Dos barberías vecinas, cada una con su profesional, su clienta y sus citas. La prueba no mira
si el código de la API pone bien el `WHERE`: mira si **la base de datos deja ver** lo ajeno
cuando el `WHERE` falta. Es la diferencia entre confiar en que nadie se olvide nunca y que
olvidarse no tenga consecuencias (ADR-0002).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from pruebas.bd.escenario import URL_DUENO_ASYNC, crear_cita, manana_a_las, montar_escenario

pytestmark = pytest.mark.bd


async def _sembrar_una_cita_en_cada_negocio(escenario) -> None:
    motor = create_async_engine(URL_DUENO_ASYNC, poolclass=None)
    try:
        async with motor.begin() as conexion:
            await crear_cita(conexion, escenario.cangrejo, inicio=manana_a_las(9))
            await crear_cita(conexion, escenario.obarrio, inicio=manana_a_las(9))
    finally:
        await motor.dispose()


async def test_un_select_sin_where_solo_ve_las_citas_del_negocio_activo(sesion_negocio):
    """El caso que motiva todo: alguien escribe una consulta y se olvida del filtro.

    Con el tenant fijado, ese descuido devuelve **cero filas ajenas** en vez de la agenda del
    salón de al lado.
    """
    escenario = await montar_escenario()
    await _sembrar_una_cita_en_cada_negocio(escenario)

    async with sesion_negocio(escenario.cangrejo.id) as sesion:
        resultado = await sesion.execute(text("SELECT business_id FROM bookings"))
        negocios_vistos = {fila[0] for fila in resultado}

    assert negocios_vistos <= {escenario.cangrejo.id}, (
        "Una consulta sin WHERE ha devuelto reservas de otro negocio. "
        f"Vistos: {negocios_vistos}, esperado como mucho: {escenario.cangrejo.id}."
    )


async def test_pedir_explicitamente_el_negocio_ajeno_tampoco_lo_enseña(sesion_negocio):
    """Ni siquiera nombrando el identificador del otro: la política no es un filtro sugerido."""
    escenario = await montar_escenario()
    await _sembrar_una_cita_en_cada_negocio(escenario)

    async with sesion_negocio(escenario.cangrejo.id) as sesion:
        resultado = await sesion.execute(
            text("SELECT count(*) FROM bookings WHERE business_id = :otro"),
            {"otro": escenario.obarrio.id},
        )

    assert resultado.scalar_one() == 0


async def test_tampoco_se_ve_la_ocupacion_ni_la_ficha_de_cliente_ajenas(sesion_negocio):
    """El aislamiento no es solo de `bookings`: la agenda y los clientes son igual de sensibles.

    La ficha del cliente lleva su teléfono y su historial de no-shows. Que se filtre entre
    negocios sería, además de un fallo, un problema de protección de datos.
    """
    escenario = await montar_escenario()
    await _sembrar_una_cita_en_cada_negocio(escenario)

    async with sesion_negocio(escenario.obarrio.id) as sesion:
        ocupacion = await sesion.execute(text("SELECT business_id FROM staff_occupancy"))
        clientes = await sesion.execute(text("SELECT business_id FROM business_clients"))
        profesionales = await sesion.execute(text("SELECT business_id FROM staff_profiles"))

    for nombre, resultado in (
        ("staff_occupancy", ocupacion),
        ("business_clients", clientes),
        ("staff_profiles", profesionales),
    ):
        ajenos = {fila[0] for fila in resultado} - {escenario.obarrio.id}
        assert not ajenos, f"{nombre} ha dejado ver filas de otro negocio: {ajenos}"


async def test_sin_tenant_fijado_no_se_ve_nada(sesion):
    """Una sesión sin negocio activo no es una sesión con permiso total: es una sin datos.

    Importa porque un trabajo en segundo plano no tiene sesión de usuario de la que heredar el
    tenant. Si olvidarlo diera acceso a todo, el peor sitio para olvidarlo sería justo ese.
    """
    escenario = await montar_escenario()
    await _sembrar_una_cita_en_cada_negocio(escenario)

    resultado = await sesion.execute(text("SELECT count(*) FROM bookings"))

    assert resultado.scalar_one() == 0


async def test_no_se_pueden_escribir_filas_de_otro_negocio(sesion_negocio):
    """Con el tenant de una barbería no se puede insertar en la agenda de la otra.

    La política tiene `WITH CHECK` además de `USING`: sin él se podría leer solo lo propio pero
    **escribir** en lo ajeno, que es una puerta trasera con mejor disfraz.
    """
    escenario = await montar_escenario()

    with pytest.raises(DBAPIError):
        async with sesion_negocio(escenario.cangrejo.id) as sesion:
            await sesion.execute(
                text(
                    """
                    INSERT INTO staff_profiles (id, business_id, display_name)
                    VALUES (:id, :negocio, 'Intruso')
                    """
                ),
                {"id": uuid.uuid4(), "negocio": escenario.obarrio.id},
            )
