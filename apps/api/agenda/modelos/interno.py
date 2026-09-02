"""Back-office y plataforma (§13 del modelo de datos).

Nada de aquí lleva aislamiento por negocio, y en el caso de `audit_logs` el motivo merece
decirse en voz alta: **es el registro de lo que hace el equipo interno, y una de sus funciones
es registrar lo que el equipo interno hace.** Si el propio equipo pudiera filtrarlo o borrarlo,
no sería auditoría.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenda.modelos.base import Base, IdMixin
from agenda.modelos.comunes import CreadoEnMixin


class AuditLog(IdMixin, CreadoEnMixin, Base):
    """Rastro append-only de acciones internas, **incluida la impersonación** (ADM-2).

    La impersonación deja aquí su rastro, con caducidad corta en el token y aviso al negocio;
    sin las tres cosas no se construye (ADR-0006).
    """

    __tablename__ = "audit_logs"

    actor_kind: Mapped[str] = mapped_column(Text, nullable=False)
    actor_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(Text)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    impersonated_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    ip_hash: Mapped[bytes | None] = mapped_column(LargeBinary)
    user_agent: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "actor_kind IN ('admin','sistema','negocio','cliente')",
            name="ck_audit_logs_actor_kind_valido",
        ),
        Index("ix_audit_logs_business_id_created_at", "business_id", text("created_at DESC")),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )


class FeatureFlag(Base):
    """Interruptores de producto sin desplegar (ADM-4)."""

    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)
    enabled_global: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    # Despliegue progresivo: porcentaje, lista de negocios, lo que haga falta. Es JSON porque
    # la forma del despliegue cambia con cada feature y no merece una migración cada vez.
    rollout: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    updated_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class FeatureFlagOverride(Base):
    """El interruptor forzado para un negocio concreto."""

    __tablename__ = "feature_flag_overrides"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[str] = mapped_column(
        Text, ForeignKey("feature_flags.key", ondelete="CASCADE"), primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (Index("ix_feature_flag_overrides_key", "key"),)


class ModerationQueue(IdMixin, CreadoEnMixin, Base):
    """Lo que espera decisión del equipo de moderación (ADM-3)."""

    __tablename__ = "moderation_queue"

    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE")
    )
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pendiente'"))
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    assigned_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pendiente','en_revision','resuelta','descartada')",
            name="ck_moderation_queue_status_valido",
        ),
        UniqueConstraint(
            "entity_type", "entity_id", name="uq_moderation_queue_entity_type_entity_id"
        ),
        # Parcial: la bandeja del moderador solo mira lo que sigue abierto.
        Index(
            "ix_moderation_queue_abiertas",
            text("priority DESC"),
            "created_at",
            postgresql_where=text("status IN ('pendiente','en_revision')"),
        ),
    )


class IdempotencyKey(IdMixin, CreadoEnMixin, Base):
    """La respuesta ya dada a una escritura repetida (ADR-0012).

    Se guarda la respuesta entera y no solo «ya lo hice»: el cliente que reintenta necesita
    **la misma respuesta**, no un 409 que le obligue a inventarse qué pasó.
    """

    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(Text, nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE")
    )
    # Hash del cuerpo: la misma clave con un cuerpo distinto **no** es un reintento, es un
    # error del cliente, y responderle con la respuesta anterior sería mentirle.
    request_hash: Mapped[bytes | None] = mapped_column(LargeBinary)
    response_status: Mapped[int | None] = mapped_column(SmallInteger)
    response_body: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("key", "endpoint", name="uq_idempotency_keys_key_endpoint"),
        Index("ix_idempotency_keys_expires_at", "expires_at"),
    )


class PlatformSetting(Base):
    """Configuración de plataforma: símbolo de moneda (D12) y nombre comercial (D1).

    Dos columnas, y evitan exactamente lo que el encargo prohíbe: meter el nombre comercial a
    fuego en algún sitio del que luego hay que sacarlo a mano.
    """

    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
