"""Darse de baja: lo que desaparece y lo que tiene que quedarse (Ley 81 · ADR-0025).

Es el derecho de supresión, y choca de frente con dos derechos ajenos: la contabilidad del salón
y las opiniones que otras personas leen para elegir. Un `DELETE` de la fila rompería los dos.

Se prueba contra PostgreSQL de verdad porque lo que se ejerce son claves ajenas, políticas de
fila y el disparador que espeja el estado de una cita en su ocupación.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.servicios import baja as servicio_baja
from pruebas.bd.conftest import URL_APP
from pruebas.bd.escenario_panel import conexion_de_dueno, montar_salon

pytestmark = pytest.mark.bd


async def _sesion_de_plataforma(usuario_id: uuid.UUID) -> AsyncSession:
    """Como `/mi/…`: **sin negocio fijado pero declarando quién pregunta**.

    Las dos mitades importan. Sin negocio, porque la baja no es de ningún salón. Y con
    `app.current_user_id`, porque es lo que permite a una persona ver lo suyo en todos los
    salones donde ha estado sin aflojar el aislamiento — la política que lo usa es de solo
    lectura y solo de lo suyo.

    La primera versión de esta prueba abría la sesión a secas, y entonces la consulta de «¿lleva
    algún salón?» devolvía **cero filas en vez de fallar**, que es la forma de fallo que ADR-0002
    busca: la baja se hacía tan campante y el salón se quedaba sin nadie detrás. Ahí se ve por
    qué las pruebas de esto van contra PostgreSQL de verdad.
    """
    motor = create_async_engine(URL_APP, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    sesion = crear()
    await sesion.begin()
    await sesion.execute(
        text("SELECT set_config('app.current_user_id', :usuario, true)"),
        {"usuario": str(usuario_id)},
    )
    return sesion


async def _cita_futura(negocio_id, staff_id, cliente_id, user_id) -> uuid.UUID:
    """Una cita de pasado mañana, confirmada, de esa persona."""
    async with conexion_de_dueno() as sesion:
        return (
            await sesion.execute(
                text(
                    """
                    INSERT INTO bookings (business_id, staff_id, business_client_id,
                        client_user_id, status, starts_at, ends_at, total_duration_min,
                        total_amount_minor, currency, source)
                    VALUES (:negocio, :staff, :ficha, :usuario, 'confirmada',
                            now() + interval '2 days', now() + interval '2 days 30 minutes',
                            30, 1500, 'USD', 'cliente_web')
                    RETURNING id
                    """
                ),
                {
                    "negocio": negocio_id,
                    "staff": staff_id,
                    "ficha": cliente_id,
                    "usuario": user_id,
                },
            )
        ).scalar_one()


async def test_la_persona_desaparece_pero_su_fila_y_sus_citas_se_quedan():
    """Lo que identifica se va; lo que sostiene la contabilidad de un salón, no.

    Es el equilibrio entero de la Ley 81 en una prueba: si la fila desapareciera, un salón
    perdería reservas cobradas; si el nombre y el teléfono se quedaran, no se habría borrado
    nada.
    """
    salon = await montar_salon()

    async with conexion_de_dueno() as sesion:
        usuario_id = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO users (full_name, email, phone_e164, phone_verified_at, status)
                    VALUES ('Yaritza Beitía', :correo, :telefono, now(), 'activo')
                    RETURNING id
                    """
                ),
                {
                    "correo": f"yaritza-{uuid.uuid4().hex[:8]}@ejemplo.pa",
                    "telefono": f"+5076{uuid.uuid4().int % 10**7:07d}",
                },
            )
        ).scalar_one()
        ficha_id = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO business_clients (business_id, user_id, display_name,
                                                  phone_e164, source, notes)
                    VALUES (:negocio, :usuario, 'Yaritza Beitía', '+50761234567', 'marketplace',
                            'Le gusta el corte muy corto')
                    RETURNING id
                    """
                ),
                {"negocio": salon.negocio_id, "usuario": usuario_id},
            )
        ).scalar_one()

    cita_id = await _cita_futura(salon.negocio_id, salon.kevin.id, ficha_id, usuario_id)

    sesion = await _sesion_de_plataforma(usuario_id)
    try:
        resumen = await servicio_baja.dar_de_baja(sesion, usuario_id)
        await sesion.commit()
    finally:
        await sesion.close()

    assert (
        resumen.citas_canceladas == 1
    ), "Irse dejando una cita puesta le deja al salón un plantón y ningún aviso."

    async with conexion_de_dueno() as sesion:
        fila = (
            await sesion.execute(
                text(
                    "SELECT full_name, email, phone_e164, status, anonymized_at IS NOT NULL "
                    "FROM users WHERE id = :id"
                ),
                {"id": usuario_id},
            )
        ).one_or_none()
        cita = (
            await sesion.execute(
                text("SELECT status, client_user_id FROM bookings WHERE id = :id"),
                {"id": cita_id},
            )
        ).one()
        ficha = (
            await sesion.execute(
                text("SELECT display_name, phone_e164, notes FROM business_clients WHERE id = :id"),
                {"id": ficha_id},
            )
        ).one()

    assert fila is not None, "La fila se borró, y de ella cuelga la contabilidad de un salón."
    assert fila[0] == servicio_baja.NOMBRE_BORRADO
    assert fila[1] is None and fila[2] is None, "El correo o el teléfono siguen identificándola."
    assert fila[3] == "eliminado" and fila[4] is True

    assert cita[0] == "cancelada_cliente"
    assert cita[1] == usuario_id, "La cita perdió a su dueño y el salón ya no sabe de quién era."

    assert ficha[0] == servicio_baja.NOMBRE_BORRADO
    assert (
        ficha[1] is None and ficha[2] is None
    ), "La ficha del salón conserva el teléfono o las notas: son datos personales y se van."


async def test_quien_lleva_un_salon_publicado_no_puede_desaparecer():
    """Un salón sin dueño sigue aceptando reservas, y la clienta se encuentra la puerta cerrada.

    No es una traba: es que cerrar el salón o pasarlo a otra persona es una decisión suya, y
    tiene que tomarla antes.
    """
    salon = await montar_salon()

    sesion = await _sesion_de_plataforma(salon.dueno_user_id)
    try:
        with pytest.raises(servicio_baja.TieneUnSalonVivo) as fallo:
            await servicio_baja.dar_de_baja(sesion, salon.dueno_user_id)
    finally:
        await sesion.rollback()
        await sesion.close()

    assert "Ciérralo o pásalo" in fallo.value.mensaje

    async with conexion_de_dueno() as sesion:
        sigue = (
            await sesion.execute(
                text("SELECT anonymized_at FROM users WHERE id = :id"),
                {"id": salon.dueno_user_id},
            )
        ).scalar_one()
    assert sigue is None, "Se dio de baja igual, y el salón se quedó sin nadie detrás."


async def test_darse_de_baja_dos_veces_no_revienta():
    """Repetir la baja no es un error: ya está hecha.

    Decirle «esa cuenta no existe» a quien acaba de borrarse suena a que algo salió mal, y lo
    que salió es exactamente lo que pidió.
    """
    async with conexion_de_dueno() as sesion:
        usuario_id = (
            await sesion.execute(
                text(
                    "INSERT INTO users (full_name, phone_e164, status) "
                    "VALUES ('Alguien', :telefono, 'activo') RETURNING id"
                ),
                {"telefono": f"+5076{uuid.uuid4().int % 10**7:07d}"},
            )
        ).scalar_one()

    for _ in range(2):
        sesion = await _sesion_de_plataforma(usuario_id)
        try:
            await servicio_baja.dar_de_baja(sesion, usuario_id)
            await sesion.commit()
        finally:
            await sesion.close()

    async with conexion_de_dueno() as sesion:
        cuantas = (
            await sesion.execute(
                text("SELECT count(*) FROM users WHERE id = :id"), {"id": usuario_id}
            )
        ).scalar_one()
    assert cuantas == 1
