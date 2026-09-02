"""Catálogo de servicios (§6 del modelo de datos).

`service_categories` es **global y sin aislamiento** a propósito: si cada negocio inventara su
categoría, el filtro «uñas» del marketplace devolvería la mitad de los salones de uñas y no
habría sobre qué ordenar (SRV-4, MKT-3). El negocio elige de la lista; M2G la administra.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CHAR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenda.modelos.base import Base, IdMixin, TenantMixin
from agenda.modelos.comunes import MarcasDeTiempoMixin


class ServiceCategory(IdMixin, Base):
    """La taxonomía de M2G, jerárquica y administrable desde el back-office."""

    __tablename__ = "service_categories"

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_categories.id", ondelete="RESTRICT")
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    icon_key: Mapped[str | None] = mapped_column(Text)
    # Para las páginas categoría × zona que indexa Google (MKT-7).
    seo_title: Mapped[str | None] = mapped_column(Text)
    seo_description: Mapped[str | None] = mapped_column(Text)

    # El único por (padre, slug) se crea en la migración con `coalesce(parent_id, …)`, porque
    # en SQL `NULL` no es igual a `NULL` y dos categorías raíz con el mismo slug pasarían.
    __table_args__ = (Index("ix_service_categories_parent_id", "parent_id"),)


class Service(IdMixin, TenantMixin, MarcasDeTiempoMixin, Base):
    """Lo que vende el negocio, con su duración, su precio y sus buffers.

    Los buffers viven aquí y **no** en la reserva… salvo que la reserva se queda con una copia
    (`staff_occupancy`, `booking_items`). Esa duplicación es intencionada y es consecuencia
    declarada de ADR-0004: cambiar el buffer de un servicio hoy **no reescribe** las citas ya
    creadas, porque reescribirlas podría volver inválidas citas confirmadas, y esa llamada la
    recibe el salón, no nosotros.
    """

    __tablename__ = "services"

    service_category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_categories.id", ondelete="RESTRICT"), nullable=False
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)  # «Corte + barba»
    description: Mapped[str | None] = mapped_column(Text)
    duration_min: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    price_kind: Mapped[str] = mapped_column(Text, nullable=False)  # fijo | desde | consultar
    price_minor: Mapped[int | None] = mapped_column(BigInteger)  # 1800 = $18,00
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'USD'"))
    buffer_before_min: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    buffer_after_min: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    # Hueco PAY-5: hoy siempre NULL.
    deposit_amount_minor: Mapped[int | None] = mapped_column(BigInteger)
    photo_key: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("duration_min > 0", name="ck_services_duracion_positiva"),
        CheckConstraint(
            "buffer_before_min >= 0 AND buffer_after_min >= 0",
            name="ck_services_buffers_no_negativos",
        ),
        CheckConstraint(
            "price_kind IN ('fijo','desde','consultar')", name="ck_services_price_kind_valido"
        ),
        # Evita el precio fantasma: «desde $120» tiene precio mínimo; «a consultar» no tiene
        # ninguno y la interfaz lo dice, en vez de pintar «$0.00».
        CheckConstraint(
            "price_kind = 'consultar' OR price_minor IS NOT NULL",
            name="ck_services_precio_coherente",
        ),
        Index("ix_services_business_id_active", "business_id", "active"),
        Index("ix_services_service_category_id", "service_category_id"),
    )


class ServiceVariant(IdMixin, TenantMixin, Base):
    """Variantes con duración y precio propios (SRV-2): «Cabello largo».

    Lista simple en v1. Las opciones combinables de v2 entran como tabla nueva sin tocar esta,
    porque la reserva no apunta al servicio «más unos extras»: apunta a una variante concreta
    o a ninguna, y eso ya está resuelto en `booking_items`.
    """

    __tablename__ = "service_variants"

    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    duration_min: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    price_kind: Mapped[str] = mapped_column(Text, nullable=False)
    price_minor: Mapped[int | None] = mapped_column(BigInteger)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        CheckConstraint("duration_min > 0", name="ck_service_variants_duracion_positiva"),
        CheckConstraint(
            "price_kind IN ('fijo','desde','consultar')",
            name="ck_service_variants_price_kind_valido",
        ),
        CheckConstraint(
            "price_kind = 'consultar' OR price_minor IS NOT NULL",
            name="ck_service_variants_precio_coherente",
        ),
        UniqueConstraint("service_id", "name", name="uq_service_variants_service_id_name"),
    )
