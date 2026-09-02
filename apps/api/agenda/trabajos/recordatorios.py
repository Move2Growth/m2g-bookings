"""Recordatorios de 24 h y 2 h, y el «¿cómo te fue?» de después (NTF-2, RVW-1).

**Estos trabajos no mandan nada.** Recorren su ventana y encolan, y la fila que insertan lleva
la hora a la que debe salir (`scheduled_for`) y la hora a partir de la cual ya no vale
(`expires_at`). Quien entrega es el trabajador de la cola, más tarde y por su cuenta.

La separación tiene una consecuencia práctica que es todo el punto: ejecutar el planificador
dos veces —porque se solapó una pasada, porque se redesplegó a mitad, porque alguien lo lanzó a
mano— no manda dos mensajes. La clave de idempotencia es la misma y la segunda inserción no
entra. Sin esta separación, «ejecutar dos veces» significaría «llamar dos veces a Meta», y ahí
ya no hay índice único que valga.

Sobre la ventana: se mira **exactamente** el tramo que empieza dentro de N horas. Si el
planificador estuvo caído seis horas, el recordatorio de 24 h de las citas que pasaron por esa
ventana no se recupera, y es a propósito: un recordatorio de 24 h que sale con 18 h de
antelación ya no es el mensaje que se diseñó, y encolarlo tarde solo sirve para que llegue a
deshora.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.dominio.reservas import ESTADOS_ACTIVOS, EstadoReserva
from agenda.modelos.clientes import BusinessClient
from agenda.modelos.negocio import Business
from agenda.modelos.reservas import Booking
from agenda.notificaciones.cola import Hecho, decidir_canal, encolar
from agenda.trabajos.bd import fabrica_de_negocio, fabrica_de_sistema, negocios_vivos

registro = logging.getLogger("agenda.trabajos")

#: Cuánto tramo se mira por delante del punto exacto. Tiene que ser **mayor que el periodo del
#: planificador**: si el `cron` corre cada 15 minutos y la ventana fuera de 5, las citas que
#: cayeran en los 10 minutos restantes no recibirían recordatorio nunca.
VENTANA_POR_DEFECTO = timedelta(hours=1)

#: Cuánto se espera desde que la cita se marca completada hasta pedir la reseña. Lo justo para
#: que la persona haya salido del local: preguntar «¿cómo te fue?» mientras le están secando el
#: pelo es peor que no preguntar.
ESPERA_DE_LA_RESENA = timedelta(hours=2)

#: Los estados en los que una cita sigue viva. Son los mismos que la restricción de exclusión
#: considera ocupados y los mismos del índice parcial `ix_bookings_recordatorios`, que es el
#: que hace que este barrido no recorra el histórico entero.
ESTADOS_QUE_MERECEN_RECORDATORIO = tuple(e.value for e in ESTADOS_ACTIVOS)


async def planificar_recordatorios_24h(ctx: dict[str, Any]) -> int:
    """`cron` diario cada pocos minutos: encola el recordatorio de las citas de mañana."""
    return await _planificar(ctx, horas=24)


async def planificar_recordatorios_2h(ctx: dict[str, Any]) -> int:
    """`cron`: encola el recordatorio de las citas de dentro de dos horas."""
    return await _planificar(ctx, horas=2)


async def planificar_reviews(ctx: dict[str, Any]) -> int:
    """`cron`: encola el «¿cómo te fue?» de las citas que el negocio acaba de completar."""
    encoladas = 0
    async with fabrica_de_sistema(ctx)() as sesion:
        negocios = await negocios_vivos(sesion)
    for negocio_id in negocios:
        encoladas += await encolar_reviews_de_negocio(ctx, str(negocio_id))
    return encoladas


async def encolar_recordatorios_de_negocio(
    ctx: dict[str, Any],
    negocio_id: str,
    horas: int,
    *,
    ahora: datetime | None = None,
    ventana: timedelta = VENTANA_POR_DEFECTO,
) -> int:
    """El recordatorio de un negocio. **Recibe el identificador y relee de la base.**

    Devuelve cuántas filas nuevas entraron en la cola. Las que ya estaban no cuentan y no son
    un problema: son la prueba de que la idempotencia hizo su trabajo.
    """
    ahora = ahora or datetime.now(UTC)
    hecho = Hecho.RECORDATORIO_24H if horas == 24 else Hecho.RECORDATORIO_2H
    desde = ahora + timedelta(hours=horas)
    hasta = desde + ventana
    encoladas = 0

    async with fabrica_de_negocio(ctx)(uuid.UUID(negocio_id)) as sesion:
        negocio = await sesion.get(Business, uuid.UUID(negocio_id))
        filas = await sesion.execute(
            select(Booking, BusinessClient)
            .join(BusinessClient, BusinessClient.id == Booking.business_client_id)
            .where(
                Booking.business_id == uuid.UUID(negocio_id),
                Booking.status.in_(ESTADOS_QUE_MERECEN_RECORDATORIO),
                Booking.starts_at >= desde,
                Booking.starts_at < hasta,
            )
        )

        for reserva, cliente in filas.all():
            decision = await decidir_canal(
                sesion,
                hecho=hecho,
                destinos={"whatsapp": cliente.phone_e164, "email": cliente.email},
                usuario_id=reserva.client_user_id,
            )
            if not decision.hay_que_mandar:
                registro.info(
                    "recordatorio de %s no encolado (%s)", reserva.id, decision.motivo
                )
                continue

            creada = await encolar(
                sesion,
                hecho=hecho,
                entidad="booking",
                entidad_id=reserva.id,
                canal=decision.canal or "",
                destino=decision.destino,
                destinatario="cliente",
                negocio_id=reserva.business_id,
                usuario_id=reserva.client_user_id,
                # La hora de salida sale de la **cita**, no de cuándo corrió el planificador.
                # Así el mensaje llega a la misma hora aunque el barrido se adelante.
                programado_para=reserva.starts_at - timedelta(hours=horas),
                # Un recordatorio que llega después de la cita es ruido, y encima de pago.
                caduca_en=reserva.starts_at,
                variables=_variables_de_la_cita(reserva, cliente, negocio),
                cola="programado",
            )
            if creada is not None:
                encoladas += 1

    return encoladas


async def encolar_reviews_de_negocio(
    ctx: dict[str, Any],
    negocio_id: str,
    *,
    ahora: datetime | None = None,
    ventana: timedelta = VENTANA_POR_DEFECTO,
) -> int:
    """El «¿cómo te fue?» de las citas completadas hace poco.

    La petición caduca con la ventana de reseñas del propio negocio (`review_window_days`): si
    la reseña ya no se puede dejar, preguntar por ella es mandar a alguien a una puerta cerrada.
    """
    ahora = ahora or datetime.now(UTC)
    hasta = ahora - ESPERA_DE_LA_RESENA
    desde = hasta - ventana
    encoladas = 0

    async with fabrica_de_negocio(ctx)(uuid.UUID(negocio_id)) as sesion:
        negocio = await sesion.get(Business, uuid.UUID(negocio_id))
        filas = await sesion.execute(
            select(Booking, BusinessClient)
            .join(BusinessClient, BusinessClient.id == Booking.business_client_id)
            .where(
                Booking.business_id == uuid.UUID(negocio_id),
                Booking.status == EstadoReserva.COMPLETADA.value,
                Booking.completed_at >= desde,
                Booking.completed_at < hasta,
            )
        )

        for reserva, cliente in filas.all():
            # Sin cuenta no hay reseña que dejar: el cliente rápido del mostrador (AGD-2) no
            # tiene dónde escribirla, así que no se le pregunta.
            if reserva.client_user_id is None:
                continue

            decision = await decidir_canal(
                sesion,
                hecho=Hecho.REVIEW_SOLICITADA,
                destinos={"whatsapp": cliente.phone_e164, "email": cliente.email},
                usuario_id=reserva.client_user_id,
            )
            if not decision.hay_que_mandar:
                continue

            completada = reserva.completed_at or ahora
            creada = await encolar(
                sesion,
                hecho=Hecho.REVIEW_SOLICITADA,
                entidad="booking",
                entidad_id=reserva.id,
                canal=decision.canal or "",
                destino=decision.destino,
                destinatario="cliente",
                negocio_id=reserva.business_id,
                usuario_id=reserva.client_user_id,
                programado_para=completada + ESPERA_DE_LA_RESENA,
                caduca_en=completada + timedelta(days=14),
                variables=_variables_de_la_cita(reserva, cliente, negocio),
                cola="programado",
            )
            if creada is not None:
                encoladas += 1

    return encoladas


async def _planificar(ctx: dict[str, Any], *, horas: int) -> int:
    """El reparto: un negocio, una transacción con su tenant fijado.

    No se recorren todas las reservas de todos los negocios en una sola consulta, aunque sería
    más corto. Con el tenant fijado por negocio, una consulta a la que se le olvide el `WHERE`
    no puede devolver datos ajenos — la base no la deja. Es la diferencia entre confiar en el
    `WHERE` y no tener que confiar.
    """
    encoladas = 0
    async with fabrica_de_sistema(ctx)() as sesion:
        negocios = await negocios_vivos(sesion)
    for negocio_id in negocios:
        encoladas += await encolar_recordatorios_de_negocio(ctx, str(negocio_id), horas)
    return encoladas


def _variables_de_la_cita(
    reserva: Booking, cliente: BusinessClient, negocio: Business | None
) -> dict[str, Any]:
    """Lo que la plantilla necesita rellenar.

    Se guarda **copiado** en la fila de la cola y no se relee al entregar: el mensaje que se
    manda tiene que ser el que se decidió mandar, aunque entre medias alguien cambie el nombre
    del salón. El instante va en UTC y en ISO; convertirlo al huso del negocio es del que pinta
    el texto, no de la cola.
    """
    return {
        "reserva_id": str(reserva.id),
        "cliente": cliente.display_name,
        "negocio": negocio.display_name if negocio else None,
        "empieza_en": reserva.starts_at.isoformat(),
        "zona_horaria": negocio.timezone if negocio else "America/Panama",
        "duracion_min": reserva.total_duration_min,
    }
