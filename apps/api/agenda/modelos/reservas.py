"""Reservas y ocupación (§8 del modelo de datos). **El núcleo del producto.**

Es la única parte del esquema donde una decisión mal tomada no se arregla con una migración:
se arregla rehaciendo el motor.

Dos cosas que el ORM **no** expresa y que viven en la migración porque solo existen en la base
de datos: las columnas generadas `blocked_from`/`blocked_to` de `staff_occupancy` —que
incluyen los buffers y las calcula PostgreSQL, no la aplicación (ADR-0004)— y la restricción
de exclusión sobre ellas, que es la garantía nº 2 de la constitución. Aquí se declaran como
columnas de solo lectura para que el resto del código las pueda leer sin sorpresas.

El vocabulario de estados **no se redefine aquí**: se importa de `agenda.dominio.reservas`, y
la cláusula `WHERE` de la restricción de exclusión usa exactamente `ESTADOS_ACTIVOS`. Si esa
lista y la restricción se separan, el motor y la base dejan de estar de acuerdo sobre qué está
ocupado, que es la peor discrepancia posible.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    FetchedValue,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CHAR, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenda.dominio.reservas import ESTADOS_ACTIVOS, EstadoReserva
from agenda.modelos.base import Base, IdMixin, TenantMixin
from agenda.modelos.comunes import CreadoEnMixin, MarcasDeTiempoMixin

#: Los seis estados del brief, tal como se serializan. Se derivan del enumerado del dominio
#: para que añadir un estado allí y olvidarlo aquí sea imposible.
ESTADOS_RESERVA: tuple[str, ...] = tuple(e.value for e in EstadoReserva)

#: Los estados que **ocupan agenda**, en el orden en que los escribe la restricción.
ESTADOS_QUE_OCUPAN: tuple[str, ...] = tuple(
    e.value for e in EstadoReserva if e in ESTADOS_ACTIVOS
)


def _lista_sql(valores: tuple[str, ...]) -> str:
    """Convierte una tupla de Python en la lista de un `IN (...)` de SQL."""
    return ", ".join(f"'{valor}'" for valor in valores)


class Booking(IdMixin, TenantMixin, MarcasDeTiempoMixin, Base):
    """La cita: quién, con quién, cuándo y en qué estado.

    Dos decisiones que no son obvias:

    **No copia el nombre ni el teléfono del cliente.** Apunta a `business_clients` y lee de
    ahí. Parecería que congelar el nombre sería más robusto —así se hace con el precio—, pero
    es justo lo contrario: si el nombre estuviera copiado en cada reserva, anonimizar a una
    persona significaría reescribir todas sus reservas en todos los salones. Con esta forma se
    anonimiza **una fila por negocio** y la contabilidad del salón sigue cuadrando.

    **`client_user_id` está desnormalizado** aunque se deduzca de `business_clients`: es para
    responder «mis reservas» sin cruzar tablas por cada negocio en el que el cliente ha
    estado, que es la pantalla de inicio de la app (RSV-7).
    """

    __tablename__ = "bookings"

    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="RESTRICT")
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="RESTRICT"), nullable=False
    )
    business_client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_clients.id", ondelete="RESTRICT"), nullable=False
    )
    client_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'pendiente'")
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # UTC
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)  # UTC
    total_duration_min: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    total_amount_minor: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'USD'"))
    source: Mapped[str] = mapped_column(Text, nullable=False)
    any_staff_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    client_note: Mapped[str | None] = mapped_column(Text)
    business_note: Mapped[str | None] = mapped_column(Text)
    # La reprogramación **no es un estado** (RSV-3): es una fila en `booking_events` y este
    # puntero. Una cita reprogramada sigue `confirmada`.
    rescheduled_from_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="SET NULL")
    )
    reschedule_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    no_show_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[str | None] = mapped_column(Text)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    # Huecos PAY-5: NULL en v1. La clave foránea a `payments` se añade con `ALTER TABLE` en la
    # migración porque `payments` también apunta a `bookings` y el ciclo hay que romperlo.
    deposit_amount_minor: Mapped[int | None] = mapped_column(BigInteger)
    deposit_payment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN ({_lista_sql(ESTADOS_RESERVA)})", name="ck_bookings_status_valido"
        ),
        CheckConstraint("ends_at > starts_at", name="ck_bookings_rango_valido"),
        CheckConstraint(
            "source IN ('cliente_web','cliente_app','negocio_manual','admin')",
            name="ck_bookings_source_valido",
        ),
        CheckConstraint(
            "cancelled_by IS NULL OR cancelled_by IN ('cliente','negocio','sistema','admin')",
            name="ck_bookings_cancelled_by_valido",
        ),
        # Cada índice responde a una consulta real del producto; un índice que nadie usa se
        # paga en cada escritura.
        Index("ix_bookings_business_id_starts_at", "business_id", "starts_at"),
        Index("ix_bookings_business_id_staff_id_starts_at", "business_id", "staff_id", "starts_at"),
        Index("ix_bookings_business_id_status_starts_at", "business_id", "status", "starts_at"),
        Index("ix_bookings_client_user_id_starts_at", "client_user_id", text("starts_at DESC")),
        Index(
            "ix_bookings_business_client_id_starts_at",
            "business_client_id",
            text("starts_at DESC"),
        ),
        # Parcial para que el barrido de recordatorios a 24 h y 2 h mire un índice pequeño y
        # no el histórico entero.
        Index(
            "ix_bookings_recordatorios",
            "starts_at",
            postgresql_where=text(f"status IN ({_lista_sql(ESTADOS_QUE_OCUPAN)})"),
        ),
    )


class BookingItem(IdMixin, TenantMixin, Base):
    """Cada servicio de la cita, con su precio y su duración **congelados**.

    Todo lo que acaba en `_snapshot` es una copia del catálogo en el momento de reservar. Es
    la diferencia entre poder responder «el balayage costaba $120 cuando ella reservó» y tener
    que explicarle al cliente que el precio cambió ayer: un catálogo mutable sin copia
    congelada reescribe el pasado en silencio.
    """

    __tablename__ = "booking_items"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 1, 2, 3… (D13)
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False
    )
    service_variant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_variants.id", ondelete="RESTRICT")
    )
    # Hueco RSV-2 v2 (servicios de la misma cita con **distintos** profesionales). Hoy
    # siempre NULL y el motor asume el profesional de la reserva.
    staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="RESTRICT")
    )
    name_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    duration_min_snapshot: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    price_kind_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    price_minor_snapshot: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    buffer_before_min_snapshot: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    buffer_after_min_snapshot: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("booking_id", "position", name="uq_booking_items_booking_id_position"),
        Index("ix_booking_items_service_id", "service_id"),
    )


class StaffOccupancy(IdMixin, TenantMixin, MarcasDeTiempoMixin, Base):
    """La **única** tabla de ocupación: reservas y bloqueos son dos tipos de fila suya.

    Si el almuerzo viviera en otra tabla, PostgreSQL no podría impedir que le encajaran una
    cita encima (ADR-0004). Y una reserva multi-servicio es **una** fila continua: tres filas
    sueltas dejarían que otra cita se colara en medio de la cadena.
    """

    __tablename__ = "staff_occupancy"

    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # reserva | bloqueo
    # Para kind='reserva' es espejo de `bookings.status` y lo mantiene un disparador; para
    # kind='bloqueo' toma activo | levantado.
    status: Mapped[str] = mapped_column(Text, nullable=False)
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE")
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("time_block_rules.id", ondelete="CASCADE")
    )
    occurrence_date: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(Text)
    # Hueco STF-4 / D17: la persona detrás del profesional, si tiene cuenta. Se rellena hoy y
    # hoy no lo usa nadie; en v2 sostiene la exclusión entre negocios sin rellenar millones
    # de filas con bloqueos largos sobre la tabla más caliente del sistema.
    staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # COPIADOS del servicio al reservar, no leídos del catálogo: cambiar el buffer de un
    # servicio no puede volver inválida una cita ya confirmada.
    buffer_before_min: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    buffer_after_min: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    # Generadas y persistidas por la base. `FetchedValue` + `server_default` es la forma de
    # decirle al ORM «esto lo escribe PostgreSQL»: si el ORM intentara insertarlas, el
    # `INSERT` fallaría con «cannot insert into generated column».
    blocked_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), FetchedValue(), server_default=FetchedValue(), nullable=False
    )
    blocked_to: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), FetchedValue(), server_default=FetchedValue(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_staff_occupancy_booking_id"),
        CheckConstraint("kind IN ('reserva','bloqueo')", name="ck_staff_occupancy_kind_valido"),
        CheckConstraint(
            "buffer_before_min >= 0", name="ck_staff_occupancy_buffer_before_no_negativo"
        ),
        CheckConstraint(
            "buffer_after_min >= 0", name="ck_staff_occupancy_buffer_after_no_negativo"
        ),
        CheckConstraint("ends_at > starts_at", name="ck_staff_occupancy_rango_valido"),
        CheckConstraint(
            "(kind = 'reserva' AND booking_id IS NOT NULL AND rule_id IS NULL)"
            " OR (kind = 'bloqueo' AND booking_id IS NULL)",
            name="ck_staff_occupancy_reserva_coherente",
        ),
        # La materialización de bloqueos recurrentes es idempotente gracias a este único:
        # ejecutar el trabajo dos veces no crea dos almuerzos.
        Index(
            "uq_staff_occupancy_regla_ocurrencia",
            "rule_id",
            "staff_id",
            "occurrence_date",
            unique=True,
            postgresql_where=text("rule_id IS NOT NULL"),
        ),
        Index("ix_staff_occupancy_agenda_staff", "business_id", "staff_id", "blocked_from"),
        Index("ix_staff_occupancy_agenda_negocio", "business_id", "blocked_from"),
    )


class BookingEvent(IdMixin, TenantMixin, CreadoEnMixin, Base):
    """El rastro **append-only** de todo lo que le pasó a la cita.

    No se actualiza ni se borra, y el rol de la API tiene `INSERT` y `SELECT` pero no `UPDATE`
    ni `DELETE`. Es lo que permite responder a soporte «¿quién canceló esta cita y cuándo?»
    (ADM-7) sin adivinar, y es donde vive la reprogramación, que no es un estado.
    """

    __tablename__ = "booking_events"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    from_status: Mapped[str | None] = mapped_column(Text)
    to_status: Mapped[str | None] = mapped_column(Text)
    actor_kind: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    actor_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    __table_args__ = (
        CheckConstraint(
            "type IN ('creada','confirmada','reprogramada','cancelada','completada','no_show',"
            "'recordatorio_encolado','review_solicitada','nota_anadida')",
            name="ck_booking_events_type_valido",
        ),
        CheckConstraint(
            "actor_kind IN ('cliente','negocio','sistema','admin')",
            name="ck_booking_events_actor_kind_valido",
        ),
        Index("ix_booking_events_booking_id_created_at", "booking_id", "created_at"),
    )
