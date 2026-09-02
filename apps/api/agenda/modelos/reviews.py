"""Reviews (§9 del modelo de datos).

Un detalle que no es negociable y se marca en el modelo: **nada de la monetización toca estas
tablas.** No hay columna de patrocinio en `reviews`, ni en `business_rating_stats`, ni un peso
de campaña en el agregado. El dinero no compra reputación.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from agenda.modelos.base import Base, IdMixin, TenantMixin
from agenda.modelos.comunes import CreadoEnMixin, MarcasDeTiempoMixin


class Review(IdMixin, TenantMixin, MarcasDeTiempoMixin, Base):
    """La opinión de un cliente sobre una reserva completada (REV-1).

    Las otras dos condiciones de REV-1 —que la reserva esté `completada` y que estemos dentro
    de `business_settings.review_window_days`— se validan en la aplicación: dependen de un
    parámetro configurable y del reloj, y una restricción de base sobre el reloj no se puede
    satisfacer de forma determinista.
    """

    __tablename__ = "reviews"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False
    )
    # Nulable **solo** para sostener el borrado de cuenta (§15). Mientras la persona existe,
    # nunca es nulo.
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="SET NULL")
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    staff_rating: Mapped[int | None] = mapped_column(SmallInteger)  # REV-2, opcional
    body: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'publicada'"))
    hidden_reason: Mapped[str | None] = mapped_column(Text)
    hidden_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        # Una review por reserva, y lo garantiza la base de datos, no la interfaz.
        UniqueConstraint("booking_id", name="uq_reviews_booking_id"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating_rango"),
        CheckConstraint(
            "staff_rating IS NULL OR staff_rating BETWEEN 1 AND 5",
            name="ck_reviews_staff_rating_rango",
        ),
        CheckConstraint(
            "status IN ('publicada','oculta','retirada')", name="ck_reviews_status_valido"
        ),
        Index("ix_reviews_business_id_created_at", "business_id", text("created_at DESC")),
        Index("ix_reviews_staff_id", "staff_id"),
    )


class ReviewMedia(IdMixin, TenantMixin, CreadoEnMixin, Base):
    """Las fotos que acompañan a la review."""

    __tablename__ = "review_media"

    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    moderation_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'pendiente'")
    )

    __table_args__ = (
        CheckConstraint(
            "moderation_status IN ('pendiente','aprobada','rechazada')",
            name="ck_review_media_moderacion_valida",
        ),
        Index("ix_review_media_review_id", "review_id"),
    )


class ReviewReply(IdMixin, TenantMixin, MarcasDeTiempoMixin, Base):
    """La respuesta pública del negocio. El único implementa REV-3 literalmente: **una**."""

    __tablename__ = "review_replies"

    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("review_id", name="uq_review_replies_review_id"),)


class ReviewReport(IdMixin, TenantMixin, CreadoEnMixin, Base):
    """Los reportes que alimentan la cola de moderación (REV-4)."""

    __tablename__ = "review_reports"

    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False
    )
    reporter_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    reporter_kind: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'abierto'"))
    resolved_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )
    resolution_note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "reporter_kind IN ('cliente','negocio','sistema')",
            name="ck_review_reports_reporter_kind_valido",
        ),
        CheckConstraint(
            "status IN ('abierto','en_revision','resuelto','descartado')",
            name="ck_review_reports_status_valido",
        ),
        Index("ix_review_reports_review_id", "review_id"),
    )


class BusinessRatingStats(Base):
    """El agregado precalculado, con el rating bayesiano ya resuelto. 1:1 con `businesses`.

    El rating que ve el cliente y el que entra en el ranking es el **bayesiano** (REV-5,
    ADR-0009): con pocas reviews el negocio se parece a la media, y solo con volumen se separa
    de ella. Es lo que impide que una sola review de 5 estrellas adelante a un negocio con
    ochenta de 4,7.

    Se guarda `rating_avg` **además** porque son cosas distintas y las dos hacen falta: la
    media simple es lo que el dueño espera ver en su panel, y explicarle la diferencia es más
    fácil que explicarle por qué su «4,9» aparece como «4,3».
    """

    __tablename__ = "business_rating_stats"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), primary_key=True
    )
    reviews_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    rating_sum: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    rating_avg: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    rating_bayesian: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    last_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    __table_args__ = (
        CheckConstraint("reviews_count >= 0", name="ck_business_rating_stats_conteo_no_negativo"),
    )
