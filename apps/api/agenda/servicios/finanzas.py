"""El dinero que hace el salón, y quién lo hizo (punto 6 del encargo).

Tres reglas gobiernan todo este módulo, y las tres son de las que se notan meses después:

1. **Solo cuentan las citas `completada`.** Una cita confirmada es una promesa, no un ingreso; y
   una cancelada o un no-show no son ni eso. Contar lo confirmado dejaría un panel de finanzas
   que baja solo los lunes por la mañana.

2. **El importe es el que se guardó en la cita**, no el precio de hoy del servicio. `bookings`
   y `booking_items` copian el catálogo al reservar precisamente para esto (ADR-0012): subirle
   el precio al balayage no puede reescribir lo que se facturó en marzo.

3. **Se agrupa en la hora local del negocio.** Panamá está a cinco horas de UTC, así que la
   caja del sábado agrupada en UTC se lleva las cinco últimas horas al domingo. El único sitio
   del sistema donde se convierte una regla horaria es el motor (ADR-0003); aquí no se
   convierte nada: se le pide a PostgreSQL que agrupe `AT TIME ZONE` la zona del negocio, que
   es la misma verdad y sin aritmética nuestra por medio.

**No hay tabla de agregados.** Un total guardado se desincroniza el primer día que alguien
cancela una cita a mano en la base, y un panel de finanzas que miente sin fallar es peor que no
tener panel. Cuando el volumen lo pida, esto se precalcula en un trabajo periódico — y entonces
será una decisión, con su ADR, no un descuido de hoy.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from sqlalchemy import func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.errores import DatoInvalido
from agenda.modelos.catalogo import Service, ServiceCategory
from agenda.modelos.equipo import StaffProfile
from agenda.modelos.reservas import Booking, BookingItem

#: Cómo se parte el eje del tiempo. Son los tres del encargo y ninguno más: un selector con
#: siete opciones en un móvil es un selector que nadie toca.
Agrupacion = Literal["dia", "semana", "mes"]

#: Por qué se ordena el mejor del mes. Los dos del encargo: quién facturó más y quién hizo más
#: servicios. **No hay un tercero implícito**: «el mejor» sin decir según qué es una opinión.
Criterio = Literal["importe", "servicios"]

_TRUNCADO = {"dia": "day", "semana": "week", "mes": "month"}


@dataclass(frozen=True)
class Periodo:
    """Un día, una semana o un mes, con lo que entró dentro."""

    #: Instante en que empieza el periodo, **en UTC pero cuadrado a la medianoche local**.
    inicio: datetime
    citas: int
    importe_centavos: int


@dataclass(frozen=True)
class Finanzas:
    """El agregado completo: el total, el desglose y lo que el total no puede decir."""

    desde: datetime
    hasta: datetime
    zona: str
    moneda: str
    agrupacion: Agrupacion
    citas: int
    importe_centavos: int
    #: Cuántas de esas citas llevaban algún servicio «a consultar», que no tiene precio y por
    #: tanto suma cero. Sin este número el total parece completo y no lo es: el salón que cobra
    #: los balayage a ojo vería una caja más baja que la real y no sabría por qué.
    citas_sin_precio: int
    periodos: list[Periodo] = field(default_factory=list)

    @property
    def ticket_medio_centavos(self) -> int:
        """Redondeado a centavos. Con cero citas es cero, no una división entre cero."""
        return round(self.importe_centavos / self.citas) if self.citas else 0


@dataclass(frozen=True)
class FilaDelRanking:
    """Una persona del equipo en el «mejor del mes»."""

    profesional_id: uuid.UUID
    nombre: str
    servicios: int
    importe_centavos: int


async def resumen(
    sesion: AsyncSession,
    *,
    negocio_id: uuid.UUID,
    zona: str,
    moneda: str,
    desde: datetime,
    hasta: datetime,
    agrupacion: Agrupacion = "dia",
    profesional_id: uuid.UUID | None = None,
) -> Finanzas:
    """Lo facturado en el rango, partido por día, semana o mes.

    El filtro por negocio se escribe **además** de la política de seguridad por fila (ADR-0002):
    la política es la red, no la excusa para consultar sin `WHERE` — y sin el filtro explícito
    el planificador deja de usar `ix_bookings_business_id_status_starts_at`.
    """
    if hasta <= desde:
        raise DatoInvalido("El periodo tiene que terminar después de empezar.")

    periodo_local = func.date_trunc(_TRUNCADO[agrupacion], func.timezone(zona, Booking.starts_at))
    # Se vuelve a instante para que el cliente reciba siempre ISO-8601 con desplazamiento
    # explícito y no una fecha suelta que cada uno interprete a su manera (ADR-0012).
    inicio_utc = func.timezone(zona, periodo_local).label("inicio")

    consulta = (
        select(
            inicio_utc,
            func.count().label("citas"),
            func.coalesce(func.sum(Booking.total_amount_minor), 0).label("importe"),
            func.count()
            .filter(
                # `EXISTS` sobre los ítems y no una comparación con cero: una cita de un
                # servicio gratuito («retoque de cortesía») también suma cero y no es lo mismo
                # que una cita cuyo precio nadie sabe todavía.
                select(literal_column("1"))
                .where(
                    BookingItem.booking_id == Booking.id,
                    BookingItem.price_kind_snapshot == "consultar",
                )
                .exists()
            )
            .label("sin_precio"),
        )
        .where(
            Booking.business_id == negocio_id,
            Booking.status == "completada",
            Booking.starts_at >= desde,
            Booking.starts_at < hasta,
        )
        .group_by(inicio_utc)
        .order_by(inicio_utc)
    )
    if profesional_id is not None:
        consulta = consulta.where(Booking.staff_id == profesional_id)

    filas = (await sesion.execute(consulta)).all()

    return Finanzas(
        desde=desde,
        hasta=hasta,
        zona=zona,
        moneda=moneda,
        agrupacion=agrupacion,
        citas=sum(fila.citas for fila in filas),
        importe_centavos=sum(int(fila.importe) for fila in filas),
        citas_sin_precio=sum(fila.sin_precio for fila in filas),
        periodos=[
            Periodo(inicio=fila.inicio, citas=fila.citas, importe_centavos=int(fila.importe))
            for fila in filas
        ],
    )


async def ranking_del_equipo(
    sesion: AsyncSession,
    *,
    negocio_id: uuid.UUID,
    desde: datetime,
    hasta: datetime,
    criterio: Criterio = "importe",
    categoria: str | None = None,
) -> list[FilaDelRanking]:
    """El «mejor del mes»: quién facturó más o quién hizo más servicios.

    Se cuenta sobre **`booking_items`** y no sobre `bookings`, y no es un capricho: filtrar por
    categoría de servicio solo tiene sentido ítem a ítem. En una cita de «corte + tinte», el
    corte cuenta para barbería y el tinte para color; sumar la cita entera a las dos categorías
    contaría el mismo dinero dos veces, que es exactamente cómo se fabrica un ranking que nadie
    entiende. Sin filtro, la suma de los ítems es el total de la cita — los dos números salen
    de la misma copia congelada del catálogo, así que no pueden separarse.

    Sale **todo el equipo con actividad**, ordenado. Quedarse con el primero es cosa de quien
    pinta: enseñar solo al ganador y esconder que el segundo se quedó a dos servicios es
    convertir un dato en un concurso.
    """
    if hasta <= desde:
        raise DatoInvalido("El periodo tiene que terminar después de empezar.")

    consulta = (
        select(
            StaffProfile.id.label("profesional_id"),
            StaffProfile.display_name.label("nombre"),
            func.count().label("servicios"),
            func.coalesce(func.sum(BookingItem.price_minor_snapshot), 0).label("importe"),
        )
        .select_from(BookingItem)
        .join(Booking, Booking.id == BookingItem.booking_id)
        .join(StaffProfile, StaffProfile.id == Booking.staff_id)
        .where(
            BookingItem.business_id == negocio_id,
            Booking.business_id == negocio_id,
            Booking.status == "completada",
            Booking.starts_at >= desde,
            Booking.starts_at < hasta,
        )
        .group_by(StaffProfile.id, StaffProfile.display_name)
    )

    if categoria:
        consulta = consulta.where(
            BookingItem.service_id.in_(
                select(Service.id).where(
                    Service.business_id == negocio_id,
                    Service.service_category_id.in_(
                        select(ServiceCategory.id).where(ServiceCategory.slug == categoria)
                    ),
                )
            )
        )

    # El desempate es siempre el otro criterio, y después el nombre: sin él, dos personas
    # empatadas se turnan en el primer puesto cada vez que se recarga la pantalla.
    if criterio == "servicios":
        orden = (
            func.count().desc(),
            func.coalesce(func.sum(BookingItem.price_minor_snapshot), 0).desc(),
        )
    else:
        orden = (
            func.coalesce(func.sum(BookingItem.price_minor_snapshot), 0).desc(),
            func.count().desc(),
        )
    consulta = consulta.order_by(*orden, StaffProfile.display_name)

    return [
        FilaDelRanking(
            profesional_id=fila.profesional_id,
            nombre=fila.nombre,
            servicios=fila.servicios,
            importe_centavos=int(fila.importe),
        )
        for fila in (await sesion.execute(consulta)).all()
    ]
