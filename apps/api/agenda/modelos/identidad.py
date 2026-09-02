"""Identidad y acceso (§3 del modelo de datos, ADR-0006).

Tres piezas que la gente confunde y aquí están separadas: **quién eres** (`users`), **cómo lo
demuestras** (`auth_identities`, `otp_codes`, `sessions`) y **qué puedes hacer** (`memberships`).

Ninguna lleva aislamiento por negocio salvo `memberships`, y el motivo es el que más veces se
equivoca al modelar un marketplace: **una persona no pertenece a un salón.** Si `users`
llevara `business_id`, un cliente que reserva en tres sitios serían tres personas y su
historial no existiría.
"""

from __future__ import annotations

import uuid
from datetime import datetime

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
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenda.modelos.base import Base, IdMixin, TenantMixin
from agenda.modelos.comunes import CreadoEnMixin, MarcasDeTiempoMixin


class User(IdMixin, MarcasDeTiempoMixin, Base):
    """Una fila por persona. El teléfono verificado en E.164 es su identificador natural."""

    __tablename__ = "users"

    # Siempre normalizado a E.164 y en un único sitio del código: dos formatos del mismo
    # número son dos cuentas, y el día que pase el cliente jura que ya tenía una y tiene razón.
    phone_e164: Mapped[str] = mapped_column(Text, nullable=False)
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email: Mapped[str | None] = mapped_column(Text)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    # La clave en el almacén de objetos, no una URL firmada: las URL caducan y guardarlas
    # obligaría a reescribir filas cada vez.
    avatar_key: Mapped[str | None] = mapped_column(Text)
    locale: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'es-PA'"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'activo'"))
    # Lápida de la Ley 81: la fila sobrevive anonimizada porque de ella cuelgan reservas y
    # reviews de terceros que no se pueden borrar (§15).
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("phone_e164", name="uq_users_phone_e164"),
        CheckConstraint(
            "status IN ('activo','bloqueado','eliminado')", name="ck_users_status_valido"
        ),
        # El único por correo es funcional sobre `lower(email)` y parcial; se crea en la
        # migración porque SQLAlchemy no lo expresa con `UniqueConstraint`.
        Index(
            "uq_users_email_lower",
            func.lower(text("email")),
            unique=True,
            postgresql_where=text("email IS NOT NULL"),
        ),
    )


class AuthIdentity(IdMixin, Base):
    """Un método con el que una persona demuestra quién es (teléfono, Google, Apple)."""

    __tablename__ = "auth_identities"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    # El E.164 para el teléfono, o el «sub» que devuelve el proveedor de identidad.
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    email_at_provider: Mapped[str | None] = mapped_column(Text)
    # Enlazar una identidad a una cuenta existente por un correo **sin verificar** es un
    # secuestro de cuenta; por eso el dato viaja hasta aquí y se guarda (ADR-0006).
    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("provider", "subject", name="uq_auth_identities_provider_subject"),
        UniqueConstraint("user_id", "provider", name="uq_auth_identities_user_id_provider"),
        CheckConstraint(
            "provider IN ('telefono','google','apple')", name="ck_auth_identities_provider_valido"
        ),
    )


class Session(IdMixin, Base):
    """Sesión viva, con su refresco opaco rotatorio y el negocio activo."""

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Reutilizar un refresco ya rotado invalida **toda la familia**: es la firma de un token
    # robado, y sin agrupar por familia no hay forma de cortar la cadena entera.
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # sha256 del refresco. El token en claro no se guarda jamás.
    refresh_token_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    # Lo que alimenta `app.current_business_id`. Va en el token, no en la petición: si el
    # cliente pudiera mandar el negocio, el aislamiento sería una sugerencia.
    active_business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="SET NULL")
    )
    surface: Mapped[str] = mapped_column(Text, nullable=False)
    device_label: Mapped[str | None] = mapped_column(Text)
    ip_hash: Mapped[bytes | None] = mapped_column(LargeBinary)
    user_agent: Mapped[str | None] = mapped_column(Text)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("refresh_token_hash", name="uq_sessions_refresh_token_hash"),
        CheckConstraint("surface IN ('web','app')", name="ck_sessions_surface_valida"),
        CheckConstraint(
            "revoked_reason IS NULL OR revoked_reason IN "
            "('cierre_sesion','rotacion_reusada','borrado_cuenta','admin')",
            name="ck_sessions_motivo_revocacion_valido",
        ),
        # Parcial: «cerrar sesión en todos los dispositivos» solo mira las vivas, y el índice
        # completo crecería con noventa días de sesiones muertas dentro.
        Index("ix_sessions_vivas", "user_id", postgresql_where=text("revoked_at IS NULL")),
        Index("ix_sessions_expires_at", "expires_at"),
    )


