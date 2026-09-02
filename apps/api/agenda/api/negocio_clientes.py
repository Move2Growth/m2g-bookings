"""Los clientes del salón, con su historial y su contador de faltas (RSV-5, RSV-6).

La regla que gobierna este archivo está en el modelo de datos y es la más fácil de equivocar
de todo el esquema: **un cliente pertenece a la plataforma; su ficha pertenece al negocio.**
La misma persona tiene ficha en la barbería de El Cangrejo y en el estudio de Obarrio, y son
dos fichas distintas con dos historiales distintos. Las notas que el barbero escribe sobre
ella no las puede leer nadie más, y su contador de faltas en un salón no la penaliza en el
otro.

El teléfono **sí** viaja aquí, y es la única superficie donde eso es correcto: el negocio
tiene el número de su clienta porque ella se lo dio al reservar, y llamarla cuando se retrasa
es literalmente el trabajo. Lo que no puede pasar —y no pasa— es que ese mismo campo salga por
un endpoint público.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.api.dependencias import SesionNegocio
from agenda.dominio.reservas import EstadoReserva
from agenda.errores import NoExiste
from agenda.modelos.clientes import BusinessClient
from agenda.modelos.equipo import StaffProfile
from agenda.modelos.reservas import Booking, BookingItem

router = APIRouter(prefix="/api/v1/negocio", tags=["clientes del negocio"])

#: Cuántas fichas se sirven por página. La búsqueda del mostrador se hace escribiendo cuatro
#: dígitos del teléfono, no paseando por la lista: si hacen falta más de dos páginas, lo que
#: falta es buscar mejor, no traer más filas.
POR_PAGINA = 30

#: Cuántas citas trae el historial de una ficha. Lo que el barbero mira antes de saludar es lo
#: último, no los cuatro años.
CITAS_EN_LA_FICHA = 20


class ClienteDelSalon(BaseModel):
    """Una ficha de la lista. Lleva lo que se decide de un vistazo."""

    id: uuid.UUID
    nombre: str
    telefono: str | None
    correo: str | None
    completadas: int
    ausencias: int = Field(description="Cuántas veces no se presentó **en este salón** (RSV-5)")
    canceladas: int
    bloqueado: bool
    motivo_bloqueo: str | None
    origen: str = Field(description="marketplace | manual | importado")
    ultima_cita: datetime | None
    tiene_cuenta: bool


class CitaDelHistorial(BaseModel):
    id: uuid.UUID
    inicio: datetime
    fin: datetime
    estado: EstadoReserva
    profesional: str
    servicios: list[str]
    total_centavos: int


class FichaDeCliente(ClienteDelSalon):
    """La ficha abierta: lo de la lista más las notas del negocio y el historial."""

    notas: str | None
    historial: list[CitaDelHistorial]


class CambioDeFichaDeCliente(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    telefono: str | None = Field(default=None, max_length=20)
    correo: str | None = Field(default=None, max_length=200)
    #: Lo que el negocio anota: alergias del tinte, cómo le gusta el corte. **No es historia
    #: clínica**: los datos de salud son RSV-6 v2 y necesitan consentimiento explícito bajo la
    #: Ley 81, así que aquí no se pide nada estructurado que se le parezca.
    notas: str | None = Field(default=None, max_length=2000)
    bloqueado: bool | None = None
    motivo_bloqueo: str | None = Field(default=None, max_length=200)


@router.get("/clientes", summary="Los clientes de este salón (RSV-6)")
async def listar_clientes(
    sesion_negocio: SesionNegocio,
    buscar: Annotated[
        str | None, Query(description="Parte del nombre o del teléfono; con cuatro dígitos basta")
    ] = None,
    solo_bloqueados: Annotated[bool, Query()] = False,
    pagina: Annotated[int, Query(ge=1)] = 1,
) -> list[ClienteDelSalon]:
    """La agenda de clientes del negocio activo. **Nunca la de otro**, ni buscando a propósito.

    El aislamiento no depende de este `WHERE`: aunque se cayera, la política de seguridad por
    fila devolvería lo mismo. El filtro está escrito igualmente porque es lo que hace que el
    planificador use el índice, y porque la intención tiene que estar en el código (ADR-0002).
    """
    sesion, identidad = sesion_negocio

    consulta = select(BusinessClient).where(BusinessClient.business_id == identidad.negocio_id)

    if buscar:
        patron = f"%{buscar.strip()}%"
        consulta = consulta.where(
            or_(
                BusinessClient.display_name.ilike(patron),
                BusinessClient.phone_e164.ilike(patron),
            )
        )
    if solo_bloqueados:
        consulta = consulta.where(BusinessClient.blocked.is_(True))

    consulta = (
        consulta.order_by(
            # Los de última hora arriba: es el orden en que se busca a alguien en un salón.
            # `NULLS LAST` para que las fichas recién creadas y sin cita no encabecen la lista.
            BusinessClient.last_booking_at.desc().nullslast(),
            BusinessClient.display_name,
        )
        .offset((pagina - 1) * POR_PAGINA)
        .limit(POR_PAGINA)
    )

    return [_pintar_cliente(fila) for fila in (await sesion.execute(consulta)).scalars().all()]


@router.get("/clientes/{cliente_id}", summary="Ficha con historial y notas (RSV-5, RSV-6)")
async def ver_cliente(cliente_id: uuid.UUID, sesion_negocio: SesionNegocio) -> FichaDeCliente:
    """La ficha abierta, con las últimas citas y quién las atendió."""
    sesion, identidad = sesion_negocio
    ficha = await _ficha_del_negocio(sesion, identidad.negocio_id, cliente_id)
    return FichaDeCliente(
        **_pintar_cliente(ficha).model_dump(),
        notas=ficha.notes,
        historial=await _historial(sesion, identidad.negocio_id, ficha.id),
    )


@router.patch("/clientes/{cliente_id}", summary="Editar la ficha y bloquear (RSV-5, RSV-6)")
async def editar_cliente(
    cliente_id: uuid.UUID, cambio: CambioDeFichaDeCliente, sesion_negocio: SesionNegocio
) -> FichaDeCliente:
    """Notas, contacto y **el bloqueo del reincidente**.

    Bloquear es del negocio y solo afecta al negocio: la misma persona sigue reservando sin
    problema en el salón de al lado. Un bloqueo que cruzara negocios sería una lista negra
    compartida, y eso ni está en el brief ni sería legal sin decírselo a nadie.
    """
    sesion, identidad = sesion_negocio
    ficha = await _ficha_del_negocio(sesion, identidad.negocio_id, cliente_id)

    for campo, columna in (
        ("nombre", "display_name"),
        ("telefono", "phone_e164"),
        ("correo", "email"),
        ("notas", "notes"),
        ("bloqueado", "blocked"),
        ("motivo_bloqueo", "blocked_reason"),
    ):
        valor = getattr(cambio, campo)
        if valor is not None:
            setattr(ficha, columna, valor)

    if cambio.bloqueado is False:
        ficha.blocked_reason = None

    await sesion.flush()
    return FichaDeCliente(
        **_pintar_cliente(ficha).model_dump(),
        notas=ficha.notes,
        historial=await _historial(sesion, identidad.negocio_id, ficha.id),
    )


async def _ficha_del_negocio(
    sesion: AsyncSession, negocio_id: uuid.UUID, cliente_id: uuid.UUID
) -> BusinessClient:
    ficha = (
        await sesion.execute(
            select(BusinessClient).where(
                BusinessClient.id == cliente_id,
                BusinessClient.business_id == negocio_id,
            )
        )
    ).scalar_one_or_none()
    if ficha is None:
        raise NoExiste("Ese cliente no existe en este negocio.")
    return ficha


async def _historial(
    sesion: AsyncSession, negocio_id: uuid.UUID, cliente_id: uuid.UUID
) -> list[CitaDelHistorial]:
    """Las últimas citas con su profesional y sus servicios. Dos consultas, no una por cita."""
    filas = (
        await sesion.execute(
            select(Booking, StaffProfile.display_name)
            .join(StaffProfile, StaffProfile.id == Booking.staff_id, isouter=True)
            .where(
                Booking.business_id == negocio_id,
                Booking.business_client_id == cliente_id,
            )
            .order_by(Booking.starts_at.desc())
            .limit(CITAS_EN_LA_FICHA)
        )
    ).all()
    if not filas:
        return []

    servicios: dict[uuid.UUID, list[str]] = {}
    for booking_id, nombre in (
        await sesion.execute(
            select(BookingItem.booking_id, BookingItem.name_snapshot)
            .where(BookingItem.booking_id.in_([reserva.id for reserva, _ in filas]))
            .order_by(BookingItem.position)
        )
    ).all():
        servicios.setdefault(booking_id, []).append(nombre)

    return [
        CitaDelHistorial(
            id=reserva.id,
            inicio=reserva.starts_at,
            fin=reserva.ends_at,
            estado=EstadoReserva(reserva.status),
            profesional=profesional or "",
            servicios=servicios.get(reserva.id, []),
            total_centavos=reserva.total_amount_minor,
        )
        for reserva, profesional in filas
    ]


def _pintar_cliente(ficha: BusinessClient) -> ClienteDelSalon:
    """Serializador **del negocio**: lleva teléfono y correo, y por eso no se comparte con
    ninguna respuesta pública."""
    return ClienteDelSalon(
        id=ficha.id,
        nombre=ficha.display_name,
        telefono=ficha.phone_e164,
        correo=ficha.email,
        completadas=ficha.completed_count,
        ausencias=ficha.no_show_count,
        canceladas=ficha.cancel_count,
        bloqueado=ficha.blocked,
        motivo_bloqueo=ficha.blocked_reason,
        origen=ficha.source,
        ultima_cita=ficha.last_booking_at,
        tiene_cuenta=ficha.user_id is not None,
    )


#: Lo importa el back-office para contar clientes sin repetir la consulta.
async def contar_clientes(sesion: AsyncSession, negocio_id: uuid.UUID) -> int:
    return (
        await sesion.execute(
            select(func.count())
            .select_from(BusinessClient)
            .where(BusinessClient.business_id == negocio_id)
        )
    ).scalar_one()
