"""La agenda de un profesional: lo suyo, y nada más que lo suyo (STF-3).

Es la misma agenda del salón vista desde otro sitio, y por eso vive aparte: el barbero que
abre la aplicación entre cliente y cliente no quiere el panel del negocio, quiere su día.

**Aquí no hay ni un `if` de permisos, y es lo importante.** Quien acota lo que se ve es la
base de datos: la dependencia de sesión declara `app.current_staff_id` a partir del rol del
token y las políticas restrictivas de la migración 0006 hacen el resto. La diferencia con
comprobarlo aquí es que un endpoint nuevo que se olvide de comprobarlo **sigue sin poder ver
la agenda de otro** — el olvido no tiene consecuencias, que es de lo que va todo esto.

La ruta cuelga de `/mi/` porque es el punto de vista de la persona, pero **exige el token de
modo negocio**: la agenda es del salón y sin negocio activo no hay tenant que fijar. Entrar
aquí con el token de clienta devuelve `NO_AUTORIZADO` pidiendo cambiar a modo negocio.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from agenda.api.dependencias import SesionNegocio
from agenda.dominio.reservas import EstadoReserva
from agenda.modelos.clientes import BusinessClient
from agenda.modelos.equipo import StaffProfile
from agenda.modelos.negocio import Business
from agenda.modelos.reservas import Booking, BookingItem, StaffOccupancy

router = APIRouter(prefix="/api/v1/mi", tags=["agenda del profesional"])

#: Lo máximo que se sirve de una vez, igual que en el panel: un mes cabe.
VENTANA_MAXIMA = timedelta(days=31)


class CitaDelProfesional(BaseModel):
    """Una cita vista por quien la va a atender.

    Lleva el teléfono del cliente **a propósito**: es una superficie de negocio autenticada y
    llamar a quien se retrasa es el trabajo. Lo que nunca puede pasar es que este serializador
    acabe compartido con uno público, y por eso está aquí y no en un módulo común.
    """

    id: uuid.UUID
    inicio: datetime
    fin: datetime
    estado: EstadoReserva
    cliente: str
    cliente_id: uuid.UUID
    telefono: str | None
    servicios: list[str]
    duracion_minutos: int
    total_centavos: int
    nota_del_cliente: str | None


class BloqueoPropio(BaseModel):
    """Un tramo suyo en el que no atiende: almuerzo materializado, día libre, vacaciones."""

    id: uuid.UUID
    desde: datetime
    hasta: datetime
    motivo: str | None


class MiJornada(BaseModel):
    """Todo lo que hace falta para pintar el día de un profesional en una sola petición."""

    profesional_id: uuid.UUID
    profesional: str
    negocio: str
    zona_horaria: str = Field(description="Para pintar «10:00» sin recalcular en el cliente")
    citas: list[CitaDelProfesional]
    bloqueos: list[BloqueoPropio]


@router.get("/agenda", summary="Mi agenda como profesional (STF-3, AGD-2)")
async def mi_agenda(
    sesion_negocio: SesionNegocio,
    desde: Annotated[datetime | None, Query()] = None,
    hasta: Annotated[datetime | None, Query()] = None,
) -> MiJornada:
    """Las citas y los bloqueos de quien pregunta, en el rango pedido.

    Por rango y no por día, como el panel: siete peticiones para pintar una semana es media
    pantalla en blanco en 3G, que es la red en la que vive esto.

    Si quien pregunta es el **dueño**, ve su propia agenda como profesional si tiene ficha; si
    no la tiene, la respuesta viene vacía en vez de enseñarle la de otro. Para ver la agenda
    entera del salón está `GET /negocio/agenda`, que es otra pantalla y otra pregunta.
    """
    sesion, identidad = sesion_negocio

    desde = desde or datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    hasta = min(hasta or desde + timedelta(days=1), desde + VENTANA_MAXIMA)

    # Para el profesional, `identidad.staff_id` ya está resuelto por la dependencia; para el
    # dueño hay que buscarlo, porque él no lo declara —si lo declarara, se quedaría sin ver el
    # resto del salón en la misma sesión.
    staff_id = identidad.staff_id
    if staff_id is None:
        staff_id = (
            await sesion.execute(
                select(StaffProfile.id).where(
                    StaffProfile.business_id == identidad.negocio_id,
                    StaffProfile.user_id == identidad.usuario_id,
                    StaffProfile.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()

    negocio = await sesion.get(Business, identidad.negocio_id)
    perfil = await sesion.get(StaffProfile, staff_id) if staff_id else None

    vacia = MiJornada(
        profesional_id=staff_id or uuid.UUID(int=0),
        profesional=perfil.display_name if perfil else "",
        negocio=negocio.display_name if negocio else "",
        zona_horaria=negocio.timezone if negocio else "America/Panama",
        citas=[],
        bloqueos=[],
    )
    if staff_id is None:
        return vacia

    citas = (
        (
            await sesion.execute(
                select(Booking)
                .where(
                    Booking.business_id == identidad.negocio_id,
                    Booking.staff_id == staff_id,
                    Booking.starts_at < hasta,
                    Booking.ends_at > desde,
                )
                .order_by(Booking.starts_at)
            )
        )
        .scalars()
        .all()
    )

    servicios: dict[uuid.UUID, list[str]] = {}
    if citas:
        for booking_id, nombre in (
            await sesion.execute(
                select(BookingItem.booking_id, BookingItem.name_snapshot)
                .where(BookingItem.booking_id.in_([c.id for c in citas]))
                .order_by(BookingItem.position)
            )
        ).all():
            servicios.setdefault(booking_id, []).append(nombre)

    fichas = {}
    if citas:
        fichas = {
            ficha.id: ficha
            for ficha in (
                (
                    await sesion.execute(
                        select(BusinessClient).where(
                            BusinessClient.id.in_([c.business_client_id for c in citas])
                        )
                    )
                )
                .scalars()
                .all()
            )
        }

    bloqueos = (
        (
            await sesion.execute(
                select(StaffOccupancy)
                .where(
                    StaffOccupancy.business_id == identidad.negocio_id,
                    StaffOccupancy.staff_id == staff_id,
                    StaffOccupancy.kind == "bloqueo",
                    StaffOccupancy.status == "activo",
                    StaffOccupancy.blocked_to > desde,
                    StaffOccupancy.blocked_from < hasta,
                )
                .order_by(StaffOccupancy.starts_at)
            )
        )
        .scalars()
        .all()
    )

    return MiJornada(
        profesional_id=staff_id,
        profesional=perfil.display_name if perfil else "",
        negocio=negocio.display_name if negocio else "",
        zona_horaria=negocio.timezone if negocio else "America/Panama",
        citas=[
            CitaDelProfesional(
                id=cita.id,
                inicio=cita.starts_at,
                fin=cita.ends_at,
                estado=EstadoReserva(cita.status),
                cliente=(
                    fichas[cita.business_client_id].display_name
                    if cita.business_client_id in fichas
                    else "Cliente"
                ),
                cliente_id=cita.business_client_id,
                telefono=(
                    fichas[cita.business_client_id].phone_e164
                    if cita.business_client_id in fichas
                    else None
                ),
                servicios=servicios.get(cita.id, []),
                duracion_minutos=cita.total_duration_min,
                total_centavos=cita.total_amount_minor,
                nota_del_cliente=cita.client_note,
            )
            for cita in citas
        ],
        bloqueos=[
            BloqueoPropio(id=b.id, desde=b.starts_at, hasta=b.ends_at, motivo=b.reason)
            for b in bloqueos
        ],
    )
