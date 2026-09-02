"""Marketplace, geografía y ranking (§10 del modelo de datos).

Aquí conviven dos cosas que parecen la misma y no lo son (ADR-0005): **«cerca de mí»**, que es
distancia real desde un punto con índice GiST, y **«barbería en San Francisco»**, que es una
entidad con nombre, URL estable y contenido indexable.

Y una regla que este dominio tiene que respetar entera: **no hay ni un número de ranking en el
código** (ADR-0009, ADM-4). Ni el radio, ni el techo de reservas recientes, ni la duración del
impulso a los nuevos. Si aparece un `0.3` en un archivo Python, es un fallo.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CHAR, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenda.modelos.base import Base, IdMixin
from agenda.modelos.comunes import CreadoEnMixin


class Zone(IdMixin, Base):
    """Taxonomía jerárquica de zonas de Panamá, administrable (MKT-6).

    Global y sin aislamiento: es catálogo compartido. Provincia → distrito → corregimiento →
    barrio, con `path` materializado.
    """

    __tablename__ = "zones"

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="RESTRICT")
    )
    level: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    # Materializado: permite pedir «toda la rama del distrito de Panamá» con un
    # `LIKE 'panama/panama/%'` en vez de una consulta recursiva en cada búsqueda. Se recalcula
    # al mover una zona, que pasa dos veces al año.
    path: Mapped[str] = mapped_column(Text, nullable=False)
    country_code: Mapped[str] = mapped_column(CHAR(2), nullable=False, server_default=text("'PA'"))
    centroid: Mapped[WKBElement | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    # Para **sugerir** la zona de un punto; la última palabra la tiene el dueño.
    boundary: Mapped[WKBElement | None] = mapped_column(
        Geography(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False)
    )
    # Cacheado para no generar páginas categoría × zona vacías: miles de páginas sin contenido
    # son baja calidad y Google penaliza el dominio entero, no solo esas páginas.
    businesses_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        CheckConstraint(
            "level IN ('provincia','distrito','corregimiento','barrio')",
            name="ck_zones_level_valido",
        ),
        # El único por (padre, slug) y el índice de `path` con `text_pattern_ops` se crean en
        # la migración: los dos necesitan una expresión que SQLAlchemy no genera igual.
        Index("ix_zones_parent_id", "parent_id"),
    )


class RankingWeights(IdMixin, CreadoEnMixin, Base):
    """Los pesos y las ventanas del ranking, versionados y con vigencia (ADR-0009).

    Cambiar los pesos es **insertar una fila y cerrar la anterior**, no un `UPDATE`, porque
    hay que poder responder «¿con qué pesos salía este negocio el noveno la semana pasada?».
    """

    __tablename__ = "ranking_weights"

    version: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    w_distancia: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    w_rating: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    w_reservas_recientes: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    w_tasa_completado: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    w_completitud: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    w_actividad: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    w_boost_nuevo: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    radius_km: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    decay_km: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    recent_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # Techo: un negocio grande no domina toda la portada por volumen.
    recent_cap: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    boost_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    bayes_m: Mapped[Decimal] = mapped_column(Numeric, nullable=False)  # media global sembrada
    bayes_c: Mapped[int] = mapped_column(Integer, nullable=False)  # reviews de confianza
    sponsored_per_page: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("2")
    )
    page_size: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("10"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )

    __table_args__ = (
        UniqueConstraint("version", name="uq_ranking_weights_version"),
        # Hay **exactamente una** versión vigente. Se indexa la expresión
        # `(effective_to IS NULL)` y no la columna: en un único, dos `NULL` se consideran
        # distintos y dos filas vigentes pasarían sin que nadie se enterara.
        Index(
            "uq_ranking_weights_vigente",
            text("(effective_to IS NULL)"),
            unique=True,
            postgresql_where=text("effective_to IS NULL"),
        ),
    )


class BusinessRankingSignals(Base):
    """Las señales caras del ranking, ya calculadas por negocio.

    La distancia es lo único que depende de quién busca, así que todo lo demás se precalcula y
    la consulta del marketplace solo combina `base_score` con la distancia. El precio es un
    desfase de minutos entre la realidad y el orden, y hay que decirlo en voz alta: **una
    reserva de hace un minuto no reordena la portada.**
    """

    __tablename__ = "business_ranking_signals"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), primary_key=True
    )
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    weights_version: Mapped[int] = mapped_column(Integer, nullable=False)
    bookings_recent: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    completion_rate: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    completeness: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))  # ONB-7
    activity_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    rating_bayesian: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    new_boost: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    base_score: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    # El desglose por señal es lo que permite responder a la primera llamada de un dueño
    # enfadado: «¿por qué salgo el noveno?». Un ranking que nadie puede explicar es un ranking
    # que nadie puede ajustar.
    signals: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (Index("ix_business_ranking_signals_base_score", text("base_score DESC")),)


class ListingImpressionDaily(IdMixin, Base):
    """Impresiones agregadas por día, superficie y ubicación (MKT-8).

    Se guardan **agregadas y no evento a evento** (ADR-0009): 5.000 negocios en portada
    generan un volumen de filas que no aporta nada, y lo que hace falta es la serie. Se
    escriben con `INSERT … ON CONFLICT DO UPDATE SET count = count + 1`, que es atómico y no
    necesita leer antes.

    La combinación (negocio, día, superficie, emplazamiento, zona, categoría) es la clave de
    conflicto, pero **no** puede ser la clave primaria: `zone_id` y `service_category_id` son
    nulos cuando la impresión no viene de una página de zona ni de categoría, y una clave
    primaria no admite nulos. Se resuelve con un único `NULLS NOT DISTINCT` —PostgreSQL 15 en
    adelante—, que es lo que hace que dos impresiones «sin zona» del mismo día sumen en la
    misma fila en vez de crear una fila nueva cada vez.
    """

    __tablename__ = "listing_impressions_daily"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    day: Mapped[date] = mapped_column(Date, nullable=False)
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    placement: Mapped[str] = mapped_column(Text, nullable=False)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="SET NULL")
    )
    service_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_categories.id", ondelete="SET NULL")
    )
    count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    __table_args__ = (
        CheckConstraint(
            "placement IN ('organico','patrocinado')",
            name="ck_listing_impressions_daily_placement_valido",
        ),
        Index("ix_listing_impressions_daily_business_id_day", "business_id", "day"),
    )


class ListingClickDaily(IdMixin, Base):
    """Clics agregados por día y tipo.

    El clic de tipo `whatsapp` es el que registra el salto en servidor del click-to-chat: el
    número **nunca** viaja al cliente (ADR-0007, garantía nº 3 de la constitución).

    Misma forma de clave que `listing_impressions_daily` y por el mismo motivo.
    """

    __tablename__ = "listing_clicks_daily"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    day: Mapped[date] = mapped_column(Date, nullable=False)
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="SET NULL")
    )
    service_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_categories.id", ondelete="SET NULL")
    )
    count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    __table_args__ = (
        CheckConstraint(
            "kind IN ('perfil','whatsapp','mapa','reservar')",
            name="ck_listing_clicks_daily_kind_valido",
        ),
        Index("ix_listing_clicks_daily_business_id_day", "business_id", "day"),
    )


class GeocodingCache(IdMixin, CreadoEnMixin, Base):
    """Caché de dirección a punto.

    Se cachea **por texto normalizado** porque el geocoding es de pago y se repite muchísimo:
    media ciudad escribe «Vía España» de seis formas distintas.
    """

    __tablename__ = "geocoding_cache"

    normalized_query: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str | None] = mapped_column(Text)
    geo: Mapped[WKBElement | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="SET NULL")
    )
    raw: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    hits: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    # El proveedor exige por contrato una caducidad para la caché.
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("normalized_query", name="uq_geocoding_cache_normalized_query"),
    )


class Holiday(IdMixin, Base):
    """Feriados de Panamá precargados, **sugeridos y no impuestos** (AGD-6).

    El trabajo que los propone crea `time_block_rules` solo si el negocio acepta: un salón de
    barrio abre el día de la madre precisamente porque es el día de la madre.
    """

    __tablename__ = "holidays"

    country_code: Mapped[str] = mapped_column(CHAR(2), nullable=False, server_default=text("'PA'"))
    date: Mapped[_dt.date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("country_code", "date", name="uq_holidays_country_code_date"),
    )


class SlugRedirect(CreadoEnMixin, Base):
    """Slugs antiguos que siguen resolviendo, para no romper enlaces ya indexados."""

    __tablename__ = "slug_redirects"

    old_slug: Mapped[str] = mapped_column(Text, primary_key=True)
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (Index("ix_slug_redirects_business_id", "business_id"),)
