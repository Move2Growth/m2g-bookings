"""Notificaciones (§13 del modelo de datos, ADR-0007).

`notifications` **es la cola**. No hay una cola aparte en Redis con el estado de verdad: una
fila por mensaje que hay que mandar, con su clave de idempotencia derivada **del hecho y no
del momento** (`recordatorio_24h:booking:{id}`). Encolar dos veces el mismo recordatorio es un
conflicto que no inserta, no un segundo mensaje — y eso sobrevive a que el planificador se
ejecute dos veces, a un reintento y a un redespliegue a mitad de trabajo (ADR-0008).

Un recordatorio duplicado a las siete de la mañana es una queja.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CHAR, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenda.modelos.base import Base, IdMixin
from agenda.modelos.comunes import CreadoEnMixin


class Notification(IdMixin, CreadoEnMixin, Base):
    """Una fila por mensaje que hay que mandar. **Esta tabla es la cola.**

    `business_id` es nulable: los OTP y los avisos de plataforma no son de ningún negocio.
    Esas filas quedan **invisibles para el rol del tenant**, porque la política compara contra
    un valor que nunca coincide con `NULL`. Solo el rol de sistema las toca, que es
    exactamente lo que se quiere.
    """

    __tablename__ = "notifications"

    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE")
    )
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    recipient_kind: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    template_key: Mapped[str] = mapped_column(Text, nullable=False)
    locale: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'es-PA'"))
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    # E.164, correo o token de push. Se purga a los 90 días **para todo el mundo**, haya
    # borrado de cuenta o no: no hace falta guardar un teléfono para saber que un recordatorio
    # se entregó (§15.4).
    destination: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pendiente'"))
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # El recordatorio de 2 h caduca cuando la cita pasa: mandarlo tarde es peor que no
    # mandarlo.
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    queue: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'default'"))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_notifications_idempotency_key"),
        CheckConstraint(
            "recipient_kind IN ('cliente','negocio','staff','admin')",
            name="ck_notifications_recipient_kind_valido",
        ),
        CheckConstraint(
            "channel IN ('whatsapp','email','push','sms')", name="ck_notifications_channel_valido"
        ),
        CheckConstraint(
            "status IN ('pendiente','enviando','enviada','fallida','descartada')",
            name="ck_notifications_status_valido",
        ),
        CheckConstraint(
            "queue IN ('default','programado','pesado')", name="ck_notifications_queue_valida"
        ),
        # **Parcial a propósito:** la cola crece para siempre y el trabajador solo mira las
        # pendientes; un índice completo sobre `scheduled_for` costaría cada vez más para
        # responder exactamente lo mismo.
        Index(
            "ix_notifications_pendientes",
            "scheduled_for",
            postgresql_where=text("status = 'pendiente'"),
        ),
        Index("ix_notifications_business_id", "business_id"),
    )


class NotificationDelivery(IdMixin, Base):
    """Qué dijo el proveedor de cada intento, y cuánto costó.

    El coste estimado por mensaje se guarda porque es lo que permite decidir, con datos, si el
    recordatorio de 24 h vale lo que cuesta.
    """

    __tablename__ = "notification_deliveries"

    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    cost_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str | None] = mapped_column(CHAR(3))
    raw: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (Index("ix_notification_deliveries_notification_id", "notification_id"),)


class NotificationTemplate(IdMixin, Base):
    """Las plantillas como datos: cambiar un texto no es un despliegue.

    `provider_status` existe porque **las plantillas de WhatsApp las aprueba Meta**, no
    nosotros, y hay que poder ver de un vistazo cuál está aprobada y cuál no.
    """

    __tablename__ = "notification_templates"

    key: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    locale: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_template_name: Mapped[str | None] = mapped_column(Text)
    provider_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'borrador'")
    )
    subject: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        UniqueConstraint(
            "key", "channel", "locale", "version", name="uq_notification_templates_clave"
        ),
        CheckConstraint(
            "channel IN ('whatsapp','email','push','sms')",
            name="ck_notification_templates_channel_valido",
        ),
        CheckConstraint(
            "provider_status IN ('borrador','pendiente','aprobada','rechazada')",
            name="ck_notification_templates_provider_status_valido",
        ),
    )


class NotificationPreference(IdMixin, Base):
    """Qué quiere recibir cada usuario y cada negocio (NTF-3)."""

    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE")
    )
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    __table_args__ = (
        CheckConstraint(
            "user_id IS NOT NULL OR business_id IS NOT NULL",
            name="ck_notification_preferences_tiene_sujeto",
        ),
        CheckConstraint(
            "channel IN ('whatsapp','email','push','sms')",
            name="ck_notification_preferences_channel_valido",
        ),
        Index(
            "uq_notification_preferences_sujeto",
            "user_id",
            "business_id",
            "channel",
            "category",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
    )
