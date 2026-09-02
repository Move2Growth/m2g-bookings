"""Todos los modelos, importados en un sitio.

Alembic solo ve las tablas que estén registradas en `Base.metadata` cuando arranca, y una
tabla que no importa nadie no está registrada. Este archivo es lo que evita el fallo clásico:
una migración generada «vacía» porque el módulo del modelo nuevo no se había importado, y el
error apareciendo semanas después con datos dentro.

Los módulos están en orden de dependencia para que leerlos de arriba abajo cuente la historia
del producto: quién eres, dónde trabajas, con quién, qué vendes, a quién, qué te reservan, qué
opinan, cómo te encuentran, quién paga y a quién se avisa.
"""

from agenda.modelos.base import Base, FechasMixin, IdMixin, TenantMixin, nuevo_id
from agenda.modelos.catalogo import Service, ServiceCategory, ServiceVariant
from agenda.modelos.clientes import BusinessClient, ClientProfile, Favorite
from agenda.modelos.comunes import CreadoEnMixin, MarcasDeTiempoMixin
from agenda.modelos.equipo import StaffHours, StaffProfile, StaffService, TimeBlockRule
from agenda.modelos.identidad import (
    AdminSession,
    AdminUser,
    AuthIdentity,
    Membership,
    OtpCode,
    PrivacyRequest,
    Session,
    User,
    UserConsent,
)
from agenda.modelos.interno import (
    AuditLog,
    FeatureFlag,
    FeatureFlagOverride,
    IdempotencyKey,
    ModerationQueue,
    PlatformSetting,
)
from agenda.modelos.marketplace import (
    BusinessRankingSignals,
    GeocodingCache,
    Holiday,
    ListingClickDaily,
    ListingImpressionDaily,
    RankingWeights,
    SlugRedirect,
    Zone,
)
from agenda.modelos.monetizacion import (
    AdCampaign,
    AdInventory,
    AdMetricDaily,
    AdProduct,
    Coupon,
    CouponRedemption,
    Invoice,
    Payment,
    PaymentMethod,
    PaymentProviderEvent,
    Plan,
    Subscription,
    SubscriptionEvent,
)
from agenda.modelos.negocio import (
    Attribute,
    AttributeValue,
    Business,
    BusinessAttribute,
    BusinessCategory,
    BusinessHours,
    BusinessMedia,
    BusinessSettings,
    Location,
)
from agenda.modelos.notificaciones import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationTemplate,
)
from agenda.modelos.reservas import (
    Booking,
    BookingEvent,
    BookingItem,
    StaffOccupancy,
)
from agenda.modelos.reviews import (
    BusinessRatingStats,
    Review,
    ReviewMedia,
    ReviewReply,
    ReviewReport,
)

__all__ = [
    "AdCampaign",
    "AdInventory",
    "AdMetricDaily",
    "AdProduct",
    "AdminSession",
    "AdminUser",
    "Attribute",
    "AttributeValue",
    "AuditLog",
    "AuthIdentity",
    "Base",
    "Booking",
    "BookingEvent",
    "BookingItem",
    "Business",
    "BusinessAttribute",
    "BusinessCategory",
    "BusinessClient",
    "BusinessHours",
    "BusinessMedia",
    "BusinessRankingSignals",
    "BusinessRatingStats",
    "BusinessSettings",
    "ClientProfile",
    "Coupon",
    "CouponRedemption",
    "CreadoEnMixin",
    "Favorite",
    "FeatureFlag",
    "FeatureFlagOverride",
    "FechasMixin",
    "GeocodingCache",
    "Holiday",
    "IdMixin",
    "IdempotencyKey",
    "Invoice",
    "ListingClickDaily",
    "ListingImpressionDaily",
    "Location",
    "MarcasDeTiempoMixin",
    "Membership",
    "ModerationQueue",
    "Notification",
    "NotificationDelivery",
    "NotificationPreference",
    "NotificationTemplate",
    "OtpCode",
    "Payment",
    "PaymentMethod",
    "PaymentProviderEvent",
    "Plan",
    "PlatformSetting",
    "PrivacyRequest",
    "RankingWeights",
    "Review",
    "ReviewMedia",
    "ReviewReply",
    "ReviewReport",
    "Service",
    "ServiceCategory",
    "ServiceVariant",
    "Session",
    "SlugRedirect",
    "StaffHours",
    "StaffOccupancy",
    "StaffProfile",
    "StaffService",
    "Subscription",
    "SubscriptionEvent",
    "TenantMixin",
    "TimeBlockRule",
    "User",
    "UserConsent",
    "Zone",
    "nuevo_id",
]