class OtpCode(IdMixin, CreadoEnMixin, Base):
    """Código de un solo uso, guardado con hash, con su ventana y sus intentos."""

    __tablename__ = "otp_codes"

    destination: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    # Nunca el código en claro: si la base se filtra, un OTP en claro es una sesión regalada.
    code_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    attempts: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("5")
    )
    request_ip_hash: Mapped[bytes | None] = mapped_column(LargeBinary)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "channel IN ('whatsapp','sms','email')", name="ck_otp_codes_channel_valido"
        ),
        CheckConstraint(
            "purpose IN ('registro','login','verificacion_telefono','cambio_telefono')",
            name="ck_otp_codes_purpose_valido",
        ),
        # Como mucho **un** código vivo por destino y finalidad: emitir uno nuevo invalida el
        # anterior. Es seguridad y es control de gasto, porque cada WhatsApp se paga.
        Index(
            "uq_otp_codes_vivo",
            "destination",
            "purpose",
            unique=True,
            postgresql_where=text("consumed_at IS NULL AND invalidated_at IS NULL"),
        ),
    )


class Membership(IdMixin, TenantMixin, MarcasDeTiempoMixin, Base):
    """Qué rol tiene un usuario en un negocio. Es la unidad de permiso."""

    __tablename__ = "memberships"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    invite_channel: Mapped[str | None] = mapped_column(Text)
    # La invitación no necesita tabla propia: es un estado de la membresía (ONB-4).
    invite_token_hash: Mapped[bytes | None] = mapped_column(LargeBinary)
    invite_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("business_id", "user_id", name="uq_memberships_business_id_user_id"),
        # `recepcion` entra en el enumerado desde la primera migración aunque la interfaz no
        # lo ofrezca (§14.5): lo caro no es la migración, es que una app ya publicada no
        # sepa interpretar un valor nuevo dentro de la misma versión de la API (ADR-0012).
        CheckConstraint(
            "role IN ('dueno','profesional','recepcion')", name="ck_memberships_role_valido"
        ),
        CheckConstraint(
            "status IN ('invitada','activa','revocada')", name="ck_memberships_status_valido"
        ),
        Index("ix_memberships_user_id", "user_id"),
    )


class AdminUser(IdMixin, MarcasDeTiempoMixin, Base):
    """Equipo interno de M2G. Está **aparte** de `users` a propósito (ADR-0006).

    Un superadministrador no es un usuario con una casilla marcada: si lo fuera, cualquier
    fallo de escalada en la aplicación del cliente sería una escalada al back-office.
    """

    __tablename__ = "admin_users"

    email: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)  # argon2id
    totp_secret: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)  # cifrado en reposo
    # 2FA obligatorio, no opcional: la columna existe para poder auditar que está activo,
    # no para poder apagarlo.
    totp_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'activo'"))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "role IN ('superadmin','soporte','finanzas','moderacion')",
            name="ck_admin_users_role_valido",
        ),
        Index("uq_admin_users_email_lower", func.lower(text("email")), unique=True),
    )


class AdminSession(IdMixin, Base):
    """Sesión del back-office. Mismo par acceso/refresco que la de la app, con caducidad más
    corta y **sin compartir tabla**: revocar todas las sesiones de un cliente no puede tener
    ninguna posibilidad de tocar las del equipo interno, ni al revés."""

    __tablename__ = "admin_sessions"

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False
    )
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    refresh_token_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    ip_hash: Mapped[bytes | None] = mapped_column(LargeBinary)
    user_agent: Mapped[str | None] = mapped_column(Text)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("refresh_token_hash", name="uq_admin_sessions_refresh_token_hash"),
        Index("ix_admin_sessions_admin_user_id", "admin_user_id"),
    )


class UserConsent(IdMixin, Base):
    """Prueba de consentimiento por finalidad y versión (Ley 81).

    Es **append-only**: revocar añade una fila, no actualiza la anterior. La ley exige poder
    demostrar qué aceptó cada persona y cuándo, y un `UPDATE` destruye justamente esa prueba.
    """

    __tablename__ = "user_consents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_hash: Mapped[bytes | None] = mapped_column(LargeBinary)
    user_agent: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('terminos_cliente','terminos_negocio','privacidad','marketing','whatsapp')",
            name="ck_user_consents_kind_valido",
        ),
        Index("ix_user_consents_user_id_kind", "user_id", "kind"),
    )


class PrivacyRequest(IdMixin, Base):
    """Solicitud de exportación, rectificación o borrado, con su ventana de gracia.

    La ventana existe porque el borrado es irreversible y el botón está a dos toques.
    """

    __tablename__ = "privacy_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    grace_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # La exportación generada, **con caducidad**: un volcado de datos personales que vive
    # para siempre en un bucket es un incidente esperando su turno.
    artifact_key: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "kind IN ('exportacion','rectificacion','borrado')",
            name="ck_privacy_requests_kind_valido",
        ),
        CheckConstraint(
            "status IN ('recibida','en_gracia','ejecutada','cancelada','rechazada')",
            name="ck_privacy_requests_status_valido",
        ),
        Index("ix_privacy_requests_user_id", "user_id"),
    )
