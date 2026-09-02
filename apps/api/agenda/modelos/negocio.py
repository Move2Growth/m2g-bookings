"""El negocio: el tenant (§4 del modelo de datos).

`businesses` es la fila de la que cuelga todo lo aislado. Aquí también viven la ubicación con
su punto geográfico, el horario de apertura como regla local recurrente, los ajustes de agenda
y las taxonomías de atributos filtrables, que son **datos y no código** (NEG-2, ADM-4): añadir
«atiende cabello afro» como filtro tiene que ser una fila, no un despliegue.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CHAR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenda.modelos.base import Base, IdMixin, TenantMixin
from agenda.modelos.comunes import CreadoEnMixin, MarcasDeTiempoMixin


class Business(IdMixin, MarcasDeTiempoMixin, Base):
    """El salón, la barbería o el profesional independiente. **Es el tenant.**"""

    __tablename__ = "businesses"

    # Parte de la URL pública y de la bio de Instagram, así que **no se reutiliza**: si el
    # negocio cambia de nombre, el slug viejo se guarda en `slug_redirects` antes que romper
    # un enlace que ya circula por WhatsApp.
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    legal_name: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    # Obligatoria: el motor de disponibilidad no puede convertir una regla local en un
    # instante sin ella, y España viene después (ADR-0003).
    timezone: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'America/Panama'")
    )
    country_code: Mapped[str] = mapped_column(CHAR(2), nullable=False, server_default=text("'PA'"))
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'USD'"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'borrador'"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    suspension_reason: Mapped[str | None] = mapped_column(Text)
    # Sello «Verificado» (ONB-5, v2). Hoy siempre NULL.
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # NUNCA se serializa hacia el público: el click-to-chat se resuelve con un salto en
    # servidor que registra el clic y redirige (ADR-0007).
    whatsapp_phone_e164: Mapped[str | None] = mapped_column(Text)
    instagram_handle: Mapped[str | None] = mapped_column(Text)
    website_url: Mapped[str | None] = mapped_column(Text)
    tax_id: Mapped[str | None] = mapped_column(Text)  # RUC (PAY-4)
    tax_id_dv: Mapped[str | None] = mapped_column(Text)
    # Traza de quién creó el negocio. **No sustituye a `memberships`**: los permisos siempre
    # se resuelven contra la membresía.
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    profile_completeness: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("slug", name="uq_businesses_slug"),
        # El mínimo para publicar (D11: un servicio activo, horario, ubicación y una foto)
        # se comprueba en la aplicación y **no** aquí: es una regla de producto que va a
        # cambiar, y una restricción de base con datos vivos dentro es una migración cada vez.
        CheckConstraint(
            "status IN ('borrador','publicado','suspendido')", name="ck_businesses_status_valido"
        ),
        CheckConstraint(
            "profile_completeness BETWEEN 0 AND 100", name="ck_businesses_completitud_rango"
        ),
        Index("ix_businesses_owner_user_id", "owner_user_id"),
        # Parcial: la portada del marketplace solo mira los publicados y vivos.
        Index(
            "ix_businesses_publicados",
            "status",
            postgresql_where=text("status = 'publicado' AND deleted_at IS NULL"),
        ),
    )


class Location(IdMixin, TenantMixin, MarcasDeTiempoMixin, Base):
    """Dónde está el negocio, con su punto geográfico y su zona."""

    __tablename__ = "locations"

    label: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'Principal'"))
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    address_line: Mapped[str] = mapped_column(Text, nullable=False)
    address_details: Mapped[str | None] = mapped_column(Text)
    # Se **persiste** y es editable por el dueño: en Panamá los límites de corregimiento no
    # coinciden con lo que la gente llama su barrio, y el dueño sabe mejor dónde está su salón.
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="SET NULL")
    )
    # Guarda si la zona la eligió el sistema o una persona, para no pisar una corrección
    # manual la próxima vez que el trabajo recalcule.
    zone_source: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'automatica'")
    )
    # `geography` y no `geometry` (ADR-0005): devuelve metros y evita el error clásico de
    # ordenar por grados, que en Panamá da resultados **casi** correctos, que es lo peor.
    geo: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )
    geocode_accuracy: Mapped[str | None] = mapped_column(Text)
    # NULL = hereda de `businesses.timezone`. Hueco multi-sede: la zona acabará viviendo aquí
    # (ADR-0003), así que la columna se deja donde tocará moverla.
    timezone: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "zone_source IN ('automatica','manual')", name="ck_locations_zone_source_valido"
        ),
        # Índice único parcial: hoy hay **exactamente una sede por negocio** (NEG-5).
        # Quitar esta línea es toda la migración de estructura que necesita multi-sede.
        Index("uq_locations_una_principal", "business_id", unique=True, postgresql_where=text("is_primary")),
        Index("ix_locations_zone_id", "zone_id"),
        Index("ix_locations_geo_gist", "geo", postgresql_using="gist"),
    )


class BusinessHours(IdMixin, TenantMixin, MarcasDeTiempoMixin, Base):
    """Horario semanal de apertura, como **regla local recurrente** (ADR-0003).

    Se permiten varias filas por día para la jornada partida, que en un salón es la norma y no
    la excepción: abre de 9 a 13 y de 15 a 19. Con un solo rango habría que inventar un
    «descanso» que no es un descanso.
    """

    __tablename__ = "business_hours"

    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE")
    )
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0 = lunes … 6 = domingo
    opens_at: Mapped[time] = mapped_column(Time, nullable=False)
    # Si `closes_at < opens_at`, el tramo cruza medianoche. Se modela en una fila, no en dos.
    closes_at: Mapped[time] = mapped_column(Time, nullable=False)

    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_business_hours_weekday_rango"),
        UniqueConstraint(
            "business_id",
            "location_id",
            "weekday",
            "opens_at",
            name="uq_business_hours_business_id_location_id_weekday_opens_at",
        ),
    )


class BusinessSettings(Base):
    """Los parámetros de agenda y reserva que el dueño ajusta. 1:1 con `businesses`.

    Tabla aparte y no columnas en `businesses` porque el motor de disponibilidad los lee en
    **cada** cálculo y el dueño los toca a menudo: separarlos evita reescribir la fila del
    perfil —con su descripción y sus textos— cada vez que cambia la granularidad.
    """

    __tablename__ = "business_settings"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("businesses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    slot_granularity_min: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("15")
    )
    min_lead_time_min: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("60")
    )
    max_lead_time_days: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("60")
    )
    auto_confirm: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    client_cancel_window_hours: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("2")
    )
    review_window_days: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("14")
    )
    # NULL = no bloquear por no-shows (RSV-5).
    no_show_block_threshold: Mapped[int | None] = mapped_column(SmallInteger)
    allow_any_staff: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    daily_digest_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    # Hueco PAY-5: apagado en v1 y no se enciende sin OK explícito.
    deposit_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "slot_granularity_min > 0", name="ck_business_settings_granularidad_positiva"
        ),
    )


class BusinessMedia(IdMixin, TenantMixin, CreadoEnMixin, Base):
    """Portada y galería del perfil público, con su estado de moderación."""

    __tablename__ = "business_media"

    kind: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    alt_text: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    moderation_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'aprobada'")
    )

    __table_args__ = (
        CheckConstraint("kind IN ('portada','galeria')", name="ck_business_media_kind_valido"),
        CheckConstraint(
            "moderation_status IN ('pendiente','aprobada','rechazada')",
            name="ck_business_media_moderacion_valida",
        ),
        # Una portada y solo una; el resto es galería ordenada por `position`.
        Index(
            "uq_business_media_una_portada",
            "business_id",
            unique=True,
            postgresql_where=text("kind = 'portada'"),
        ),
    )


class BusinessCategory(Base):
    """Qué categorías **globales** ofrece el negocio. Tabla de unión pura.

    Apunta al catálogo de M2G a propósito: si cada negocio inventara su categoría, el filtro
    «uñas» del marketplace devolvería la mitad de los salones de uñas.

    No usa `TenantMixin` porque aquí `business_id` forma parte de la **clave primaria
    compuesta** y el mixin lo declara como columna normal; lleva igualmente su política de
    seguridad por fila, que es lo que el mixin señaliza.
    """

    __tablename__ = "business_categories"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="RESTRICT"), primary_key=True
    )
    service_category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("service_categories.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    __table_args__ = (Index("ix_business_categories_service_category_id", "service_category_id"),)


class BusinessAttribute(Base):
    """Qué atributos filtrables declara el negocio, desde el catálogo global (NEG-2)."""

    __tablename__ = "business_attributes"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="RESTRICT"), primary_key=True
    )
    attribute_value_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attribute_values.id", ondelete="CASCADE"),
        primary_key=True,
    )

    __table_args__ = (Index("ix_business_attributes_attribute_value_id", "attribute_value_id"),)


class Attribute(IdMixin, Base):
    """Catálogo global de grupos de atributos filtrables (NEG-2, ADM-4)."""

    __tablename__ = "attributes"

    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # Los valores del brief: tipo_cabello, tecnicas, publico, accesibilidad,
    # estacionamiento, metodos_pago, idiomas.
    group_key: Mapped[str] = mapped_column(Text, nullable=False)
    input_kind: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        UniqueConstraint("slug", name="uq_attributes_slug"),
        CheckConstraint(
            "input_kind IN ('unico','multiple','booleano')", name="ck_attributes_input_kind_valido"
        ),
    )


class AttributeValue(IdMixin, Base):
    """Los valores concretos de cada atributo. Catálogo global."""

    __tablename__ = "attribute_values"

    attribute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attributes.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        UniqueConstraint("attribute_id", "slug", name="uq_attribute_values_attribute_id_slug"),
    )
