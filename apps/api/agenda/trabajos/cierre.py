"""Citas que ya pasaron y siguen confirmadas: se marcan para revisión, **no se cierran solas**.

Este trabajo es el que más fácil se escribe mal, porque la versión incorrecta es la más cómoda:
pasar la hora y marcar `no_show` a lo que nadie tocó. No se hace, y no por prudencia sino
porque sería falso y además tendría consecuencias.

Falso, porque el barbero atendió a esa persona y no tocó el móvil: en un salón lleno un jueves
por la tarde, eso pasa todos los días. Y con consecuencias, porque el no-show **le cuenta al
cliente** (RSV-5) y puede acabar bloqueándolo para reservar. Un contador de faltas alimentado
por el olvido del negocio castiga a quien sí fue.

Así que el sistema hace lo único que le corresponde: **avisar al negocio de que tiene citas sin
cerrar**, con la lista, para que las cierre él. Cerrar una cita es decir qué pasó, y eso solo lo
sabe quien estaba allí.

El aviso es uno por negocio y por día —la clave lleva la fecha—, así que el trabajo puede
correr cada hora sin convertirse en una lluvia de mensajes.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.dominio.reservas import EstadoReserva
from agenda.modelos.identidad import User
from agenda.modelos.negocio import Business
from agenda.modelos.reservas import Booking
from agenda.notificaciones.cola import Hecho, decidir_canal, encolar
from agenda.trabajos.bd import fabrica_de_negocio, fabrica_de_sistema, negocios_vivos

registro = logging.getLogger("agenda.trabajos")

#: Margen desde que la cita termina hasta que se considera «sin cerrar». Da tiempo a que el
#: negocio la cierre con calma cuando el cliente ya salió por la puerta.
GRACIA_POR_DEFECTO = timedelta(hours=2)

#: Cuántas reservas van en el aviso. La lista es para que el dueño sepa qué mirar, no un
#: volcado: si hay ciento veinte, el problema no se arregla enseñándoselas todas en WhatsApp.
MAXIMO_EN_EL_AVISO = 50


async def planificar_cierre_de_citas_pasadas(ctx: dict[str, Any]) -> int:
    """`cron`: recorre los negocios y avisa al que tenga citas sin cerrar."""
    avisos = 0
    async with fabrica_de_sistema(ctx)() as sesion:
        negocios = await negocios_vivos(sesion)
    for negocio_id in negocios:
        avisos += await marcar_citas_sin_cerrar_de_negocio(ctx, str(negocio_id))
    return avisos


async def marcar_citas_sin_cerrar_de_negocio(
    ctx: dict[str, Any],
    negocio_id: str,
    *,
    ahora: datetime | None = None,
    gracia: timedelta = GRACIA_POR_DEFECTO,
) -> int:
    """Devuelve 1 si encoló el aviso del día, 0 si no había nada que avisar o ya estaba.

    **Ninguna reserva cambia de estado aquí.** El único efecto es la fila en la cola, y su
    `payload` lleva la lista de citas para que el negocio sepa exactamente cuáles son.
    """
    ahora = ahora or datetime.now(UTC)
    limite = ahora - gracia

    async with fabrica_de_negocio(ctx)(uuid.UUID(negocio_id)) as sesion:
        pendientes = list(
            (
                await sesion.execute(
                    select(Booking.id)
                    .where(
                        Booking.business_id == uuid.UUID(negocio_id),
                        Booking.status == EstadoReserva.CONFIRMADA.value,
                        Booking.ends_at < limite,
                    )
                    .order_by(Booking.starts_at)
                )
            )
            .scalars()
            .all()
        )
        if not pendientes:
            return 0

        negocio = await sesion.get(Business, uuid.UUID(negocio_id))
        destinos = await _destinos_del_negocio(sesion, negocio)
        decision = await decidir_canal(
            sesion,
            hecho=Hecho.CITAS_SIN_CERRAR,
            destinos=destinos,
            negocio_id=uuid.UUID(negocio_id),
        )
        if not decision.hay_que_mandar:
            registro.info(
                "negocio %s tiene %d citas sin cerrar y no se le puede avisar (%s)",
                negocio_id,
                len(pendientes),
                decision.motivo,
            )
            return 0

        creada = await encolar(
            sesion,
            hecho=Hecho.CITAS_SIN_CERRAR,
            entidad="business",
            entidad_id=negocio_id,
            # Uno por día: correr cada hora no puede convertirse en veinticuatro avisos.
            sufijo_de_clave=ahora.date().isoformat(),
            canal=decision.canal or "",
            destino=decision.destino,
            destinatario="negocio",
            negocio_id=uuid.UUID(negocio_id),
            programado_para=ahora,
            # Caduca al final del día siguiente: recordarle el lunes lo del jueves pasado no
            # ayuda a nadie, y la lista para entonces ya es otra.
            caduca_en=ahora + timedelta(days=1),
            variables={
                "total": len(pendientes),
                "reservas": [str(i) for i in pendientes[:MAXIMO_EN_EL_AVISO]],
                "negocio": negocio.display_name if negocio else None,
            },
            cola="programado",
        )
        return 1 if creada is not None else 0


async def _destinos_del_negocio(
    sesion: AsyncSession, negocio: Business | None
) -> dict[str, str | None]:
    """Por dónde se avisa al salón: su WhatsApp de contacto y, si no, el correo del dueño."""
    if negocio is None:
        return {}
    dueno = await sesion.get(User, negocio.owner_user_id)
    return {
        "whatsapp": negocio.whatsapp_phone_e164 or (dueno.phone_e164 if dueno else None),
        "email": dueno.email if dueno else None,
    }
