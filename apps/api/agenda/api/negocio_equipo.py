"""El equipo del salón: fichas, visibilidad, servicios y horario propio (STF-1 a STF-3).

Lo que faltaba aquí es lo que un salón hace cada mes: alguien entra, alguien se va, alguien
cambia de turno y alguien deja de hacer barbas. Sin listar, editar ni desactivar, dar de alta
a un profesional era un viaje de ida.

**Que el horario del profesional sea distinto del horario del negocio es el caso normal**, no
la excepción: la ayudante entra a las once y el dueño abre a las ocho. Por eso el horario del
equipo tiene su propio endpoint y no es un porcentaje del horario del salón.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.api.comunes import url_de_media
from agenda.api.dependencias import SesionNegocio
from agenda.errores import DatoInvalido, NoExiste
from agenda.modelos.catalogo import Service
from agenda.modelos.equipo import StaffHours, StaffProfile, StaffService
from agenda.modelos.identidad import Membership
from agenda.modelos.reservas import Booking

router = APIRouter(prefix="/api/v1/negocio", tags=["equipo del negocio"])


class TramoDeHorario(BaseModel):
    """Un tramo semanal en **hora local del negocio**. No es un instante y no puede serlo."""

    dia: int = Field(ge=0, le=6, description="0 = lunes … 6 = domingo")
    desde: time
    hasta: time
    clase: str = Field(
        default="trabajo",
        pattern="^(trabajo|descanso)$",
        description="«trabajo» es jornada; «descanso» la recorta (el almuerzo de cada día)",
    )


class ProfesionalDelPanel(BaseModel):
    id: uuid.UUID
    nombre: str
    bio: str | None
    foto: str | None
    activo: bool
    visible_en_marketplace: bool
    acepta_cualquiera: bool = Field(
        description="Si entra en el reparto de «cualquier profesional disponible» (STF-5)"
    )
    orden: int
    tiene_cuenta: bool = Field(
        description="Si la persona ya aceptó la invitación; sin cuenta también se le agenda"
    )
    servicios: list[uuid.UUID]
    horario: list[TramoDeHorario]
    #: Citas vivas de aquí en adelante. Es lo que hace falta para avisar antes de desactivar a
    #: alguien que todavía tiene gente esperándole.
    citas_futuras: int


class CambioDeProfesional(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    bio: str | None = None
    foto: str | None = None
    activo: bool | None = None
    visible_en_marketplace: bool | None = None
    acepta_cualquiera: bool | None = None
    orden: int | None = Field(default=None, ge=0, le=999)


@router.get("/profesionales", summary="El equipo del salón (STF-1, STF-2)")
async def listar_profesionales(
    sesion_negocio: SesionNegocio,
    incluir_inactivos: Annotated[bool, Query()] = True,
) -> list[ProfesionalDelPanel]:
    sesion, identidad = sesion_negocio

    consulta = (
        select(StaffProfile)
        .where(
            StaffProfile.business_id == identidad.negocio_id,
            StaffProfile.deleted_at.is_(None),
        )
        .order_by(StaffProfile.position, StaffProfile.display_name)
    )
    if not incluir_inactivos:
        consulta = consulta.where(StaffProfile.active.is_(True))

    equipo = (await sesion.execute(consulta)).scalars().all()
    return await _pintar_equipo(sesion, identidad.negocio_id, list(equipo))


@router.patch("/profesionales/{profesional_id}", summary="Editar la ficha (STF-1, STF-2)")
async def editar_profesional(
    profesional_id: uuid.UUID, cambio: CambioDeProfesional, sesion_negocio: SesionNegocio
) -> ProfesionalDelPanel:
    """Activo o inactivo y visible u oculto son **dos cosas distintas** (STF-2).

    Inactivo = no se le agenda nada: se fue del salón o está de baja larga. Oculto = trabaja
    igual pero no sale en el marketplace, que es lo que quiere quien atiende solo a su clientela
    de siempre. Juntarlas obligaría a elegir entre desaparecer o aparecer, y ninguna de las dos
    es lo que pide un salón con un ayudante nuevo.
    """
    sesion, identidad = sesion_negocio
    profesional = await _profesional_del_negocio(sesion, identidad.negocio_id, profesional_id)

    for campo, columna in (
        ("nombre", "display_name"),
        ("bio", "bio"),
        ("foto", "photo_key"),
        ("activo", "active"),
        ("visible_en_marketplace", "visible_in_marketplace"),
        ("acepta_cualquiera", "accepts_any_staff"),
        ("orden", "position"),
    ):
        valor = getattr(cambio, campo)
        if valor is not None:
            setattr(profesional, columna, valor)

    await sesion.flush()
    return (await _pintar_equipo(sesion, identidad.negocio_id, [profesional]))[0]


@router.delete("/profesionales/{profesional_id}", summary="Dar de baja a alguien (STF-2)")
async def dar_de_baja(
    profesional_id: uuid.UUID,
    sesion_negocio: SesionNegocio,
    forzar: Annotated[
        bool, Query(description="Darlo de baja aunque tenga citas vivas por delante")
    ] = False,
) -> ProfesionalDelPanel:
    """Baja lógica. **Se niega si le quedan citas por atender**, salvo que se insista.

    Es la protección más barata contra el peor lunes posible: dar de baja a alguien un viernes
    y descubrir el lunes que sus quince citas de la semana desaparecieron de la agenda sin que
    nadie avisara a nadie. Si el dueño sabe lo que hace, `forzar=true` y adelante — pero
    habiéndolo leído.
    """
    sesion, identidad = sesion_negocio
    profesional = await _profesional_del_negocio(sesion, identidad.negocio_id, profesional_id)

    futuras = await _citas_futuras(sesion, identidad.negocio_id, [profesional.id])
    pendientes = futuras.get(profesional.id, 0)
    if pendientes and not forzar:
        raise DatoInvalido(
            f"A {profesional.display_name} le quedan {pendientes} citas por atender. "
            "Muévelas o cancélalas antes, o repite la baja forzándola.",
            citas_futuras=pendientes,
        )

    profesional.active = False
    profesional.visible_in_marketplace = False
    profesional.deleted_at = datetime.now(UTC)
    # La membresía se revoca **en el acto**, no cuando caduque su token (ADR-0006): los
    # permisos se resuelven contra la membresía en cada petición.
    membresia = (
        await sesion.execute(
            select(Membership).where(
                Membership.business_id == identidad.negocio_id,
                Membership.user_id == profesional.user_id,
                Membership.status == "activa",
            )
        )
    ).scalar_one_or_none()
    if membresia is not None:
        membresia.status = "revocada"
        membresia.revoked_at = datetime.now(UTC)

    await sesion.flush()
    return (await _pintar_equipo(sesion, identidad.negocio_id, [profesional]))[0]


@router.put("/profesionales/{profesional_id}/servicios", summary="Qué hace cada quien (SRV-3)")
async def asignar_servicios(
    profesional_id: uuid.UUID, servicios: list[uuid.UUID], sesion_negocio: SesionNegocio
) -> list[uuid.UUID]:
    """Reemplaza la lista entera. **Un servicio que no presta nadie no se puede reservar.**

    Se manda la lista completa y no altas y bajas sueltas porque la pantalla es una lista de
    casillas: mandar el estado final es lo que hace que dos dedos rápidos no dejen la
    asignación a medias.
    """
    sesion, identidad = sesion_negocio
    profesional = await _profesional_del_negocio(sesion, identidad.negocio_id, profesional_id)

    if servicios:
        existentes = set(
            (
                await sesion.execute(
                    select(Service.id).where(
                        Service.business_id == identidad.negocio_id,
                        Service.id.in_(servicios),
                        Service.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        faltan = [str(s) for s in servicios if s not in existentes]
        if faltan:
            raise DatoInvalido(
                "Alguno de esos servicios no existe en este negocio.", servicios=faltan
            )

    anteriores = (
        (
            await sesion.execute(
                select(StaffService).where(
                    StaffService.business_id == identidad.negocio_id,
                    StaffService.staff_id == profesional.id,
                )
            )
        )
        .scalars()
        .all()
    )
    for fila in anteriores:
        await sesion.delete(fila)
    await sesion.flush()

    for servicio_id in dict.fromkeys(servicios):
        sesion.add(
            StaffService(
                business_id=identidad.negocio_id,
                staff_id=profesional.id,
                service_id=servicio_id,
            )
        )
    await sesion.flush()
    return list(dict.fromkeys(servicios))


@router.get("/profesionales/{profesional_id}/horario", summary="Horario propio (STF-1, AGD-2)")
async def leer_horario_del_profesional(
    profesional_id: uuid.UUID, sesion_negocio: SesionNegocio
) -> list[TramoDeHorario]:
    sesion, identidad = sesion_negocio
    await _profesional_del_negocio(sesion, identidad.negocio_id, profesional_id)
    return await _horario_de(sesion, identidad.negocio_id, profesional_id)


@router.put("/profesionales/{profesional_id}/horario", summary="Poner su horario (STF-1, AGD-3)")
async def poner_horario_del_profesional(
    profesional_id: uuid.UUID, horario: list[TramoDeHorario], sesion_negocio: SesionNegocio
) -> list[TramoDeHorario]:
    """Jornada y descansos en la misma lista, distinguidos por `clase`.

    Van juntos porque se editan juntos: en la pantalla, el almuerzo es un hueco dentro del día
    y no una sección aparte. El motor sí los trata distinto —la jornada se interseca, el
    descanso se resta— y esa diferencia vive en el motor, no en la pantalla.

    **No borra citas que queden fuera del horario nuevo** (caso 4 del motor): el negocio decide
    qué hacer con ellas.
    """
    sesion, identidad = sesion_negocio
    # Un profesional puede editar **su** horario; el de otro, no. Quien lo impide es la
    # política restrictiva de la migración 0006: para él, las filas de `staff_hours` de otro
    # no existen, así que el borrado no borra nada y la inserción no entra.
    await _profesional_del_negocio(sesion, identidad.negocio_id, profesional_id)

    for tramo in horario:
        if tramo.clase == "descanso" and tramo.hasta <= tramo.desde:
            raise DatoInvalido(
                "Un descanso no puede cruzar la medianoche: pártelo en dos si hace falta."
            )

    anteriores = (
        (
            await sesion.execute(
                select(StaffHours).where(
                    StaffHours.business_id == identidad.negocio_id,
                    StaffHours.staff_id == profesional_id,
                )
            )
        )
        .scalars()
        .all()
    )
    for fila in anteriores:
        await sesion.delete(fila)
    await sesion.flush()

    for tramo in horario:
        sesion.add(
            StaffHours(
                business_id=identidad.negocio_id,
                staff_id=profesional_id,
                weekday=tramo.dia,
                starts_at=tramo.desde,
                ends_at=tramo.hasta,
                kind=tramo.clase,
            )
        )
    await sesion.flush()
    return await _horario_de(sesion, identidad.negocio_id, profesional_id)


async def _profesional_del_negocio(
    sesion: AsyncSession, negocio_id: uuid.UUID, profesional_id: uuid.UUID
) -> StaffProfile:
    """La ficha, o un 404.

    No hay comprobación de rol aquí y es a propósito: quién puede tocar la ficha de quién lo
    decide la base con las políticas de la migración 0006. Un profesional que pida la ficha de
    otro la ve —le hace falta para leer su propia agenda—, pero si intenta escribirla, el
    `UPDATE` no encuentra la fila. Repetir la regla aquí sería tener dos sitios donde
    equivocarse.
    """
    perfil = (
        await sesion.execute(
            select(StaffProfile).where(
                StaffProfile.id == profesional_id,
                StaffProfile.business_id == negocio_id,
                StaffProfile.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if perfil is None:
        raise NoExiste("Ese profesional no existe en este negocio.")
    return perfil


async def _horario_de(
    sesion: AsyncSession, negocio_id: uuid.UUID, profesional_id: uuid.UUID
) -> list[TramoDeHorario]:
    filas = (
        (
            await sesion.execute(
                select(StaffHours)
                .where(
                    StaffHours.business_id == negocio_id,
                    StaffHours.staff_id == profesional_id,
                )
                .order_by(StaffHours.weekday, StaffHours.starts_at)
            )
        )
        .scalars()
        .all()
    )
    return [
        TramoDeHorario(dia=f.weekday, desde=f.starts_at, hasta=f.ends_at, clase=f.kind)
        for f in filas
    ]


async def _citas_futuras(
    sesion: AsyncSession, negocio_id: uuid.UUID, staff_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Citas vivas de aquí en adelante, agrupadas por profesional. Una consulta para todos."""
    if not staff_ids:
        return {}
    filas = await sesion.execute(
        select(Booking.staff_id, func.count())
        .where(
            Booking.business_id == negocio_id,
            Booking.staff_id.in_(staff_ids),
            Booking.starts_at > datetime.now(UTC),
            Booking.status.in_(("pendiente", "confirmada")),
        )
        .group_by(Booking.staff_id)
    )
    return dict(filas.all())


