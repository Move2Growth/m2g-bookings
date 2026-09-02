"""Monetización y pagos (§11 y §12 del modelo de datos).

Dos garantías del proyecto viven aquí y no son negociables:

* **En ninguna tabla hay número de tarjeta, ni CVV, ni nada que se le parezca** (PAY-3,
  garantía nº 4 de la constitución). Solo el token de la pasarela. Como los datos no pasan por
  aquí, el proyecto no entra en el alcance de PCI, y eso es una decisión de arquitectura, no
  una casualidad.
* **El pagador es polimórfico desde el día uno** (`payments.payer_kind`). El error caro no son
  las columnas de PAY-5: es haber escrito `payments.business_id NOT NULL` asumiendo que paga
  siempre el negocio, y tener que migrar la tabla del dinero —con historial fiscal dentro— el
  día que cobre el cliente final.

Nada de esto se enciende en v1: `deposit_enabled` está en `false` y no hay endpoint que cobre.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
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

from agenda.modelos.base import Base, IdMixin, TenantMixin
from agenda.modelos.comunes import CreadoEnMixin, MarcasDeTiempoMixin


class Plan(IdMixin, CreadoEnMixin, Base):
    """Los planes con su precio, sus límites y su fecha efectiva. Catálogo global.

    **Un cambio de precio no es un `UPDATE`** (ADR-0010): es una fila nueva con su fecha
    efectiva. Hay que poder decir qué precio tenía cada negocio en cada momento, y un `UPDATE`
    borra esa respuesta para siempre.
    """

    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(Text, nullable=False)  # 'gratis'
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)  # 0 al lanzamiento
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'USD'"))
    period: Mapped[str] = mapped_column(Text, nullable=False)  # mensual | anual
    trial_days: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    limits: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    features: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )

    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_plans_code_version"),
        CheckConstraint("period IN ('mensual','anual')", name="ck_plans_period_valido"),
        CheckConstraint("price_minor >= 0", name="ck_plans_precio_no_negativo"),
    )


class Subscription(MarcasDeTiempoMixin, Base):
    """La suscripción del negocio. Una por negocio, desde que se registra, **aunque valga 0**.

    Con precio 0 el ciclo se ejecuta igual: el trabajo periódico renueva, marca el ciclo
    cumplido y no genera cobro. Así el camino está probado miles de veces **antes** de que
    haya dinero de por medio; un motor de cobro que se estrena el día que empieza a cobrar es
    un motor sin probar.

    Y una regla de producto que el modelo respeta (ADR-0010): **la suspensión por impago no
    borra datos ni cancela reservas.** Es un cambio de `status`, para que regularizar y volver
    a publicar sea inmediato.
    """

    __tablename__ = "subscriptions"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), primary_key=True
    )
    # Identificador propio además de la clave: `payments` y `subscription_events` apuntan aquí
    # y una clave foránea al negocio confundiría «el cobro de esta suscripción» con «el cobro
    # de este negocio», que no son lo mismo en cuanto haya una segunda suscripción histórica.
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # Apunta a una **versión concreta** del plan: ahí es donde vive el grandfathering.
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    grace_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    grandfathered: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    next_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT")
    )
    next_plan_effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    __table_args__ = (
        UniqueConstraint("id", name="uq_subscriptions_id"),
        CheckConstraint(
            "status IN ('activa','en_gracia','suspendida','cancelada')",
            name="ck_subscriptions_status_valido",
        ),
        CheckConstraint(
            "current_period_end > current_period_start", name="ck_subscriptions_ciclo_valido"
        ),
    )


class SubscriptionEvent(IdMixin, TenantMixin, CreadoEnMixin, Base):
    """Todo lo que le pasó a la suscripción.

    Es lo que permite responder a «¿por qué a este negocio se le cobró esto?» sin
    reconstruirlo de memoria.
    """

    __tablename__ = "subscription_events"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    from_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT")
    )
    to_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT")
    )
    amount_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str | None] = mapped_column(CHAR(3))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    actor_kind: Mapped[str] = mapped_column(Text, nullable=False)
    actor_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )

    __table_args__ = (
        CheckConstraint(
            "type IN ('alta','renovacion','cambio_plan','aviso_previo','entrada_gracia',"
            "'suspension','reactivacion','cancelacion','impago')",
            name="ck_subscription_events_type_valido",
        ),
        CheckConstraint(
            "actor_kind IN ('negocio','sistema','admin')",
            name="ck_subscription_events_actor_kind_valido",
        ),
        Index("ix_subscription_events_subscription_id", "subscription_id"),
    )


class AdProduct(IdMixin, Base):
    """Los productos de posicionamiento con su precio y su duración. Catálogo global."""

    __tablename__ = "ad_products"

    code: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # En v1 solo toma `categoria_zona`; el home y el push a cercanos son ADS-6 y v2.
    placement: Mapped[str] = mapped_column(Text, nullable=False)
    duration_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'USD'"))
    slots: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("3"))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("code", name="uq_ad_products_code"),
        CheckConstraint("placement IN ('categoria_zona')", name="ck_ad_products_placement_valido"),
    )


class AdInventory(IdMixin, Base):
    """Los slots disponibles por categoría, zona y periodo (ADS-2). Global: es de la plataforma.

    El `CHECK (slots_taken <= slots_total)` es lo que hace que «inventario limitado» sea una
    verdad de la base de datos y no una carrera entre dos negocios comprando el último slot a
    la vez — el mismo problema que la doble reserva, resuelto con la misma filosofía.
    """

    __tablename__ = "ad_inventory"

    ad_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ad_products.id", ondelete="RESTRICT"), nullable=False
    )
    service_category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_categories.id", ondelete="RESTRICT"), nullable=False
    )
    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="RESTRICT"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    slots_total: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    slots_taken: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )

    __table_args__ = (
        UniqueConstraint(
            "ad_product_id",
            "service_category_id",
            "zone_id",
            "period_start",
            name="uq_ad_inventory_producto_categoria_zona_periodo",
        ),
        CheckConstraint("slots_taken <= slots_total", name="ck_ad_inventory_slots_disponibles"),
        CheckConstraint("slots_taken >= 0", name="ck_ad_inventory_slots_no_negativos"),
        CheckConstraint("period_end >= period_start", name="ck_ad_inventory_periodo_valido"),
    )


class AdCampaign(IdMixin, TenantMixin, MarcasDeTiempoMixin, Base):
    """La compra concreta de un negocio.

    Una campaña **no ocupa slot** hasta que el pago está confirmado, y por eso el contador de
    `ad_inventory` se incrementa en la misma transacción en la que el pago pasa a `pagado`.

    Los patrocinados **no entran en la fórmula de ranking** (ADR-0009, MKT-4): se resuelven en
    una consulta aparte y se intercalan después. El modelo lo refleja en que no hay ninguna
    columna que una esta tabla con `business_ranking_signals`.
    """

    __tablename__ = "ad_campaigns"

    ad_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ad_products.id", ondelete="RESTRICT"), nullable=False
    )
    ad_inventory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ad_inventory.id", ondelete="RESTRICT")
    )
    service_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_categories.id", ondelete="RESTRICT")
    )
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("zones.id", ondelete="RESTRICT")
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'USD'"))
    # La clave foránea a `payments` se añade con `ALTER TABLE` en la migración: `payments`
    # también apunta aquí y el ciclo hay que romperlo por algún lado.
    payment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    coupon_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coupons.id", ondelete="SET NULL")
    )
    auto_renew: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    __table_args__ = (
        CheckConstraint(
            "status IN ('pendiente_pago','activa','finalizada','cancelada','rechazada')",
            name="ck_ad_campaigns_status_valido",
        ),
        CheckConstraint("ends_at > starts_at", name="ck_ad_campaigns_rango_valido"),
        Index("ix_ad_campaigns_business_id_status", "business_id", "status"),
        # Parcial: la consulta de patrocinados solo mira las campañas vivas.
        Index(
            "ix_ad_campaigns_activas",
            "service_category_id",
            "zone_id",
            "ends_at",
            postgresql_where=text("status = 'activa'"),
        ),
    )


class AdMetricDaily(TenantMixin, Base):
    """Impresiones, clics y reservas atribuidas de la campaña (ADS-4)."""

    __tablename__ = "ad_metrics_daily"

    ad_campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ad_campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    clicks: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    attributed_bookings: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )


class Coupon(IdMixin, CreadoEnMixin, Base):
    """Cupones y promociones administrables (ADS-5). Catálogo global."""

    __tablename__ = "coupons"

    code: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # porcentaje | importe
    percent_off: Mapped[int | None] = mapped_column(SmallInteger)
    amount_off_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str | None] = mapped_column(CHAR(3))
    applies_to: Mapped[str] = mapped_column(Text, nullable=False)  # suscripcion | ads | ambos
    max_redemptions: Mapped[int | None] = mapped_column(Integer)
    redemptions_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL")
    )

    __table_args__ = (
        UniqueConstraint("code", name="uq_coupons_code"),
        CheckConstraint("kind IN ('porcentaje','importe')", name="ck_coupons_kind_valido"),
        CheckConstraint(
            "applies_to IN ('suscripcion','ads','ambos')", name="ck_coupons_applies_to_valido"
        ),
        # Un cupón de porcentaje tiene porcentaje y uno de importe tiene importe. Sin esto se
        # cuela un cupón que no descuenta nada y el negocio se entera al pagar.
        CheckConstraint(
            "(kind = 'porcentaje' AND percent_off IS NOT NULL)"
            " OR (kind = 'importe' AND amount_off_minor IS NOT NULL AND currency IS NOT NULL)",
            name="ck_coupons_descuento_coherente",
        ),
        CheckConstraint(
            "max_redemptions IS NULL OR redemptions_count <= max_redemptions",
            name="ck_coupons_canjes_dentro_del_limite",
        ),
    )


class CouponRedemption(IdMixin, TenantMixin, CreadoEnMixin, Base):
    """Quién canjeó qué, para que el límite de canjes signifique algo."""

    __tablename__ = "coupon_redemptions"

    coupon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("coupons.id", ondelete="RESTRICT"), nullable=False
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL")
    )
    amount_off_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str | None] = mapped_column(CHAR(3))

    __table_args__ = (
        # Un negocio canjea un cupón una vez. El límite global vive en `coupons`.
        UniqueConstraint(
            "coupon_id", "business_id", name="uq_coupon_redemptions_coupon_id_business_id"
        ),
    )


class PaymentMethod(IdMixin, MarcasDeTiempoMixin, Base):
    """El **token** de la pasarela y cuatro datos de presentación. Nada más.

    Aquí no hay número de tarjeta, ni CVV, y no lo va a haber (PAY-3). `brand`, `last4` y la
    caducidad son para que el dueño reconozca cuál de sus tarjetas es, y llegan del proveedor
    ya recortados.
    """

    __tablename__ = "payment_methods"

    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="RESTRICT")
    )
    # Hueco PAY-5: que un **cliente** guarde un medio de pago. Hoy siempre NULL.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_token: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str] = mapped_column(Text, nullable=False)  # tarjeta | yappy
    brand: Mapped[str | None] = mapped_column(Text)
    last4: Mapped[str | None] = mapped_column(CHAR(4))
    exp_month: Mapped[int | None] = mapped_column(SmallInteger)
    exp_year: Mapped[int | None] = mapped_column(SmallInteger)
    holder_label: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'activo'"))

    __table_args__ = (
        CheckConstraint(
            "business_id IS NOT NULL OR user_id IS NOT NULL",
            name="ck_payment_methods_tiene_dueno",
        ),
        CheckConstraint("method IN ('tarjeta','yappy')", name="ck_payment_methods_method_valido"),
        Index("ix_payment_methods_business_id", "business_id"),
        Index("ix_payment_methods_user_id", "user_id"),
    )


class Payment(IdMixin, MarcasDeTiempoMixin, Base):
    """Un intento de cobro y su desenlace.

    `business_id` es nulable y significa siempre lo mismo —«el negocio al que se refiere el
    cobro»—; quién paga lo dice `payer_kind`. Esa es la decisión que evita migrar la tabla del
    dinero el día que entre PAY-5.
    """

    __tablename__ = "payments"

    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="RESTRICT")
    )
    payer_kind: Mapped[str] = mapped_column(Text, nullable=False)  # negocio | cliente
    payer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="RESTRICT")
    )
    ad_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ad_campaigns.id", ondelete="RESTRICT")
    )
    # Hueco PAY-5: colgar el cobro de una cita concreta. Hoy siempre NULL.
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="RESTRICT")
    )
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    method: Mapped[str | None] = mapped_column(Text)
    payment_method_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_methods.id", ondelete="SET NULL")
    )
    # Texto libre a propósito: la pasarela es D5 y la decide Luis (§16).
    provider: Mapped[str | None] = mapped_column(Text)
    provider_payment_id: Mapped[str | None] = mapped_column(Text)
    provider_status: Mapped[str | None] = mapped_column(Text)
    # Misma idea que la clave de las notificaciones y por la misma razón: la app va a
    # reintentar sola con 3G y **un reintento no puede cobrar dos veces**.
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    failure_code: Mapped[str | None] = mapped_column(Text)
    failure_message: Mapped[str | None] = mapped_column(Text)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
        CheckConstraint("payer_kind IN ('negocio','cliente')", name="ck_payments_payer_kind_valido"),
        CheckConstraint(
            "purpose IN ('suscripcion','ads','deposito_reserva','servicio')",
            name="ck_payments_purpose_valido",
        ),
        CheckConstraint(
            "status IN ('iniciado','autorizado','pagado','fallido','reembolsado','expirado')",
            name="ck_payments_status_valido",
        ),
        CheckConstraint(
            "method IS NULL OR method IN ('tarjeta','yappy')", name="ck_payments_method_valido"
        ),
        Index("ix_payments_business_id_created_at", "business_id", text("created_at DESC")),
        Index("ix_payments_subscription_id", "subscription_id"),
    )


class Invoice(IdMixin, TenantMixin, CreadoEnMixin, Base):
    """El recibo con los datos fiscales del negocio (PAY-4).

    Los datos fiscales van **copiados**: un recibo emitido no cambia porque el negocio edite
    su RUC seis meses después.
    """

    __tablename__ = "invoices"

    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False
    )
    number: Mapped[str] = mapped_column(Text, nullable=False)
    series: Mapped[str | None] = mapped_column(Text)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    subtotal_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tax_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(Text)
    tax_id_dv: Mapped[str | None] = mapped_column(Text)
    legal_name: Mapped[str | None] = mapped_column(Text)
    address_snapshot: Mapped[str | None] = mapped_column(Text)
    pdf_key: Mapped[str | None] = mapped_column(Text)
    # Hueco de la factura electrónica de la DGI (D16, v2).
    dgi_status: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("payment_id", name="uq_invoices_payment_id"),
        UniqueConstraint("number", name="uq_invoices_number"),
    )


class PaymentProviderEvent(IdMixin, Base):
    """Webhooks crudos de la pasarela, tal como llegaron.

    **Sin aislamiento por negocio a propósito:** un webhook llega antes de que sepamos de qué
    negocio es. Se procesa con el rol de sistema y de ahí sale el `payment_id`. El único sobre
    `provider_event_id` es lo que hace que reprocesar un webhook reenviado no duplique nada.
    """

    __tablename__ = "payment_provider_events"

    provider: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    provider_event_id: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    signature_valid: Mapped[bool | None] = mapped_column(Boolean)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_error: Mapped[str | None] = mapped_column(Text)
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL")
    )

    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_event_id", name="uq_payment_provider_events_provider_event_id"
        ),
        Index(
            "ix_payment_provider_events_sin_procesar",
            "received_at",
            postgresql_where=text("processed_at IS NULL"),
        ),
    )
