"""Entrada y salida del equipo (punto 6 del encargo).

Dos condiciones venían con el encargo y las dos están escritas en la base, no solo en la
pantalla: el fichaje es **opcional** y el dueño lo enciende **persona a persona**.

* El interruptor es `staff_profiles.clock_in_enabled` y nace **apagado**. Un fichaje que
  aparece sin que nadie lo pida no se lee como una función: se lee como vigilancia.
* Mientras está apagado, la política de escritura de `staff_clock_events` **rechaza la fila**
  (migración 0010). Aquí se comprueba además, y no por redundancia decorativa: sin la
  comprobación el usuario vería un `403` genérico de PostgreSQL en vez de «el dueño no te ha
  activado el fichaje».

Y una tercera que no venía en el encargo y hace falta igual: **esto es append-only**. El rol de
la aplicación tiene `SELECT` e `INSERT` y no tiene `UPDATE` ni `DELETE`. Un registro horario que
se puede reescribir no prueba nada, ni a favor del salón ni a favor de quien trabaja allí.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.errores import DatoInvalido, NoAutorizado, NoExiste
from agenda.modelos.dueno import StaffClockEvent
from agenda.modelos.equipo import StaffProfile

ENTRADA = "entrada"
SALIDA = "salida"


@dataclass(frozen=True)
class Marca:
    """Un fichaje ya guardado."""

    id: uuid.UUID
    profesional_id: uuid.UUID
    clase: str
    instante: datetime
    origen: str
    nota: str | None


@dataclass(frozen=True)
class Jornada:
    """Lo que fichó una persona en el rango pedido."""

    profesional_id: uuid.UUID
    nombre: str
    fichaje_activo: bool
    #: `entrada` = está dentro ahora mismo; `salida` o `None` = no.
    ultimo: str | None
    minutos_trabajados: int
    #: Verdadero cuando la última marca es una entrada sin su salida. La pantalla lo necesita
    #: para no pintar un total que va a cambiar dentro de un rato.
    jornada_abierta: bool
    marcas: list[Marca] = field(default_factory=list)


def minutos_trabajados(marcas: list[tuple[str, datetime]]) -> int:
    """Minutos entre pares entrada/salida. **Una entrada sin salida no se inventa.**

    Función pura y sin base de datos a propósito: es aritmética con casos raros de verdad —
    dos entradas seguidas, una salida huérfana, una jornada abierta— y cada uno se prueba
    aparte. Los casos raros no son teóricos: alguien ficha, se le cierra la aplicación y vuelve
    a fichar, y contar desde la primera entrada le regalaría horas al parte.

    * Dos entradas seguidas → manda **la última**.
    * Una salida sin entrada → se ignora; no se puede saber desde cuándo.
    * La jornada abierta al final del rango → **no suma**. Sumar «hasta ahora» daría un total
      que crece solo mientras la pantalla está abierta.
    """
    total = 0
    abierta: datetime | None = None
    for clase, instante in sorted(marcas, key=lambda m: m[1]):
        if clase == ENTRADA:
            abierta = instante
        elif abierta is not None:
            total += int((instante - abierta).total_seconds() // 60)
            abierta = None
    return total


async def encender(
    sesion: AsyncSession, *, negocio_id: uuid.UUID, profesional_id: uuid.UUID, activo: bool
) -> StaffProfile:
    """El interruptor del dueño, **persona a persona**.

    Apagarlo **no borra** lo ya fichado: el parte de las semanas anteriores sigue siendo cierto,
    y borrarlo al apagar convertiría un cambio de política en una destrucción de registros.
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

    perfil.clock_in_enabled = activo
    await sesion.flush()
    return perfil


