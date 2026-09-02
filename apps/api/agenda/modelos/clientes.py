"""Clientes (§7 del modelo de datos).

La separación de este dominio es la más fácil de equivocar de todo el esquema: **un cliente
pertenece a la plataforma; su ficha pertenece al negocio.** Si `client_profiles` llevara
`business_id`, un cliente que reserva en tres salones serían tres personas y el historial de
RSV-7 no existiría.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenda.modelos.base import Base, IdMixin, TenantMixin
from agenda.modelos.comunes import CreadoEnMixin, MarcasDeTiempoMixin


class ClientProfile(MarcasDeTiempoMixin, Base):
    """El cliente como usuario de la plataforma. Deliberadamente flaco.

    Todo lo que sea «datos de salud» o preferencias clínicas es RSV-6 y **v2 con
    consentimiento explícito**: son datos sensibles bajo la Ley 81 y no se recogen «ya que
    estamos».
    """

    __tablename__ = "client_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    birthdate: Mapped[date | None] = mapped_column(Date)
    # Para arrancar la búsqueda sin pedir GPS la primera vez.
    default_zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="SET NULL")
    )
    marketing_opt_in: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )


class BusinessClient(IdMixin, TenantMixin, MarcasDeTiempoMixin, Base):
    """La ficha del cliente **dentro de un negocio**, con sus notas y sus contadores."""

    __tablename__ = "business_clients"

    # NULL = «cliente rápido» del walk-in (AGD-2): el señor que entra sin cita y al que el
    # barbero le crea la reserva de viva voz. Ojo con la asimetría, que es intencionada: por
    # el marketplace **no se reserva sin teléfono verificado** (D9); el cliente rápido solo
    # existe en reservas creadas por el propio negocio.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    phone_e164: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)  # notas del negocio sobre el cliente (RSV-6)
    # Desnormalizados a propósito: la agenda los pinta en cada fila, y contar reservas por
    # cliente en cada carga de la pantalla del día es exactamente la consulta que convierte
    # 3G en inutilizable. Los mantiene el mismo disparador que cierra una reserva.
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    no_show_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    cancel_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    blocked_reason: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'marketplace'")
    )
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_booking_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "source IN ('marketplace','manual','importado')",
            name="ck_business_clients_source_valido",
        ),
        Index(
            "uq_business_clients_business_id_user_id",
            "business_id",
            "user_id",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
        ),
        # Así encuentra el dueño a alguien: escribiendo cuatro dígitos del teléfono mientras
        # atiende. Sin este índice el buscador de la agenda hace recorrido secuencial.
        Index("ix_business_clients_business_id_phone_e164", "business_id", "phone_e164"),
    )


class Favorite(CreadoEnMixin, Base):
    """Los negocios que un cliente guardó (MKT-5).

    Sin aislamiento por negocio **aunque contenga `business_id`**: la fila es del usuario, no
    del salón, y el salón no tiene por qué ver quién lo guardó. Es la excepción que confirma
    la regla, y por eso la prueba de catálogo lleva una lista corta y justificada de
    exclusiones en vez de mirar solo el nombre de la columna.
    """

    __tablename__ = "favorites"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), primary_key=True
    )

    __table_args__ = (Index("ix_favorites_business_id", "business_id"),)