async def _pintar_equipo(
    sesion: AsyncSession, negocio_id: uuid.UUID, equipo: list[StaffProfile]
) -> list[ProfesionalDelPanel]:
    if not equipo:
        return []
    ids = [p.id for p in equipo]

    asignados: dict[uuid.UUID, list[uuid.UUID]] = {}
    for staff_id, servicio_id in (
        await sesion.execute(
            select(StaffService.staff_id, StaffService.service_id).where(
                StaffService.business_id == negocio_id, StaffService.staff_id.in_(ids)
            )
        )
    ).all():
        asignados.setdefault(staff_id, []).append(servicio_id)

    horarios: dict[uuid.UUID, list[TramoDeHorario]] = {}
    for fila in (
        (
            await sesion.execute(
                select(StaffHours)
                .where(StaffHours.business_id == negocio_id, StaffHours.staff_id.in_(ids))
                .order_by(StaffHours.weekday, StaffHours.starts_at)
            )
        )
        .scalars()
        .all()
    ):
        horarios.setdefault(fila.staff_id, []).append(
            TramoDeHorario(
                dia=fila.weekday, desde=fila.starts_at, hasta=fila.ends_at, clase=fila.kind
            )
        )

    futuras = await _citas_futuras(sesion, negocio_id, ids)

    return [
        ProfesionalDelPanel(
            id=p.id,
            nombre=p.display_name,
            bio=p.bio,
            foto=url_de_media(p.photo_key),
            activo=p.active,
            visible_en_marketplace=p.visible_in_marketplace,
            acepta_cualquiera=p.accepts_any_staff,
            orden=p.position,
            tiene_cuenta=p.user_id is not None,
            servicios=asignados.get(p.id, []),
            horario=horarios.get(p.id, []),
            citas_futuras=futuras.get(p.id, 0),
        )
        for p in equipo
    ]
