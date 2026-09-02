"""Rutas del panel del negocio: la agenda y las citas.

Es la superficie que decide si la Fase 1 está hecha, porque el criterio literal es que **un
salón real pueda operar su agenda entera desde un teléfono**. Todo lo de aquí se usa de pie,
con una mano, entre cliente y cliente.

Dos consecuencias de diseño que se ven en las firmas:

* **La agenda se pide por rango, no por día.** Siete peticiones para pintar una semana en 3G es
  media pantalla en blanco.
* **El negocio sale del token**, nunca de la URL. Si viniera en la ruta, cambiar un
  identificador sería suficiente para pedir la agenda del salón de al lado, y la única barrera
  sería que a nadie se le olvidara comprobarlo en cada endpoint.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.api.dependencias import Identidad, SesionNegocio
from agenda.dominio.reservas import Actor, EstadoReserva
from agenda.errores import ReservaNoModificable
from agenda.modelos.clientes import BusinessClient
from agenda.modelos.reservas import Booking, BookingItem
from agenda.servicios import reservas as servicio_reservas

router = APIRouter(prefix="/api/v1/negocio", tags=["negocio"])

#: Lo máximo que se sirve de una vez. Un mes cabe; el histórico entero se consulta de otra
#: manera y no desde la pantalla que se abre cada mañana.
VENTANA_MAXIMA = timedelta(days=31)


class ServicioDeLaCita(BaseModel):
    nombre: str
    duracion_minutos: int
    precio_centavos: int | None


class CitaEnAgenda(BaseModel):
    """Una fila de la agenda. Lleva lo que se lee de un vistazo y nada más.

    El precio no está: en la agenda no se decide nada con él y ocuparía la línea donde va el
    servicio. Vive en el detalle de la cita.
    """

    id: uuid.UUID
    inicio: datetime
    fin: datetime
    estado: EstadoReserva
    profesional_id: uuid.UUID
    cliente: str
    tiene_telefono: bool = Field(
        default=False,
        description="Si hay número al que escribir; el número en sí no viaja en el listado",
    )
    servicios: list[ServicioDeLaCita]


class PeticionReservaManual(BaseModel):
    """Walk-in o teléfono: la cita que apunta el propio salón (AGD-2)."""

    profesional_id: uuid.UUID
    servicios: list[uuid.UUID]
    inicio: datetime
    cliente_id: uuid.UUID | None = None
    cliente_nombre: str | None = Field(
        default=None, description="Para el «cliente rápido» que aún no está en la ficha"
    )
    cliente_telefono: str | None = None
    nota: str | None = None


class CambioDeEstado(BaseModel):
    estado: EstadoReserva
    motivo: str | None = None


@router.get("/agenda", summary="Agenda del día o de la semana (AGD-2)")
async def agenda(
    sesion_negocio: SesionNegocio,
    desde: Annotated[datetime, Query()],
    hasta: Annotated[datetime, Query()],
    profesional: Annotated[uuid.UUID | None, Query()] = None,
) -> list[CitaEnAgenda]:
    sesion, identidad = sesion_negocio

    if hasta - desde > VENTANA_MAXIMA:
        hasta = desde + VENTANA_MAXIMA

    consulta = (
        select(Booking)
        .where(
            Booking.business_id == identidad.negocio_id,
            Booking.starts_at < hasta,
            Booking.ends_at > desde,
        )
        .order_by(Booking.starts_at)
    )
    if profesional is not None:
        consulta = consulta.where(Booking.staff_id == profesional)

    # El profesional solo ve su agenda (STF-3). **Quien lo impide es la base**: la
    # dependencia de sesión declaró `app.current_staff_id` y las políticas restrictivas de la
    # migración 0006 acotan la consulta aunque este filtro no estuviera. Se escribe igualmente
    # porque es lo que hace que el planificador use el índice y porque la intención tiene que
    # verse en el código (ADR-0002); pero si un día se cae de aquí, no se cae la garantía.
    if identidad.staff_id is not None:
        consulta = consulta.where(Booking.staff_id == identidad.staff_id)

    citas = (await sesion.execute(consulta)).scalars().all()
    return [await _pintar_cita(sesion, cita) for cita in citas]


@router.post("/reservas", status_code=201, summary="Reserva manual de walk-in o teléfono (AGD-2)")
async def crear_reserva_manual(
    peticion: PeticionReservaManual, sesion_negocio: SesionNegocio
) -> CitaEnAgenda:
    """La cita que apunta el salón. **Puede saltarse la antelación mínima**: si la persona ya
    está en la puerta, no tiene sentido decirle que vuelva dentro de una hora.

    Lo que no se salta es la restricción de exclusión: si el hueco está cogido, la base lo
    rechaza igual que a cualquiera.
    """
    sesion, identidad = sesion_negocio

    cliente_id = peticion.cliente_id
    if cliente_id is None:
        # El «cliente rápido» (AGD-2): se apunta un nombre y, si acaso, un teléfono. Su ficha
        # es del negocio, no una cuenta de la plataforma; si esa persona se registra algún día,
        # la ficha se enlaza y conserva su historial.
        cliente = BusinessClient(
            business_id=identidad.negocio_id,
            display_name=peticion.cliente_nombre or "Cliente sin nombre",
            source="manual",
            phone_e164=peticion.cliente_telefono,
        )
        sesion.add(cliente)
        await sesion.flush()
        cliente_id = cliente.id

    reserva = await servicio_reservas.crear(
        sesion,
        servicio_reservas.PeticionDeReserva(
            negocio_id=identidad.negocio_id,
            staff_id=peticion.profesional_id,
            business_client_id=cliente_id,
            servicios_ids=peticion.servicios,
            inicio=peticion.inicio,
            origen="negocio_manual",
            actor=Actor.NEGOCIO,
            creada_por_user_id=identidad.usuario_id,
            nota_cliente=peticion.nota,
        ),
    )
    return await _pintar_cita(sesion, reserva)


@router.post("/reservas/{reserva_id}/estado", summary="Confirmar, completar o marcar no-show")
async def cambiar_estado(
    reserva_id: uuid.UUID, cambio: CambioDeEstado, sesion_negocio: SesionNegocio
) -> CitaEnAgenda:
    """El no-show lo marca el negocio, que es quien estaba allí (RSV-5).

    Nunca lo marca el sistema al pasar la hora: una cita puede haberse atendido sin que nadie
    toque el móvil, y un no-show injusto le cuenta al cliente para acabar bloqueándolo.
    """
    sesion, identidad = sesion_negocio
    reserva = await _cita_del_negocio(sesion, identidad, reserva_id)

    await servicio_reservas.cambiar_estado(
        sesion,
        reserva,
        cambio.estado,
        actor=Actor.NEGOCIO,
        actor_user_id=identidad.usuario_id,
        motivo=cambio.motivo,
    )
    return await _pintar_cita(sesion, reserva)


@router.post("/reservas/{reserva_id}/reprogramar", summary="Mover una cita de hora (RSV-3)")
async def reprogramar(
    reserva_id: uuid.UUID,
    nuevo_inicio: Annotated[datetime, Query()],
    sesion_negocio: SesionNegocio,
    profesional: Annotated[uuid.UUID | None, Query()] = None,
) -> CitaEnAgenda:
    """Mover no es cancelar y volver a crear: la cita sigue siendo la misma y conserva su
    historial. Si el hueco nuevo está cogido, se queda donde estaba."""
    sesion, identidad = sesion_negocio
    reserva = await _cita_del_negocio(sesion, identidad, reserva_id)

    await servicio_reservas.reprogramar(
        sesion,
        reserva,
        nuevo_inicio=nuevo_inicio,
        nuevo_staff_id=profesional,
        actor=Actor.NEGOCIO,
        actor_user_id=identidad.usuario_id,
    )
    return await _pintar_cita(sesion, reserva)


async def _cita_del_negocio(
    sesion: AsyncSession, identidad: Identidad, reserva_id: uuid.UUID
) -> Booking:
    reserva = await sesion.get(Booking, reserva_id)
    # El aislamiento por fila ya impediría verla, pero la comprobación explícita convierte un
    # «no aparece» en un error claro y deja la intención escrita (ADR-0002).
    if reserva is None or reserva.business_id != identidad.negocio_id:
        raise ReservaNoModificable("Esa cita no existe en este negocio.")
    return reserva


async def _pintar_cita(sesion: AsyncSession, reserva: Booking) -> CitaEnAgenda:
    """Serializador **de negocio**. No se comparte con el público: ahí no va ni el nombre."""
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
    cliente = await sesion.get(BusinessClient, reserva.business_client_id)

    return CitaEnAgenda(
        id=reserva.id,
        inicio=reserva.starts_at,
        fin=reserva.ends_at,
        estado=EstadoReserva(reserva.status),
        profesional_id=reserva.staff_id,
        cliente=cliente.display_name if cliente else "Cliente",
        tiene_telefono=bool(cliente and cliente.phone_e164),
        servicios=[
            ServicioDeLaCita(
                nombre=item.name_snapshot,
                duracion_minutos=item.duration_min_snapshot,
                precio_centavos=item.price_minor_snapshot,
            )
            for item in items
        ],
    )
