"""Lo que hace una persona cuando reserva: `/mi/…`.

La diferencia con `/negocio/…` no es de permisos, es de **punto de vista**. Aquí la persona ve
lo suyo en todos los salones donde ha estado; allí el salón ve todo lo que pasa dentro de sus
paredes. Por eso las dos superficies tienen su propio serializador y su propia sesión: lo que
la clienta puede ver de su cita no es lo mismo que ve el negocio, y compartir el código sería
la forma más rápida de que se cruzaran.

Reservar exige **teléfono verificado** (D9). No hay reserva como invitado, y no es un capricho:
es lo único que sostiene el control de no-shows sin pedir un depósito por adelantado.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from agenda.api.dependencias import Identidad, SesionPlataforma, identidad_actual
from agenda.dominio.reservas import Actor, EstadoReserva
from agenda.errores import (
    NegocioNoPublicado,
    ReservaNoModificable,
    TelefonoNoVerificado,
)
from agenda.modelos.clientes import BusinessClient
from agenda.modelos.identidad import User
from agenda.modelos.negocio import Business
from agenda.modelos.reservas import Booking, BookingItem
from agenda.servicios import reservas as servicio_reservas

router = APIRouter(prefix="/api/v1/mi", tags=["cliente"])


class ServicioDeMiCita(BaseModel):
    nombre: str
    duracion_minutos: int
    precio_centavos: int | None


class MiCita(BaseModel):
    """Una cita vista **por quien la reservó**: dónde, cuándo y con qué servicios."""

    id: uuid.UUID
    negocio: str
    negocio_slug: str
    inicio: datetime
    fin: datetime
    estado: EstadoReserva
    zona_horaria: str
    servicios: list[ServicioDeMiCita]
    total_centavos: int
    #: Si todavía se puede cancelar sin llamar al salón (RSV-4). Lo calcula el servidor: si lo
    #: decidiera la pantalla, dos relojes distintos darían dos respuestas distintas.
    se_puede_cancelar: bool


class PeticionDeReserva(BaseModel):
    negocio_slug: str
    servicios: list[uuid.UUID] = Field(min_length=1)
    inicio: datetime
    profesional_id: uuid.UUID
    nota: str | None = None


@router.get("/reservas", summary="Mis reservas (RSV-7)")
async def mis_reservas(
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> list[MiCita]:
    """El historial de la persona, en todos los salones donde ha reservado.

    Se apoya en `client_user_id`, que está desnormalizado a propósito: si hubiera que cruzar
    las fichas de cliente de cada negocio, la pantalla de inicio de la app haría una consulta
    por salón (ADR sobre el modelo, §8.1).
    """
    filas = (
        (
            await sesion.execute(
                select(Booking)
                .where(Booking.client_user_id == identidad.usuario_id)
                .order_by(Booking.starts_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    return [await _pintar(sesion, reserva) for reserva in filas]


@router.post("/reservas", status_code=201, summary="Reservar (RSV-1, AGD-4)")
async def reservar(
    peticion: PeticionDeReserva,
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> MiCita:
    """Crea la cita. Devuelve `409 SLOT_NO_DISPONIBLE` si alguien se adelantó.

    Mirar un hueco no lo aparta: se compite por él al confirmar, y quien pierde recibe un
    mensaje que entiende en vez de una cita a otra hora que no eligió.
    """
    usuario = await sesion.get(User, identidad.usuario_id)
    if usuario is None or usuario.phone_verified_at is None:
        raise TelefonoNoVerificado()

    negocio = (
        await sesion.execute(
            select(Business).where(
                Business.slug == peticion.negocio_slug, Business.status == "publicado"
            )
        )
    ).scalar_one_or_none()
    if negocio is None:
        raise NegocioNoPublicado()

    # El resto del trabajo ocurre **con el negocio fijado**: crear la cita toca la agenda del
    # salón, y esa es su casa. La ficha de cliente también es suya —cada salón tiene la suya,
    # con su historial y su contador de no-shows—, y por eso se busca o se crea aquí dentro.
    await sesion.execute(
        text("SELECT set_config('app.current_business_id', :negocio, true)"),
        {"negocio": str(negocio.id)},
    )

    ficha = (
        await sesion.execute(
            select(BusinessClient).where(
                BusinessClient.business_id == negocio.id,
                BusinessClient.user_id == usuario.id,
            )
        )
    ).scalar_one_or_none()

    if ficha is None:
        ficha = BusinessClient(
            business_id=negocio.id,
            user_id=usuario.id,
            display_name=usuario.full_name or "Cliente",
            phone_e164=usuario.phone_e164,
            source="marketplace",
        )
        sesion.add(ficha)
        await sesion.flush()

    reserva = await servicio_reservas.crear(
        sesion,
        servicio_reservas.PeticionDeReserva(
            negocio_id=negocio.id,
            staff_id=peticion.profesional_id,
            business_client_id=ficha.id,
            servicios_ids=peticion.servicios,
            inicio=peticion.inicio,
            origen="cliente_web",
            actor=Actor.CLIENTE,
            client_user_id=usuario.id,
            nota_cliente=peticion.nota,
        ),
    )
    return await _pintar(sesion, reserva)


@router.post("/reservas/{reserva_id}/cancelar", summary="Cancelar mi cita (RSV-4)")
async def cancelar(
    reserva_id: uuid.UUID,
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> MiCita:
    """Cancelar dentro de la ventana del negocio. Pasada, la cita la mueve el salón.

    A dos horas de la cita el hueco ya no se vuelve a llenar, y el salón tiene derecho a
    enterarse por una conversación y no por una notificación.
    """
    reserva = await sesion.get(Booking, reserva_id)
    if reserva is None or reserva.client_user_id != identidad.usuario_id:
        raise ReservaNoModificable("Esa reserva no es tuya o ya no existe.")

    await sesion.execute(
        text("SELECT set_config('app.current_business_id', :negocio, true)"),
        {"negocio": str(reserva.business_id)},
    )
    await servicio_reservas.cancelar_por_el_cliente(
        sesion, reserva, actor_user_id=identidad.usuario_id
    )
    return await _pintar(sesion, reserva)


async def _pintar(sesion, reserva: Booking) -> MiCita:
    """Serializador **del cliente**. No comparte código con el del negocio, a propósito."""
    await sesion.execute(
        text("SELECT set_config('app.current_business_id', :negocio, true)"),
        {"negocio": str(reserva.business_id)},
    )

    negocio = await sesion.get(Business, reserva.business_id)
    items = (
        (
            await sesion.execute(
                select(BookingItem)
                .where(BookingItem.booking_id == reserva.id)
                .order_by(BookingItem.position)
            )
        )
        .scalars()
        .all()
    )

    estado = EstadoReserva(reserva.status)
    vive = estado in {EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA}
    # La ventana la sirve el servidor ya resuelta: si la pantalla la calculara, el reloj del
    # teléfono decidiría quién puede cancelar.
    margen = timedelta(hours=2)
    se_puede_cancelar = vive and reserva.starts_at > datetime.now(UTC) + margen

    return MiCita(
        id=reserva.id,
        negocio=negocio.display_name if negocio else "",
        negocio_slug=negocio.slug if negocio else "",
        inicio=reserva.starts_at,
        fin=reserva.ends_at,
        estado=estado,
        zona_horaria=negocio.timezone if negocio else "America/Panama",
        servicios=[
            ServicioDeMiCita(
                nombre=item.name_snapshot,
                duracion_minutos=item.duration_min_snapshot,
                precio_centavos=item.price_minor_snapshot,
            )
            for item in items
        ],
        total_centavos=reserva.total_amount_minor,
        se_puede_cancelar=se_puede_cancelar,
    )
