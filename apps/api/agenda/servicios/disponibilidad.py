"""El puente entre la base de datos y el motor de disponibilidad.

El motor (`agenda.dominio.disponibilidad`) es puro a propósito: no sabe qué es una tabla ni
qué hora es. Este módulo es lo único que traduce en las dos direcciones —filas a objetos de
dominio, y huecos a respuesta— y por eso es también el único sitio donde hay que mirar cuando
el calendario enseña algo raro que las pruebas del motor no reproducen.

Una consulta por concepto y ninguna dentro de un bucle: la disponibilidad tiene un presupuesto
de 300 ms al percentil 95 y se pide con la pantalla abierta. Un `N+1` aquí se nota a simple
vista en 3G.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.dominio.disponibilidad import (
    AgendaProfesional,
    AjustesAgenda,
    ReglaHoraria,
    Servicio,
    Slot,
    calcular_slots,
    repartir_por_carga,
)
from agenda.dominio.reservas import ESTADOS_ACTIVOS
from agenda.dominio.tiempo import Intervalo
from agenda.errores import ServicioNoDisponible
from agenda.modelos.catalogo import Service
from agenda.modelos.equipo import StaffHours, StaffProfile, StaffService
from agenda.modelos.negocio import Business, BusinessHours, BusinessSettings
from agenda.modelos.reservas import StaffOccupancy

#: Tipos de fila de `staff_hours` que **no** son jornada de trabajo, sino su contrario.
#: El descanso recorta la jornada igual que un bloqueo, pero se declara en el horario semanal
#: del profesional en vez de en la tabla de ocupación.
CLASES_DE_AUSENCIA = ("descanso", "libre", "vacaciones")


@dataclass(frozen=True)
class Disponibilidad:
    """Lo que se devuelve al cliente: los huecos y el contexto para pintarlos bien."""

    slots: list[Slot]
    zona: str
    duracion_total: timedelta

    @property
    def hay_huecos(self) -> bool:
        return bool(self.slots)


async def calcular(
    sesion: AsyncSession,
    *,
    negocio_id: uuid.UUID,
    servicios_ids: list[uuid.UUID],
    desde: datetime,
    hasta: datetime,
    ahora: datetime,
    profesional_id: uuid.UUID | None = None,
    un_solo_profesional_por_hora: bool = True,
) -> Disponibilidad:
    """Huecos ofrecibles para uno o varios servicios encadenados (D13).

    `profesional_id` a `None` significa «cualquiera disponible» (STF-5): se calcula para todos
    los que prestan **todos** los servicios pedidos y, salvo que se pida lo contrario, cada
    hora se ofrece una sola vez asignada a quien menos agenda tenga ese día.
    """
    negocio = await sesion.get(Business, negocio_id)
    if negocio is None:
        raise ServicioNoDisponible("Ese negocio no existe o no está disponible.")

    ajustes_fila = await sesion.get(BusinessSettings, negocio_id)
    ajustes = _ajustes_de(ajustes_fila)

    servicios = await _cargar_servicios(sesion, negocio_id, servicios_ids)
    horario_negocio = await _horario_negocio(sesion, negocio_id)
    if not horario_negocio:
        # Un negocio sin horario no es un error: es un negocio a medio configurar, y la
        # respuesta correcta es «hoy no hay huecos», no una excepción.
        return Disponibilidad(slots=[], zona=negocio.timezone, duracion_total=_duracion(servicios))

    candidatos = await _profesionales_candidatos(sesion, negocio_id, servicios_ids, profesional_id)
    if not candidatos:
        return Disponibilidad(slots=[], zona=negocio.timezone, duracion_total=_duracion(servicios))

    ventana = Intervalo(desde, max(hasta, desde))
    horarios = await _horarios_de_profesionales(sesion, negocio_id, list(candidatos))
    ocupacion = await _ocupacion(sesion, negocio_id, list(candidatos), ventana, ajustes)

    agendas = [
        AgendaProfesional(
            profesional_id=str(staff.id),
            horario=horarios.get(staff.id, {}).get("trabajo", []),
            ocupacion=ocupacion.get(staff.id, []),
            descansos=horarios.get(staff.id, {}).get("descansos", []),
            activo=staff.active,
        )
        for staff in candidatos.values()
    ]

    slots = calcular_slots(
        ahora=ahora,
        zona=negocio.timezone,
        horario_negocio=horario_negocio,
        profesionales=agendas,
        servicios=servicios,
        desde=desde,
        hasta=hasta,
        ajustes=ajustes,
    )

    if profesional_id is None and un_solo_profesional_por_hora:
        carga = {str(staff_id): len(filas) for staff_id, filas in ocupacion.items()}
        slots = repartir_por_carga(slots, carga)

    return Disponibilidad(slots=slots, zona=negocio.timezone, duracion_total=_duracion(servicios))


def _duracion(servicios: list[Servicio]) -> timedelta:
    return sum((s.duracion for s in servicios), timedelta(0))


def _ajustes_de(fila: BusinessSettings | None) -> AjustesAgenda:
    """Los ajustes del negocio, o los valores por defecto si aún no los ha tocado."""
    if fila is None:
        return AjustesAgenda()
    return AjustesAgenda(
        granularidad=timedelta(minutes=fila.slot_granularity_min),
        antelacion_minima=timedelta(minutes=fila.min_lead_time_min),
        antelacion_maxima=timedelta(days=fila.max_lead_time_days),
    )


async def _cargar_servicios(
    sesion: AsyncSession, negocio_id: uuid.UUID, ids: list[uuid.UUID]
) -> list[Servicio]:
    """Carga los servicios **en el orden en que los pidió el cliente**.

    El orden importa: en una cadena, el buffer anterior es el del primero y el posterior el
    del último. Devolverlos en el orden de la base cambiaría los buffers de la reserva.
    """
    if not ids:
        raise ServicioNoDisponible("Hay que elegir al menos un servicio.")

    filas = (
        (
            await sesion.execute(
                select(Service).where(
                    Service.business_id == negocio_id,
                    Service.id.in_(ids),
                    Service.active.is_(True),
                    Service.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    por_id = {fila.id: fila for fila in filas}

    faltan = [str(i) for i in ids if i not in por_id]
    if faltan:
        raise ServicioNoDisponible(
            "Alguno de los servicios elegidos ya no está disponible.", servicios=faltan
        )

    return [
        Servicio(
            duracion=timedelta(minutes=por_id[i].duration_min),
            buffer_antes=timedelta(minutes=por_id[i].buffer_before_min),
            buffer_despues=timedelta(minutes=por_id[i].buffer_after_min),
        )
        for i in ids
    ]


async def _horario_negocio(sesion: AsyncSession, negocio_id: uuid.UUID) -> list[ReglaHoraria]:
    filas = (
        (await sesion.execute(select(BusinessHours).where(BusinessHours.business_id == negocio_id)))
        .scalars()
        .all()
    )
    return [ReglaHoraria(f.weekday, f.opens_at, f.closes_at) for f in filas]


async def _profesionales_candidatos(
    sesion: AsyncSession,
    negocio_id: uuid.UUID,
    servicios_ids: list[uuid.UUID],
    profesional_id: uuid.UUID | None,
) -> dict[uuid.UUID, StaffProfile]:
    """Quién puede atender **todos** los servicios pedidos.

    «Todos» y no «alguno»: en una cadena de corte y manicura, quien solo hace cortes no puede
    quedarse a medias. Ofrecer su hueco sería ofrecer una cita que no se puede cumplir.
    """
    consulta = select(StaffProfile).where(
        StaffProfile.business_id == negocio_id,
        StaffProfile.active.is_(True),
    )
    if profesional_id is not None:
        consulta = consulta.where(StaffProfile.id == profesional_id)

    profesionales = (await sesion.execute(consulta)).scalars().all()
    if not profesionales:
        return {}

    asignaciones = (
        await sesion.execute(
            select(StaffService.staff_id, StaffService.service_id).where(
                StaffService.business_id == negocio_id,
                StaffService.service_id.in_(servicios_ids),
            )
        )
    ).all()

    servicios_por_staff: dict[uuid.UUID, set[uuid.UUID]] = {}
    for staff_id, servicio_id in asignaciones:
        servicios_por_staff.setdefault(staff_id, set()).add(servicio_id)

    pedidos = set(servicios_ids)
    return {
        staff.id: staff
        for staff in profesionales
        if pedidos <= servicios_por_staff.get(staff.id, set())
    }


async def _horarios_de_profesionales(
    sesion: AsyncSession, negocio_id: uuid.UUID, staff_ids: list[uuid.UUID]
) -> dict[uuid.UUID, dict[str, list]]:
    """Separa la jornada de trabajo de lo que la recorta.

    Los descansos y los días libres viven en la misma tabla que la jornada, distinguidos por
    `kind`. Se devuelven aparte porque el motor los trata distinto: la jornada se interseca,
    las ausencias se restan.
    """
    filas = (
        (
            await sesion.execute(
                select(StaffHours).where(
                    StaffHours.business_id == negocio_id,
                    StaffHours.staff_id.in_(staff_ids),
                )
            )
        )
        .scalars()
        .all()
    )

    resultado: dict[uuid.UUID, dict[str, list]] = {
        staff_id: {"trabajo": [], "descansos": []} for staff_id in staff_ids
    }
    for fila in filas:
        regla = ReglaHoraria(fila.weekday, fila.starts_at, fila.ends_at)
        clave = "descansos" if fila.kind in CLASES_DE_AUSENCIA else "trabajo"
        resultado[fila.staff_id][clave].append(regla)
    return resultado


async def _ocupacion(
    sesion: AsyncSession,
    negocio_id: uuid.UUID,
    staff_ids: list[uuid.UUID],
    ventana: Intervalo,
    ajustes: AjustesAgenda,
) -> dict[uuid.UUID, list[Intervalo]]:
    """Lo que ya está ocupado: citas vivas y bloqueos activos, con sus buffers dentro.

    Se lee `blocked_from`/`blocked_to`, que es lo que de verdad bloquea la agenda y lo mismo
    que mira la restricción de exclusión. Leer `starts_at`/`ends_at` aquí haría que el motor
    ofreciera huecos que la base rechazaría al confirmar.
    """
    # Un margen a los lados para no perder la cita que empieza antes de la ventana y termina
    # dentro, ni el bloqueo que la abraza entera.
    margen = (
        ajustes.antelacion_maxima if ventana.duracion > timedelta(days=7) else timedelta(days=1)
    )
    estados_vivos = tuple(e.value for e in ESTADOS_ACTIVOS)

    filas = (
        await sesion.execute(
            select(
                StaffOccupancy.staff_id,
                StaffOccupancy.blocked_from,
                StaffOccupancy.blocked_to,
            ).where(
                StaffOccupancy.business_id == negocio_id,
                StaffOccupancy.staff_id.in_(staff_ids),
                StaffOccupancy.blocked_to > ventana.inicio - margen,
                StaffOccupancy.blocked_from < ventana.fin + margen,
                ((StaffOccupancy.kind == "reserva") & StaffOccupancy.status.in_(estados_vivos))
                | ((StaffOccupancy.kind == "bloqueo") & (StaffOccupancy.status == "activo")),
            )
        )
    ).all()

    ocupacion: dict[uuid.UUID, list[Intervalo]] = {staff_id: [] for staff_id in staff_ids}
    for staff_id, desde, hasta in filas:
        ocupacion[staff_id].append(Intervalo(desde, hasta))
    return ocupacion
