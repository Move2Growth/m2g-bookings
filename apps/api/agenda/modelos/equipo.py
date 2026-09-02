"""El equipo del negocio (§5 del modelo de datos).

Los bloqueos **puntuales** no están aquí: son filas de `staff_occupancy` (§8), porque si
vivieran en otra tabla la base de datos no podría impedir que le encajaran una cita encima
(ADR-0004). Aquí solo vive lo **recurrente**: el horario semanal y el almuerzo de todos los
días, que un trabajo periódico materializa en ocupación.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenda.modelos.base import Base, IdMixin, TenantMixin
from agenda.modelos.comunes import MarcasDeTiempoMixin


class StaffProfile(IdMixin, TenantMixin, MarcasDeTiempoMixin, Base):
    """La ficha del profesional **dentro de un negocio**, tenga cuenta o no.

    Es por negocio y no una persona global, a propósito: la bio, la foto y los servicios de la
    misma persona son distintos en cada salón. Lo que STF-4 necesitará en v2 es que la
    **ocupación** se cruce entre negocios, y de eso se ocupa `staff_occupancy.staff_user_id`.
    """

    __tablename__ = "staff_profiles"

    # Nulable a propósito (ONB-4): el dueño da de alta a alguien en dos minutos y le manda la
    # invitación después. Exigir cuenta para existir en la agenda es pedirle al dueño que
    # pare el negocio para hacer una gestión.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    bio: Mapped[str | None] = mapped_column(Text)
    photo_key: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    visible_in_marketplace: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    # Entra en el reparto de «cualquier profesional disponible» (STF-5).
    accepts_any_staff: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    # Borrado lógico: destruir la ficha destruiría la historia de la agenda del negocio.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index(
            "uq_staff_profiles_business_id_user_id",
            "business_id",
            "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        Index("ix_staff_profiles_business_id_active", "business_id", "active"),
    )


class StaffHours(IdMixin, TenantMixin, MarcasDeTiempoMixin, Base):
    """Horario propio y descansos del profesional, como regla local recurrente.

    Que el horario del profesional sea **distinto** del horario del negocio es el caso normal,
    no la excepción, y por eso es una tabla propia y no un porcentaje del horario del negocio:
    la ayudante entra a las 11 y el dueño abre a las 8.
    """

    __tablename__ = "staff_hours"

    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE")
    )
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0 = lunes
    starts_at: Mapped[time] = mapped_column(Time, nullable=False)  # hora LOCAL
    ends_at: Mapped[time] = mapped_column(Time, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'trabajo'"))

    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_staff_hours_weekday_rango"),
        CheckConstraint("kind IN ('trabajo','descanso')", name="ck_staff_hours_kind_valido"),
        UniqueConstraint(
            "staff_id", "weekday", "kind", "starts_at", name="uq_staff_hours_staff_dia_tramo"
        ),
        Index("ix_staff_hours_business_id_staff_id", "business_id", "staff_id"),
    )


class StaffService(Base):
    """Qué servicios hace cada profesional.

    Las dos columnas de override existen hoy y valen `NULL`: el precio por profesional es v2
    (SRV-3), pero añadir dos columnas nulables a una tabla de unión es gratis, mientras que
    descubrir en v2 que la relación era un array dentro de `services` sería rehacerla.
    """

    __tablename__ = "staff_services"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("staff_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), primary_key=True
    )
    price_minor_override: Mapped[int | None] = mapped_column(BigInteger)
    duration_min_override: Mapped[int | None] = mapped_column(SmallInteger)

    __table_args__ = (
        Index("ix_staff_services_business_id", "business_id"),
        Index("ix_staff_services_service_id", "service_id"),
    )


class TimeBlockRule(IdMixin, TenantMixin, MarcasDeTiempoMixin, Base):
    """Bloqueos **recurrentes**: el almuerzo de todos los días (AGD-3).

    Un bloqueo recurrente es una regla local, no un instante (ADR-0003), pero una restricción
    de exclusión no puede mirar una regla: solo mira rangos. La solución es **materializar**:
    un trabajo periódico convierte cada regla en filas de `staff_occupancy` con
    `kind = 'bloqueo'` hasta `materialized_until`, y así el almuerzo del jueves está protegido
    por la misma restricción que una cita, y no por un `if`.

    El motor de disponibilidad **además** resta las reglas al calcular huecos, por si el
    horizonte se quedó corto. Es redundante a propósito: la redundancia barata en el sitio
    donde el fallo es «alguien reserva encima del almuerzo» está bien gastada.
    """

    __tablename__ = "time_block_rules"

    # NULL = todo el equipo del negocio.
    staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE")
    )
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    starts_at: Mapped[time] = mapped_column(Time, nullable=False)  # hora LOCAL
    ends_at: Mapped[time] = mapped_column(Time, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date)  # NULL = indefinido
    # Hasta dónde llegó la materialización. Es lo que permite que el trabajo sea reanudable
    # sin recorrer el horizonte entero cada vez.
    materialized_until: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_time_block_rules_weekday_rango"),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= valid_from",
            name="ck_time_block_rules_vigencia_coherente",
        ),
        Index("ix_time_block_rules_business_id_staff_id", "business_id", "staff_id"),
    )
