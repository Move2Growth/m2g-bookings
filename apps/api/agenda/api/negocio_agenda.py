"""Horario del salón, ausencias del equipo y cierres puntuales (AGD-2, AGD-3, AGD-6).

Todo lo que le quita horas a la agenda vive en dos sitios y **no es arbitrario cuál**:

* Lo **recurrente en hora local** —la jornada y el almuerzo de todos los días— son reglas
  semanales (`business_hours`, `staff_hours`). No son instantes y no pueden serlo: no tienen
  fecha. El motor las convierte a instantes en un único sitio (ADR-0003).
* Lo **puntual** —las vacaciones de agosto, la tarde del médico, el 3 de noviembre que el
  salón cierra— son filas de ocupación (`staff_occupancy` con `kind = 'bloqueo'`). Viven ahí y
  no en una tabla propia por una razón que ADR-0004 deja escrita: si el almuerzo viviera en
  otra tabla, **PostgreSQL no podría impedir que le encajaran una cita encima**. Compartiendo
  tabla comparten restricción de exclusión, y entonces sí.

De ahí una consecuencia que se ve al usarlo: intentar bloquear un tramo que ya tiene citas
dentro **falla**, con `409` y diciéndolo. Es lo correcto — el sistema no puede hacer
desaparecer las citas de tres clientas porque alguien marcó unas vacaciones; y tampoco puede
dejar el bloqueo a medias, porque entonces no bloquea.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.api.dependencias import SesionNegocio, exigir_dueno
from agenda.errores import DatoInvalido, NoExiste, SlotNoDisponible
from agenda.modelos.equipo import StaffProfile
from agenda.modelos.marketplace import Holiday
from agenda.modelos.negocio import Business, BusinessHours, BusinessSettings
from agenda.modelos.reservas import StaffOccupancy

router = APIRouter(prefix="/api/v1/negocio", tags=["agenda del negocio"])

#: `SQLSTATE 23P01` — violación de restricción de exclusión. Igual que al reservar: el único
#: error de la base que se traduce; cualquier otro sube tal cual porque significa algo que no
#: habíamos previsto y taparlo lo escondería.
EXCLUSION_VIOLADA = "23P01"

#: Cuánto se puede pedir de bloqueos de una vez. Lo mismo que la agenda: un mes cabe.
VENTANA_MAXIMA = timedelta(days=93)


class TramoDelNegocio(BaseModel):
    """Un tramo de apertura. Varias filas por día = jornada partida, que es lo normal."""

    dia: int = Field(ge=0, le=6, description="0 = lunes … 6 = domingo")
    abre: time
    cierra: time = Field(
        description="Si es menor o igual que «abre», el tramo cruza la medianoche (spa de noche)"
    )


class AjustesDeAgenda(BaseModel):
    """Los números que el brief deja configurables (AGD-1, RSV-4, D10, REV-1).

    **Ninguno vive como constante en el código.** Cambiar la granularidad a 30 minutos o la
    ventana de cancelación a 24 horas es editar esta fila, no desplegar.
    """

    granularidad_minutos: int = Field(ge=5, le=120)
    antelacion_minima_minutos: int = Field(ge=0, le=60 * 24 * 30)
    antelacion_maxima_dias: int = Field(ge=1, le=365)
    auto_confirmar: bool
    ventana_cancelacion_horas: int = Field(ge=0, le=24 * 14)
    ventana_resena_dias: int = Field(ge=1, le=365)
    bloquear_tras_ausencias: int | None = Field(
        default=None, ge=1, le=20, description="NULL = no bloquear a nadie por no-shows (RSV-5)"
    )
    permitir_cualquier_profesional: bool
    resumen_diario: bool


class CambioDeAjustes(BaseModel):
    granularidad_minutos: int | None = Field(default=None, ge=5, le=120)
    antelacion_minima_minutos: int | None = Field(default=None, ge=0, le=60 * 24 * 30)
    antelacion_maxima_dias: int | None = Field(default=None, ge=1, le=365)
    auto_confirmar: bool | None = None
    ventana_cancelacion_horas: int | None = Field(default=None, ge=0, le=24 * 14)
    ventana_resena_dias: int | None = Field(default=None, ge=1, le=365)
    bloquear_tras_ausencias: int | None = Field(default=None, ge=1, le=20)
    permitir_cualquier_profesional: bool | None = None
    resumen_diario: bool | None = None


class Ausencia(BaseModel):
    """Un tramo concreto en el que alguien no está: vacaciones, día libre, médico (AGD-3)."""

    id: uuid.UUID
    profesional_id: uuid.UUID
    profesional: str
    desde: datetime
    hasta: datetime
    motivo: str | None
    activa: bool


class AltaDeAusencia(BaseModel):
    profesional_id: uuid.UUID | None = Field(
        default=None, description="NULL = cierre del salón entero: se bloquea a todo el equipo"
    )
    desde: datetime
    hasta: datetime
    motivo: str | None = Field(default=None, max_length=200)


class FeriadoSugerido(BaseModel):
    """Un feriado de Panamá **sugerido, no impuesto** (AGD-6).

    Un salón de barrio abre el día de la madre precisamente porque es el día de la madre. La
    lista es un dato administrable, no código, y cerrar ese día es una decisión del dueño.
    """

    fecha: date
    nombre: str
    ya_cerrado: bool


@router.get("/horario", summary="Horario semanal del salón (AGD-2, NEG-1)")
async def leer_horario(sesion_negocio: SesionNegocio) -> list[TramoDelNegocio]:
    sesion, identidad = sesion_negocio
    filas = (
        (
            await sesion.execute(
                select(BusinessHours)
                .where(BusinessHours.business_id == identidad.negocio_id)
                .order_by(BusinessHours.weekday, BusinessHours.opens_at)
            )
        )
        .scalars()
        .all()
    )
    return [TramoDelNegocio(dia=f.weekday, abre=f.opens_at, cierra=f.closes_at) for f in filas]


@router.get("/ajustes", summary="Los números configurables del salón (AGD-1, D10)")
async def leer_ajustes(sesion_negocio: SesionNegocio) -> AjustesDeAgenda:
    sesion, identidad = sesion_negocio
    fila = await _ajustes_del_negocio(sesion, identidad.negocio_id)
    return _pintar_ajustes(fila)


@router.patch("/ajustes", summary="Cambiar los números sin desplegar (AGD-1, RSV-4, D10)")
async def cambiar_ajustes(
    cambio: CambioDeAjustes, sesion_negocio: SesionNegocio
) -> AjustesDeAgenda:
    """Cambia lo que venga. **No toca las citas que ya existen.**

    Subir la antelación mínima a tres horas no cancela la cita de dentro de dos: esa ya está
    hecha y el hueco está apartado. Lo que cambia es lo que se ofrece a partir de ahora.
    """
    sesion, identidad = sesion_negocio
    # Los ajustes de agenda son configuración del salón, no de una persona (STF-3).
    exigir_dueno(identidad)
    fila = await _ajustes_del_negocio(sesion, identidad.negocio_id)

    for campo, columna in (
        ("granularidad_minutos", "slot_granularity_min"),
        ("antelacion_minima_minutos", "min_lead_time_min"),
        ("antelacion_maxima_dias", "max_lead_time_days"),
        ("auto_confirmar", "auto_confirm"),
        ("ventana_cancelacion_horas", "client_cancel_window_hours"),
        ("ventana_resena_dias", "review_window_days"),
        ("permitir_cualquier_profesional", "allow_any_staff"),
        ("resumen_diario", "daily_digest_enabled"),
    ):
        valor = getattr(cambio, campo)
        if valor is not None:
            setattr(fila, columna, valor)

    # Igual que el precio del servicio: `None` significa dos cosas distintas —«no lo cambies» y
    # «no bloquees a nadie»— y se distinguen mirando si el campo venía en el cuerpo.
    enviados = cambio.model_dump(exclude_unset=True)
    if "bloquear_tras_ausencias" in enviados:
        fila.no_show_block_threshold = enviados["bloquear_tras_ausencias"]

    await sesion.flush()
    return _pintar_ajustes(fila)


@router.get("/ausencias", summary="Vacaciones, días libres y cierres puntuales (AGD-3)")
async def listar_ausencias(
    sesion_negocio: SesionNegocio,
    desde: Annotated[datetime | None, Query()] = None,
    hasta: Annotated[datetime | None, Query()] = None,
    incluir_levantadas: Annotated[bool, Query()] = False,
) -> list[Ausencia]:
    """Los bloqueos del equipo en un rango. Por defecto, de hoy en adelante."""
    sesion, identidad = sesion_negocio

    desde = desde or datetime.now(UTC)
    hasta = min(hasta or desde + VENTANA_MAXIMA, desde + VENTANA_MAXIMA)

    consulta = (
        select(StaffOccupancy, StaffProfile.display_name)
        .join(StaffProfile, StaffProfile.id == StaffOccupancy.staff_id)
        .where(
            StaffOccupancy.business_id == identidad.negocio_id,
            StaffOccupancy.kind == "bloqueo",
            StaffOccupancy.blocked_to > desde,
            StaffOccupancy.blocked_from < hasta,
        )
        .order_by(StaffOccupancy.starts_at)
    )
    if not incluir_levantadas:
        consulta = consulta.where(StaffOccupancy.status == "activo")

    return [
        Ausencia(
            id=fila.id,
            profesional_id=fila.staff_id,
            profesional=nombre,
            desde=fila.starts_at,
            hasta=fila.ends_at,
            motivo=fila.reason,
            activa=fila.status == "activo",
        )
        for fila, nombre in (await sesion.execute(consulta)).all()
    ]


@router.post("/ausencias", status_code=201, summary="Bloquear un tramo (AGD-3, AGD-6)")
async def crear_ausencia(alta: AltaDeAusencia, sesion_negocio: SesionNegocio) -> list[Ausencia]:
    """Bloquea a una persona o a **todo el equipo**, que es como se cierra el salón un día.

    Devuelve una lista porque un cierre del salón son tantas filas como profesionales activos:
    la agenda es por persona y la restricción de exclusión también, así que no hay una fila
    «del negocio» que pueda bloquear a todos a la vez. Verlo como lista es además lo honesto,
    porque después se puede levantar el bloqueo de uno sin levantar el de los demás.

    Si dentro del tramo ya hay citas, **no se bloquea nada** y sale `409`: la transacción es
    una sola, así que o entran todos los bloqueos o no entra ninguno.
    """
    sesion, identidad = sesion_negocio

    if alta.hasta <= alta.desde:
        raise DatoInvalido("El tramo bloqueado tiene que terminar después de empezar.")

    equipo = await _equipo_objetivo(sesion, identidad.negocio_id, alta.profesional_id)

    creadas = [
        StaffOccupancy(
            business_id=identidad.negocio_id,
            staff_id=profesional.id,
            kind="bloqueo",
            status="activo",
            staff_user_id=profesional.user_id,
            starts_at=alta.desde,
            ends_at=alta.hasta,
            reason=alta.motivo,
        )
        for profesional in equipo
    ]
    for fila in creadas:
        sesion.add(fila)

    try:
        await sesion.flush()
    except IntegrityError as error:
        if _es_solape(error):
            raise SlotNoDisponible(
                "Ese tramo ya tiene citas dentro. Muévelas o cancélalas antes de bloquearlo."
            ) from error
        raise

    nombres = {p.id: p.display_name for p in equipo}
    return [
        Ausencia(
            id=fila.id,
            profesional_id=fila.staff_id,
            profesional=nombres[fila.staff_id],
            desde=fila.starts_at,
            hasta=fila.ends_at,
            motivo=fila.reason,
            activa=True,
        )
        for fila in creadas
    ]


@router.delete("/ausencias/{ausencia_id}", summary="Levantar un bloqueo (AGD-3)")
async def levantar_ausencia(ausencia_id: uuid.UUID, sesion_negocio: SesionNegocio) -> Ausencia:
    """Levanta el bloqueo **sin borrar la fila**, igual que cancelar una cita.

    La restricción de exclusión solo mira los bloqueos `activo`, así que el hueco vuelve a
    ofrecerse de inmediato; y queda el rastro de que ese día estuvo cerrado, que es lo que
    hace falta para entender una agenda vacía tres meses después.
    """
    sesion, identidad = sesion_negocio

    fila = (
        await sesion.execute(
            select(StaffOccupancy).where(
                StaffOccupancy.id == ausencia_id,
                StaffOccupancy.business_id == identidad.negocio_id,
                StaffOccupancy.kind == "bloqueo",
            )
        )
    ).scalar_one_or_none()
    if fila is None:
        raise NoExiste("Ese bloqueo no existe en este negocio.")

    fila.status = "levantado"
    await sesion.flush()

    profesional = await sesion.get(StaffProfile, fila.staff_id)
    return Ausencia(
        id=fila.id,
        profesional_id=fila.staff_id,
        profesional=profesional.display_name if profesional else "",
        desde=fila.starts_at,
        hasta=fila.ends_at,
        motivo=fila.reason,
        activa=False,
    )


@router.get("/feriados", summary="Feriados de Panamá sugeridos (AGD-6)")
async def listar_feriados(
    sesion_negocio: SesionNegocio,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
) -> list[FeriadoSugerido]:
    """Los feriados del país del negocio, con la marca de si el salón ya cerró ese día.

    **Sugeridos, no impuestos**: la respuesta dice qué días son feriado y cuáles ya están
    cerrados; cerrar es un `POST /negocio/ausencias` como cualquier otro. Media ciudad abre el
    día de la madre.
    """
    sesion, identidad = sesion_negocio
    negocio = await sesion.get(Business, identidad.negocio_id)

    hoy = datetime.now(UTC).date()
    desde = desde or hoy
    hasta = hasta or date(desde.year, 12, 31)

    feriados = (
        (
            await sesion.execute(
                select(Holiday)
                .where(
                    Holiday.country_code == (negocio.country_code if negocio else "PA"),
                    Holiday.date >= desde,
                    Holiday.date <= hasta,
                )
                .order_by(Holiday.date)
            )
        )
        .scalars()
        .all()
    )
    if not feriados:
        return []

    # Un solo barrido de los bloqueos del rango y después se cruza en memoria: una consulta por
    # feriado serían veinte consultas para pintar una lista de veinte líneas.
    bloqueos = (
        (
            await sesion.execute(
                select(StaffOccupancy).where(
                    StaffOccupancy.business_id == identidad.negocio_id,
                    StaffOccupancy.kind == "bloqueo",
                    StaffOccupancy.status == "activo",
                    StaffOccupancy.starts_at
                    < datetime.combine(hasta + timedelta(days=1), time(0, 0), tzinfo=UTC),
                    StaffOccupancy.ends_at > datetime.combine(desde, time(0, 0), tzinfo=UTC),
                )
            )
        )
        .scalars()
        .all()
    )
    zona = negocio.timezone if negocio else "America/Panama"

    return [
        FeriadoSugerido(
            fecha=feriado.date,
            nombre=feriado.name,
            ya_cerrado=any(_cubre_el_dia(b, feriado.date, zona) for b in bloqueos),
        )
        for feriado in feriados
    ]


def _cubre_el_dia(bloqueo: StaffOccupancy, dia: date, zona: str) -> bool:
    """Si el bloqueo tapa el día **en hora local del negocio**, que es el día que ve el dueño.

    Comparar en UTC daría respuestas raras a los dos lados de la medianoche: en Panamá son
    cinco horas de diferencia, así que un cierre «del 3 de noviembre» empieza el 3 a las 05:00
    UTC y un `date()` sobre el instante diría que empieza el 3 —bien— pero un cierre que
    termina a medianoche local diría que termina el 4.
    """
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(zona)
    inicio_local = datetime.combine(dia, time(0, 0), tzinfo=tz)
    return bloqueo.starts_at <= inicio_local and bloqueo.ends_at >= inicio_local + timedelta(days=1)


def _es_solape(error: IntegrityError) -> bool:
    codigo = getattr(getattr(error, "orig", None), "sqlstate", None)
    return codigo == EXCLUSION_VIOLADA or EXCLUSION_VIOLADA in str(error)


async def _ajustes_del_negocio(sesion: AsyncSession, negocio_id: uuid.UUID) -> BusinessSettings:
    """La fila de ajustes, creándola si el negocio es anterior a que existiera."""
    fila = await sesion.get(BusinessSettings, negocio_id)
    if fila is None:
        fila = BusinessSettings(business_id=negocio_id)
        sesion.add(fila)
        await sesion.flush()
    return fila


async def _equipo_objetivo(
    sesion: AsyncSession, negocio_id: uuid.UUID, profesional_id: uuid.UUID | None
) -> list[StaffProfile]:
    consulta = select(StaffProfile).where(
        StaffProfile.business_id == negocio_id,
        StaffProfile.active.is_(True),
        StaffProfile.deleted_at.is_(None),
    )
    if profesional_id is not None:
        consulta = consulta.where(StaffProfile.id == profesional_id)

    equipo = list((await sesion.execute(consulta)).scalars().all())
    if not equipo:
        raise NoExiste("No hay a quién bloquear: ese profesional no existe o está inactivo.")
    return equipo


def _pintar_ajustes(fila: BusinessSettings) -> AjustesDeAgenda:
    return AjustesDeAgenda(
        granularidad_minutos=fila.slot_granularity_min,
        antelacion_minima_minutos=fila.min_lead_time_min,
        antelacion_maxima_dias=fila.max_lead_time_days,
        auto_confirmar=fila.auto_confirm,
        ventana_cancelacion_horas=fila.client_cancel_window_hours,
        ventana_resena_dias=fila.review_window_days,
        bloquear_tras_ausencias=fila.no_show_block_threshold,
        permitir_cualquier_profesional=fila.allow_any_staff,
        resumen_diario=fila.daily_digest_enabled,
    )
