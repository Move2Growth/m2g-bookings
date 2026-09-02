"""Los trabajos periódicos: ejecutarlos dos veces no manda nada dos veces.

Se ejecutan **llamando a la función directamente**, sin Redis. Lo que se quiere probar es el
efecto —qué filas quedan en la cola—, no el transporte de arq (ADR-0008). El contexto lleva las
fábricas de sesión inyectadas, que es el mismo hueco que `on_startup` rellena en producción.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from agenda.notificaciones.cola import Hecho, clave_de_idempotencia
from agenda.trabajos.cierre import marcar_citas_sin_cerrar_de_negocio
from agenda.trabajos.recordatorios import (
    encolar_recordatorios_de_negocio,
    encolar_reviews_de_negocio,
    planificar_recordatorios_24h,
)
from pruebas.notificaciones.escenario import apagar_canal, crear_cita, montar_negocio

pytestmark = pytest.mark.bd


async def _filas(abrir_negocio, negocio_id: uuid.UUID, clave: str) -> list[tuple]:
    async with abrir_negocio(negocio_id) as sesion:
        return list(
            (
                await sesion.execute(
                    text(
                        "SELECT status, channel, destination, scheduled_for, expires_at,"
                        " recipient_kind, payload FROM notifications"
                        " WHERE idempotency_key = :clave"
                    ),
                    {"clave": clave},
                )
            ).all()
        )


async def test_el_trabajo_de_recordatorios_ejecutado_dos_veces_no_duplica(ctx, abrir_negocio):
    """La segunda pasada encola **cero**. Es el caso real: el planificador se solapa.

    Y la fila que quedó lleva la hora de salida derivada de la **cita**, no de cuándo corrió el
    barrido: el mensaje llega 24 h antes aunque el trabajo se adelante o se retrase.
    """
    negocio = await montar_negocio()
    cita = datetime.now(UTC) + timedelta(hours=24, minutes=10)
    reserva_id = await crear_cita(negocio, inicio=cita)

    primera = await encolar_recordatorios_de_negocio(ctx, str(negocio.id), 24)
    segunda = await encolar_recordatorios_de_negocio(ctx, str(negocio.id), 24)

    clave = clave_de_idempotencia(Hecho.RECORDATORIO_24H, "booking", reserva_id)
    filas = await _filas(abrir_negocio, negocio.id, clave)

    assert primera == 1, "La primera pasada no encoló el recordatorio de la cita de mañana."
    assert segunda == 0, "La segunda pasada volvió a encolar: el planificador duplicaría."
    assert len(filas) == 1
    estado, canal, destino, programado, caduca, destinatario, _ = filas[0]
    assert estado == "pendiente"
    assert canal == "whatsapp"
    assert destino == negocio.telefono_de_la_clienta
    assert destinatario == "cliente"
    assert programado == cita - timedelta(hours=24)
    assert caduca == cita, "El recordatorio tiene que caducar cuando empieza la cita."


async def test_el_cron_completo_ejecutado_dos_veces_tampoco_duplica(ctx, abrir_negocio):
    """El mismo caso, pero por el `cron` de verdad: recorre todos los negocios y reparte.

    Aquí se ejerce además el reparto por tenant: el trabajo enumera negocios con el rol de
    sistema y abre **una transacción con el tenant fijado por cada uno**.
    """
    negocio = await montar_negocio()
    cita = datetime.now(UTC) + timedelta(hours=24, minutes=20)
    reserva_id = await crear_cita(negocio, inicio=cita)

    primera = await planificar_recordatorios_24h(ctx)
    segunda = await planificar_recordatorios_24h(ctx)

    clave = clave_de_idempotencia(Hecho.RECORDATORIO_24H, "booking", reserva_id)
    filas = await _filas(abrir_negocio, negocio.id, clave)

    assert primera >= 1, "El cron no encoló ni el recordatorio de la cita recién creada."
    assert segunda == 0, "La segunda ejecución del cron encoló otra vez."
    assert len(filas) == 1


async def test_una_cita_fuera_de_la_ventana_no_se_recuerda_todavia(ctx, abrir_negocio):
    """Lo que empieza dentro de tres días no entra en el barrido de las 24 h.

    Parece obvio y es la mitad del trabajo: una ventana mal puesta encolaría hoy el
    recordatorio de la semana que viene y lo mandaría con seis días de antelación.
    """
    negocio = await montar_negocio()
    reserva_id = await crear_cita(negocio, inicio=datetime.now(UTC) + timedelta(days=3))

    encoladas = await encolar_recordatorios_de_negocio(ctx, str(negocio.id), 24)

    clave = clave_de_idempotencia(Hecho.RECORDATORIO_24H, "booking", reserva_id)
    assert encoladas == 0
    assert await _filas(abrir_negocio, negocio.id, clave) == []


async def test_quien_apago_el_canal_no_recibe_el_recordatorio(ctx, abrir_negocio):
    """Decidir mira las preferencias (NTF-3), y apagarlas se nota en que **no se encola**.

    No se encola y luego se filtra al entregar: lo que no se va a mandar no entra en la cola,
    porque una cola llena de filas que nunca saldrán deja de servir para saber qué está pasando.
    """
    negocio = await montar_negocio(telefono=True, correo=False)
    cita = datetime.now(UTC) + timedelta(hours=24, minutes=30)
    reserva_id = await crear_cita(negocio, inicio=cita)

    async with abrir_negocio(negocio.id) as sesion:
        usuario_id = (
            await sesion.execute(
                text("SELECT client_user_id FROM bookings WHERE id = :id"), {"id": reserva_id}
            )
        ).scalar_one()
    await apagar_canal(negocio, usuario_id=usuario_id, canal="whatsapp", categoria="recordatorios")

    encoladas = await encolar_recordatorios_de_negocio(ctx, str(negocio.id), 24)

    clave = clave_de_idempotencia(Hecho.RECORDATORIO_24H, "booking", reserva_id)
    assert encoladas == 0
    assert await _filas(abrir_negocio, negocio.id, clave) == []


async def test_el_como_te_fue_se_encola_una_vez_por_cita(ctx, abrir_negocio):
    """El «¿cómo te fue?» de una cita completada, y solo uno por cita."""
    negocio = await montar_negocio()
    ahora = datetime.now(UTC)
    reserva_id = await crear_cita(
        negocio,
        inicio=ahora - timedelta(hours=5),
        estado="completada",
        completada_en=ahora - timedelta(hours=2, minutes=30),
    )

    primera = await encolar_reviews_de_negocio(ctx, str(negocio.id))
    segunda = await encolar_reviews_de_negocio(ctx, str(negocio.id))

    clave = clave_de_idempotencia(Hecho.REVIEW_SOLICITADA, "booking", reserva_id)
    assert primera == 1
    assert segunda == 0
    assert len(await _filas(abrir_negocio, negocio.id, clave)) == 1


async def test_una_cita_pasada_se_marca_para_revision_y_nunca_se_pone_no_show(ctx, abrir_negocio):
    """**La prueba que protege al cliente.**

    Una cita confirmada cuya hora ya pasó no la cierra el sistema. El barbero pudo atenderla y
    no tocar el móvil, y un no-show automático le contaría al cliente para bloquearlo (RSV-5).
    Lo único que hace el trabajo es avisar al negocio con la lista, para que la cierre quien
    estaba allí.
    """
    negocio = await montar_negocio()
    ahora = datetime.now(UTC)
    reserva_id = await crear_cita(negocio, inicio=ahora - timedelta(hours=6))

    avisos = await marcar_citas_sin_cerrar_de_negocio(ctx, str(negocio.id), ahora=ahora)
    repetido = await marcar_citas_sin_cerrar_de_negocio(ctx, str(negocio.id), ahora=ahora)

    clave = clave_de_idempotencia(
        Hecho.CITAS_SIN_CERRAR, "business", negocio.id, ahora.date().isoformat()
    )
    filas = await _filas(abrir_negocio, negocio.id, clave)

    async with abrir_negocio(negocio.id) as sesion:
        estado, no_show_at = (
            await sesion.execute(
                text("SELECT status, no_show_at FROM bookings WHERE id = :id"),
                {"id": reserva_id},
            )
        ).one()

    assert avisos == 1
    assert repetido == 0, "Correr cada hora no puede convertirse en veinticuatro avisos."
    assert len(filas) == 1
    assert filas[0][5] == "negocio", "El aviso es para el salón, no para la clienta."
    assert str(reserva_id) in filas[0][6]["reservas"]
    assert estado == "confirmada", "El sistema cambió el estado de una cita y no le toca."
    assert no_show_at is None, (
        "Se marcó un no-show automático. Eso le cuenta al cliente y lo decide el negocio, "
        "que es quien estaba allí."
    )
