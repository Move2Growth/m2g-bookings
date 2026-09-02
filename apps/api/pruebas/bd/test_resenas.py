"""Las reglas de una reseña, contra la base de verdad (REV-1, REV-3, REV-5).

REV-1 dice tres cosas y las tres se rompen distinto:

* **Sin cita completada no hay reseña.** Se comprueba en la aplicación porque depende del
  estado de la cita y del reloj.
* **Una por reserva.** La garantiza el único de la base, y por eso se prueba **saltándose la
  aplicación**: si el único no estuviera, dos peticiones simultáneas crearían dos reseñas y la
  validación del servicio no se enteraría.
* **Dentro de la ventana**, que es configurable por negocio y por tanto no puede vivir en una
  restricción de la base.

Y el agregado: lo que se enseña y lo que ordena el marketplace es el **bayesiano** (REV-5), no
la media. Aquí se comprueba que una sola reseña de cinco estrellas no dispara al negocio.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agenda.errores import ResenaNoPermitida, YaExiste
from agenda.modelos.reservas import Booking
from agenda.servicios import resenas as servicio_resenas
from pruebas.bd.escenario_panel import (
    ayer_a_las,
    conexion_de_dueno,
    crear_cita,
    crear_cita_completada,
    manana_a_las,
    montar_salon,
)

pytestmark = pytest.mark.bd


async def _sesion_en(motor, negocio_id: uuid.UUID) -> AsyncSession:
    """Una sesión de la API con el negocio fijado, como la de un endpoint."""
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    sesion = crear()
    await sesion.begin()
    await sesion.execute(
        text("SELECT set_config('app.current_business_id', :negocio, true)"),
        {"negocio": str(negocio_id)},
    )
    return sesion


async def test_no_se_puede_resenar_una_cita_que_no_esta_completada(motor):
    """El caso más común: la clienta ya fue, pero el salón no cerró la cita todavía.

    Se rechaza con un mensaje que dice qué hacer —pedirle al salón que la cierre— en vez de un
    «no se puede» a secas, porque el paso siguiente es una conversación, no un error.
    """
    salon = await montar_salon()
    cita_id = await crear_cita(
        salon.negocio_id,
        salon.kevin.id,
        salon.cliente_de_kevin,
        salon.servicio_id,
        # A las 15:00 y no a las 10:30: Kevin ya tiene una cita de 10:00 a 10:45 en el
        # escenario, y la restricción de exclusión la rechazaría —con razón—, que es otra
        # prueba y no esta.
        inicio=manana_a_las(15),
        estado="confirmada",
        usuario_id=salon.dueno_user_id,
    )

    sesion = await _sesion_en(motor, salon.negocio_id)
    try:
        reserva = await sesion.get(Booking, cita_id)
        with pytest.raises(ResenaNoPermitida) as fallo:
            await servicio_resenas.crear(sesion, reserva, autor_user_id=salon.dueno_user_id, nota=5)
        assert "atendida" in str(fallo.value)
    finally:
        await sesion.rollback()
        await sesion.close()


async def test_no_se_puede_resenar_dos_veces_la_misma_cita(motor):
    """Segunda reseña de la misma cita: la aplicación la corta con un mensaje."""
    salon = await montar_salon()
    cita_id = await crear_cita_completada(
        salon.negocio_id,
        salon.kevin.id,
        salon.cliente_de_kevin,
        salon.servicio_id,
        salon.dueno_user_id,
    )

    sesion = await _sesion_en(motor, salon.negocio_id)
    try:
        reserva = await sesion.get(Booking, cita_id)
        await servicio_resenas.crear(sesion, reserva, autor_user_id=salon.dueno_user_id, nota=5)
        await sesion.commit()
    finally:
        await sesion.close()

    sesion = await _sesion_en(motor, salon.negocio_id)
    try:
        reserva = await sesion.get(Booking, cita_id)
        with pytest.raises(YaExiste):
            await servicio_resenas.crear(sesion, reserva, autor_user_id=salon.dueno_user_id, nota=1)
    finally:
        await sesion.rollback()
        await sesion.close()


async def test_la_base_impide_la_segunda_resena_aunque_el_codigo_no_mire(motor):
    """**Con la comprobación del código desactivada, la base rechaza igual la segunda.**

    Es la misma forma de probarlo que la no doble reserva: se inserta a pelo, saltándose el
    servicio. Si esto pasara, dos peticiones a la vez crearían dos reseñas de la misma cita y
    el rating del salón contaría dos veces la misma opinión.
    """
    salon = await montar_salon()
    cita_id = await crear_cita_completada(
        salon.negocio_id,
        salon.kevin.id,
        salon.cliente_de_kevin,
        salon.servicio_id,
        salon.dueno_user_id,
    )

    insertar = text(
        """
        INSERT INTO reviews (business_id, booking_id, author_user_id, rating, status)
        VALUES (:negocio, :cita, :autor, :nota, 'publicada')
        """
    )
    parametros = {
        "negocio": salon.negocio_id,
        "cita": cita_id,
        "autor": salon.dueno_user_id,
        "nota": 5,
    }

    async with conexion_de_dueno() as sesion:
        await sesion.execute(insertar, parametros)

    with pytest.raises(IntegrityError) as fallo:
        async with conexion_de_dueno() as sesion:
            await sesion.execute(insertar, {**parametros, "nota": 1})

    assert "uq_reviews_booking_id" in str(fallo.value)


async def test_fuera_de_la_ventana_ya_no_se_puede_opinar(motor):
    """La ventana se cuenta desde que **terminó la cita**, no desde que se marcó completada.

    Si el salón tarda tres días en cerrarla, esos tres días no se los puede comer al cliente.
    """
    salon = await montar_salon()
    hace_mucho = datetime.now(UTC) - timedelta(days=40)
    cita_id = await crear_cita_completada(
        salon.negocio_id,
        salon.kevin.id,
        salon.cliente_de_kevin,
        salon.servicio_id,
        salon.dueno_user_id,
        inicio=hace_mucho,
    )

    sesion = await _sesion_en(motor, salon.negocio_id)
    try:
        reserva = await sesion.get(Booking, cita_id)
        with pytest.raises(ResenaNoPermitida) as fallo:
            await servicio_resenas.crear(sesion, reserva, autor_user_id=salon.dueno_user_id, nota=5)
        assert "plazo" in str(fallo.value)
    finally:
        await sesion.rollback()
        await sesion.close()


async def test_la_ventana_sale_de_la_configuracion_del_negocio(motor):
    """Cambiar `review_window_days` cambia el plazo **sin desplegar** (REV-1, ADM-4).

    Con la ventana subida a noventa días, la misma cita de hace cuarenta sí se puede reseñar.
    Ningún número de negocio vive como constante.
    """
    salon = await montar_salon()
    hace_mucho = datetime.now(UTC) - timedelta(days=40)
    cita_id = await crear_cita_completada(
        salon.negocio_id,
        salon.kevin.id,
        salon.cliente_de_kevin,
        salon.servicio_id,
        salon.dueno_user_id,
        inicio=hace_mucho,
    )
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text(
                "UPDATE business_settings SET review_window_days = 90 WHERE business_id = :negocio"
            ),
            {"negocio": salon.negocio_id},
        )

    sesion = await _sesion_en(motor, salon.negocio_id)
    try:
        reserva = await sesion.get(Booking, cita_id)
        resena = await servicio_resenas.crear(
            sesion, reserva, autor_user_id=salon.dueno_user_id, nota=4
        )
        assert resena.rating == 4
        await sesion.commit()
    finally:
        await sesion.close()


async def test_una_cita_ajena_no_se_puede_resenar(motor):
    """Reseñar la cita de otra persona **no se distingue de que no exista**.

    Distinguirlas convertiría cualquier identificador en un oráculo de «esta cita existe».
    """
    salon = await montar_salon()
    cita_id = await crear_cita_completada(
        salon.negocio_id,
        salon.kevin.id,
        salon.cliente_de_kevin,
        salon.servicio_id,
        salon.dueno_user_id,
    )

    sesion = await _sesion_en(motor, salon.negocio_id)
    try:
        reserva = await sesion.get(Booking, cita_id)
        with pytest.raises(ResenaNoPermitida) as fallo:
            await servicio_resenas.crear(sesion, reserva, autor_user_id=uuid.uuid4(), nota=5)
        assert "no es tuya" in str(fallo.value)
    finally:
        await sesion.rollback()
        await sesion.close()


async def test_el_agregado_es_bayesiano_y_no_la_media(motor):
    """Una sola reseña de cinco estrellas **no** deja el negocio en 5,00 (REV-5, ADR-0009).

    Con `m = 4,3` y `C = 10` sembrados, una reseña de 5 deja el bayesiano en 4,36: se separa de
    la media global lo justo. Es lo que impide que un salón nuevo con una opinión adelante a
    otro con ochenta de 4,7.
    """
    salon = await montar_salon()
    cita_id = await crear_cita_completada(
        salon.negocio_id,
        salon.kevin.id,
        salon.cliente_de_kevin,
        salon.servicio_id,
        salon.dueno_user_id,
    )

    sesion = await _sesion_en(motor, salon.negocio_id)
    try:
        reserva = await sesion.get(Booking, cita_id)
        await servicio_resenas.crear(sesion, reserva, autor_user_id=salon.dueno_user_id, nota=5)
        stats = await servicio_resenas.recalcular_agregado(sesion, salon.negocio_id)

        assert stats.reviews_count == 1
        assert float(stats.rating_avg) == 5.0, "La media simple sí es 5,00: es la del panel."
        assert float(stats.rating_bayesian) < 5.0, (
            "El rating que se enseña tiene que estar ponderado hacia la media global. "
            f"Salió {stats.rating_bayesian}."
        )
        assert 4.0 < float(stats.rating_bayesian) < 4.6
        await sesion.commit()
    finally:
        await sesion.close()


async def test_ocultar_una_resena_la_saca_del_agregado(motor):
    """Ocultar tiene que significar algo: si siguiera pesando en la media, no serviría de nada.

    Es lo que hace la consola al resolver un reporte (ADM-3), y por eso el agregado se
    **recuenta** en vez de llevar un contador incremental.
    """
    salon = await montar_salon()
    cita_id = await crear_cita_completada(
        salon.negocio_id,
        salon.kevin.id,
        salon.cliente_de_kevin,
        salon.servicio_id,
        salon.dueno_user_id,
        inicio=ayer_a_las(9),
    )

    sesion = await _sesion_en(motor, salon.negocio_id)
    try:
        reserva = await sesion.get(Booking, cita_id)
        resena = await servicio_resenas.crear(
            sesion, reserva, autor_user_id=salon.dueno_user_id, nota=1
        )
        await sesion.commit()
    finally:
        await sesion.close()

    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("UPDATE reviews SET status = 'oculta' WHERE id = :resena"),
            {"resena": resena.id},
        )

    sesion = await _sesion_en(motor, salon.negocio_id)
    try:
        stats = await servicio_resenas.recalcular_agregado(sesion, salon.negocio_id)
        assert stats.reviews_count == 0
        assert stats.rating_avg is None
        await sesion.commit()
    finally:
        await sesion.close()