async def fichar(
    sesion: AsyncSession,
    *,
    negocio_id: uuid.UUID,
    profesional_id: uuid.UUID,
    clase: str,
    actor_user_id: uuid.UUID | None = None,
    origen: str = "profesional",
    nota: str | None = None,
    instante: datetime | None = None,
) -> Marca:
    """Apunta una entrada o una salida.

    No deja fichar dos entradas seguidas ni una salida sin entrada: no es purismo, es que un
    parte con marcas descabaladas no se puede leer, y el momento de darse cuenta es al pulsar el
    botón —cuando la persona está delante y lo puede arreglar— y no a fin de mes.
    """
    if clase not in (ENTRADA, SALIDA):
        raise DatoInvalido("Un fichaje es una entrada o una salida.")

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
    if not perfil.clock_in_enabled:
        # La base lo rechazaría igual (política de la migración 0010). Esto está para que el
        # mensaje se entienda: el `403` de PostgreSQL no explica de quién depende encenderlo.
        raise NoAutorizado(
            "El fichaje no está activado para esta persona. Lo activa quien administra el salón."
        )

    ultima = await _ultima_marca(sesion, negocio_id=negocio_id, profesional_id=profesional_id)
    if clase == ENTRADA and ultima is not None and ultima.kind == ENTRADA:
        raise DatoInvalido("Ya hay una entrada sin cerrar. Ficha la salida primero.")
    if clase == SALIDA and (ultima is None or ultima.kind == SALIDA):
        raise DatoInvalido("No hay ninguna entrada abierta que cerrar.")

    fila = StaffClockEvent(
        business_id=negocio_id,
        staff_id=profesional_id,
        kind=clase,
        occurred_at=instante or datetime.now(UTC),
        source=origen,
        recorded_by_user_id=actor_user_id,
        note=nota,
    )
    sesion.add(fila)
    await sesion.flush()
    return _pintar(fila)


async def _ultima_marca(
    sesion: AsyncSession, *, negocio_id: uuid.UUID, profesional_id: uuid.UUID
) -> StaffClockEvent | None:
    return (
        await sesion.execute(
            select(StaffClockEvent)
            .where(
                StaffClockEvent.business_id == negocio_id,
                StaffClockEvent.staff_id == profesional_id,
            )
            .order_by(StaffClockEvent.occurred_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def partes(
    sesion: AsyncSession,
    *,
    negocio_id: uuid.UUID,
    desde: datetime,
    hasta: datetime,
    profesional_id: uuid.UUID | None = None,
) -> list[Jornada]:
    """El parte del rango, por persona.

    Sale **todo el equipo con el fichaje encendido**, aunque no haya fichado nada: una fila a
    cero es un dato —hoy no vino— y esconderla convertiría la ausencia en un hueco que hay que
    interpretar.
    """
    if hasta <= desde:
        raise DatoInvalido("El periodo tiene que terminar después de empezar.")

    consulta = select(StaffProfile).where(
        StaffProfile.business_id == negocio_id,
        StaffProfile.deleted_at.is_(None),
        StaffProfile.clock_in_enabled.is_(True),
    )
    if profesional_id is not None:
        consulta = consulta.where(StaffProfile.id == profesional_id)
    equipo = list((await sesion.execute(consulta.order_by(StaffProfile.position))).scalars().all())
    if not equipo:
        return []

    ids = [p.id for p in equipo]
    eventos = (
        (
            await sesion.execute(
                select(StaffClockEvent)
                .where(
                    StaffClockEvent.business_id == negocio_id,
                    StaffClockEvent.staff_id.in_(ids),
                    StaffClockEvent.occurred_at >= desde,
                    StaffClockEvent.occurred_at < hasta,
                )
                .order_by(StaffClockEvent.occurred_at)
            )
        )
        .scalars()
        .all()
    )

    por_persona: dict[uuid.UUID, list[StaffClockEvent]] = {p.id: [] for p in equipo}
    for evento in eventos:
        por_persona[evento.staff_id].append(evento)

    partes_del_equipo: list[Jornada] = []
    for perfil in equipo:
        suyos = por_persona[perfil.id]
        ultimo = suyos[-1].kind if suyos else None
        partes_del_equipo.append(
            Jornada(
                profesional_id=perfil.id,
                nombre=perfil.display_name,
                fichaje_activo=perfil.clock_in_enabled,
                ultimo=ultimo,
                minutos_trabajados=minutos_trabajados([(e.kind, e.occurred_at) for e in suyos]),
                jornada_abierta=ultimo == ENTRADA,
                marcas=[_pintar(e) for e in suyos],
            )
        )
    return partes_del_equipo


def _pintar(fila: StaffClockEvent) -> Marca:
    return Marca(
        id=fila.id,
        profesional_id=fila.staff_id,
        clase=fila.kind,
        instante=fila.occurred_at,
        origen=fila.source,
        nota=fila.note,
    )
