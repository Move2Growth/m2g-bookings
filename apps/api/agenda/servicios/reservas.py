"""Crear, mover y cerrar reservas.

Aquí vive la escritura más delicada del producto. Tres cosas la caracterizan y ninguna es
opcional:

1. **La reserva y su ocupación se insertan en la misma transacción.** Si se separaran, existiría
   un instante en el que la cita está creada y su hueco todavía libre, y ese instante es
   suficiente para que entre otra.
2. **Quien decide si el hueco está libre es PostgreSQL**, con la restricción de exclusión
   (ADR-0004). Este módulo no comprueba solapes: los provoca y traduce el rechazo. Comprobar
   antes y confiar en que siga siendo cierto es la misma carrera con otro nombre.
3. **Los precios, las duraciones y los buffers se copian** del catálogo al reservar. Un catálogo
   mutable sin copia congelada reescribe el pasado: mañana el balayage cuesta otra cosa y la
   cita de ayer parecería haber costado eso.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.dominio.reservas import (
    Actor,
    EstadoReserva,
    PoliticaDeCancelacion,
    estado_inicial,
    validar_cancelacion_del_cliente,
    validar_transicion,
)
from agenda.errores import FueraDeAntelacion, ServicioNoDisponible, SlotNoDisponible
from agenda.modelos.catalogo import Service
from agenda.modelos.equipo import StaffProfile
from agenda.modelos.negocio import BusinessSettings
from agenda.modelos.reservas import Booking, BookingEvent, BookingItem, StaffOccupancy

#: «Violación de restricción de exclusión». Es el único error de la base que este módulo
#: interpreta; cualquier otro se deja subir tal cual, porque significa algo que no habíamos
#: previsto y taparlo lo escondería.
EXCLUSION_VIOLADA = "23P01"

#: Cómo se llama en el historial cada llegada a un estado. Las dos cancelaciones comparten
#: nombre de evento —el detalle de quién canceló ya viaja en `actor_kind` y en `from_status`—
#: para que el historial se lea como una historia y no como un volcado de la máquina.
_TIPO_DE_EVENTO = {
    EstadoReserva.CONFIRMADA: "confirmada",
    EstadoReserva.COMPLETADA: "completada",
    EstadoReserva.NO_SHOW: "no_show",
    EstadoReserva.CANCELADA_CLIENTE: "cancelada",
    EstadoReserva.CANCELADA_NEGOCIO: "cancelada",
    EstadoReserva.PENDIENTE: "creada",
}


def _es_solape(error: IntegrityError) -> bool:
    codigo = getattr(getattr(error, "orig", None), "sqlstate", None)
    return codigo == EXCLUSION_VIOLADA or EXCLUSION_VIOLADA in str(error)


@dataclass(frozen=True)
class PeticionDeReserva:
    """Lo que hace falta para crear una cita, venga del cliente o del mostrador."""

    negocio_id: uuid.UUID
    staff_id: uuid.UUID
    business_client_id: uuid.UUID
    servicios_ids: list[uuid.UUID]
    inicio: datetime
    origen: str  # cliente_web | cliente_app | negocio_manual | admin
    actor: Actor = Actor.CLIENTE
    client_user_id: uuid.UUID | None = None
    creada_por_user_id: uuid.UUID | None = None
    nota_cliente: str | None = None
    cualquier_profesional: bool = False


async def crear(
    sesion: AsyncSession, peticion: PeticionDeReserva, *, ahora: datetime | None = None
) -> Booking:
    """Crea la cita. Lanza `SlotNoDisponible` si alguien se adelantó por milisegundos.

    **No reintenta con el siguiente hueco.** Reservar otra hora en nombre de una persona que
    eligió esta es peor que decirle que se ocupó: mueve la sorpresa al día de la cita.
    """
    ahora = ahora or datetime.now(UTC)

    ajustes = await sesion.get(BusinessSettings, peticion.negocio_id)
    servicios = await _servicios_del_negocio(sesion, peticion)
    profesional = await _profesional_activo(sesion, peticion)

    duracion = sum((s.duration_min for s in servicios), 0)
    fin = peticion.inicio + timedelta(minutes=duracion)

    _validar_antelacion(peticion.inicio, ahora=ahora, ajustes=ajustes, actor=peticion.actor)

    reserva = Booking(
        business_id=peticion.negocio_id,
        staff_id=profesional.id,
        business_client_id=peticion.business_client_id,
        client_user_id=peticion.client_user_id,
        status=estado_inicial(auto_confirmar=ajustes.auto_confirm if ajustes else True).value,
        starts_at=peticion.inicio,
        ends_at=fin,
        total_duration_min=duracion,
        total_amount_minor=sum((s.price_minor or 0) for s in servicios),
        currency=servicios[0].currency,
        source=peticion.origen,
        any_staff_requested=peticion.cualquier_profesional,
        client_note=peticion.nota_cliente,
        created_by_user_id=peticion.creada_por_user_id,
        confirmed_at=ahora if (ajustes is None or ajustes.auto_confirm) else None,
    )
    sesion.add(reserva)
    await sesion.flush()  # necesitamos el identificador para lo que cuelga de él

    for posicion, servicio in enumerate(servicios, start=1):
        sesion.add(
            BookingItem(
                business_id=peticion.negocio_id,
                booking_id=reserva.id,
                position=posicion,
                service_id=servicio.id,
                name_snapshot=servicio.name,
                duration_min_snapshot=servicio.duration_min,
                price_kind_snapshot=servicio.price_kind,
                price_minor_snapshot=servicio.price_minor,
                currency=servicio.currency,
                buffer_before_min_snapshot=servicio.buffer_before_min,
                buffer_after_min_snapshot=servicio.buffer_after_min,
            )
        )

    # **Una sola fila de ocupación** para toda la cadena (D13): tres filas sueltas dejarían que
    # otra cita se colara entre el corte y la manicura.
    sesion.add(
        StaffOccupancy(
            business_id=peticion.negocio_id,
            staff_id=profesional.id,
            kind="reserva",
            status=reserva.status,
            booking_id=reserva.id,
            staff_user_id=profesional.user_id,
            starts_at=peticion.inicio,
            ends_at=fin,
            buffer_before_min=servicios[0].buffer_before_min,
            buffer_after_min=servicios[-1].buffer_after_min,
        )
    )

    sesion.add(
        BookingEvent(
            business_id=peticion.negocio_id,
            booking_id=reserva.id,
            type="creada",
            to_status=reserva.status,
            actor_kind=peticion.actor.value,
            actor_user_id=peticion.creada_por_user_id or peticion.client_user_id,
        )
    )

    try:
        await sesion.flush()
    except IntegrityError as error:
        if _es_solape(error):
            raise SlotNoDisponible() from error
        raise

    return reserva


async def cambiar_estado(
    sesion: AsyncSession,
    reserva: Booking,
    nuevo: EstadoReserva,
    *,
    actor: Actor,
    actor_user_id: uuid.UUID | None = None,
    motivo: str | None = None,
    ahora: datetime | None = None,
) -> Booking:
    """Mueve la cita de estado dejando rastro. El disparador espeja la ocupación."""
    ahora = ahora or datetime.now(UTC)
    anterior = EstadoReserva(reserva.status)
    validar_transicion(anterior, nuevo, actor)

    reserva.status = nuevo.value
    match nuevo:
        case EstadoReserva.CONFIRMADA:
            reserva.confirmed_at = ahora
        case EstadoReserva.COMPLETADA:
            reserva.completed_at = ahora
        case EstadoReserva.NO_SHOW:
            reserva.no_show_at = ahora
        case EstadoReserva.CANCELADA_CLIENTE | EstadoReserva.CANCELADA_NEGOCIO:
            reserva.cancelled_at = ahora
            reserva.cancelled_by = actor.value
            reserva.cancellation_reason = motivo
        case _:
            pass

    sesion.add(
        BookingEvent(
            business_id=reserva.business_id,
            booking_id=reserva.id,
            # El tipo de evento **nombra lo que pasó**, no la mecánica: «completada», no
            # «cambio_de_estado». Es lo que después se lee en el historial de la cita y en
            # soporte, y ahí «cambio_de_estado x3» no cuenta nada.
            type=_TIPO_DE_EVENTO[nuevo],
            from_status=anterior.value,
            to_status=nuevo.value,
            actor_kind=actor.value,
            actor_user_id=actor_user_id,
        )
    )
    await sesion.flush()
    return reserva


async def cancelar_por_el_cliente(
    sesion: AsyncSession,
    reserva: Booking,
    *,
    actor_user_id: uuid.UUID | None = None,
    ahora: datetime | None = None,
) -> Booking:
    """Cancelación del cliente, sujeta a la ventana del negocio (RSV-4)."""
    ahora = ahora or datetime.now(UTC)
    ajustes = await sesion.get(BusinessSettings, reserva.business_id)
    politica = PoliticaDeCancelacion(
        horas_antes=ajustes.client_cancel_window_hours if ajustes else 2
    )
    validar_cancelacion_del_cliente(ahora=ahora, empieza_en=reserva.starts_at, politica=politica)
    return await cambiar_estado(
        sesion,
        reserva,
        EstadoReserva.CANCELADA_CLIENTE,
        actor=Actor.CLIENTE,
        actor_user_id=actor_user_id,
        ahora=ahora,
    )


async def reprogramar(
    sesion: AsyncSession,
    reserva: Booking,
    *,
    nuevo_inicio: datetime,
    nuevo_staff_id: uuid.UUID | None = None,
    actor: Actor,
    actor_user_id: uuid.UUID | None = None,
    ahora: datetime | None = None,
) -> Booking:
    """Mueve la cita de hora **en una sola transacción**.

    El hueco viejo se libera y el nuevo se ocupa a la vez: si el nuevo está cogido, la cita se
    queda donde estaba. Lo contrario —liberar primero y ocupar después— deja a alguien sin cita
    y sin hueco al que volver si la segunda mitad falla.

    Y no es un estado nuevo (RSV-3): la cita sigue confirmada, cambia de hora y queda el evento.
    """
    ahora = ahora or datetime.now(UTC)
    duracion = timedelta(minutes=reserva.total_duration_min)
    anterior_inicio = reserva.starts_at

    ocupacion = (
        await sesion.execute(select(StaffOccupancy).where(StaffOccupancy.booking_id == reserva.id))
    ).scalar_one()

    reserva.starts_at = nuevo_inicio
    reserva.ends_at = nuevo_inicio + duracion
    reserva.reschedule_count = (reserva.reschedule_count or 0) + 1
    if nuevo_staff_id is not None:
        reserva.staff_id = nuevo_staff_id
        ocupacion.staff_id = nuevo_staff_id

    ocupacion.starts_at = nuevo_inicio
    ocupacion.ends_at = nuevo_inicio + duracion

    sesion.add(
        BookingEvent(
            business_id=reserva.business_id,
            booking_id=reserva.id,
            type="reprogramada",
            from_status=reserva.status,
            to_status=reserva.status,
            actor_kind=actor.value,
            actor_user_id=actor_user_id,
            payload={
                "antes": anterior_inicio.isoformat(),
                "despues": nuevo_inicio.isoformat(),
            },
        )
    )

    try:
        await sesion.flush()
    except IntegrityError as error:
        if _es_solape(error):
            raise SlotNoDisponible(
                "Ese horario se acaba de ocupar. La cita sigue en su hora original."
            ) from error
        raise

    return reserva


def _validar_antelacion(
    inicio: datetime, *, ahora: datetime, ajustes: BusinessSettings | None, actor: Actor
) -> None:
    """La antelación protege al cliente, no al negocio.

    Por eso **el mostrador puede saltársela**: si alguien entra por la puerta y hay hueco, el
    salón lo atiende ahora, no dentro de una hora. Lo que no puede es que un desconocido reserve
    para dentro de diez minutos y el equipo se entere cuando ya está allí.
    """
    if actor is Actor.NEGOCIO:
        return

    minima = timedelta(minutes=ajustes.min_lead_time_min if ajustes else 60)
    maxima = timedelta(days=ajustes.max_lead_time_days if ajustes else 60)

    if inicio < ahora + minima:
        raise FueraDeAntelacion(
            "Esa hora ya no se puede reservar con tan poca antelación. Elige otra."
        )
    if inicio > ahora + maxima:
        raise FueraDeAntelacion("Todavía no se puede reservar con tanta anticipación.")


async def _servicios_del_negocio(
    sesion: AsyncSession, peticion: PeticionDeReserva
) -> list[Service]:
    """Los servicios pedidos, activos y **en el orden en que se pidieron**."""
    if not peticion.servicios_ids:
        raise ServicioNoDisponible("Hay que elegir al menos un servicio.")

    filas = (
        (
            await sesion.execute(
                select(Service).where(
                    Service.business_id == peticion.negocio_id,
                    Service.id.in_(peticion.servicios_ids),
                    Service.active.is_(True),
                    Service.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    por_id = {fila.id: fila for fila in filas}
    faltan = [str(i) for i in peticion.servicios_ids if i not in por_id]
    if faltan:
        raise ServicioNoDisponible(
            "Alguno de los servicios elegidos ya no está disponible.", servicios=faltan
        )
    return [por_id[i] for i in peticion.servicios_ids]


async def _profesional_activo(sesion: AsyncSession, peticion: PeticionDeReserva) -> StaffProfile:
    profesional = await sesion.get(StaffProfile, peticion.staff_id)
    if (
        profesional is None
        or profesional.business_id != peticion.negocio_id
        or not profesional.active
    ):
        raise ServicioNoDisponible("Ese profesional ya no está disponible.")
    return profesional
