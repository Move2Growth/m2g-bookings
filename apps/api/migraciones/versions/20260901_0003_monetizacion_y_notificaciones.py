"""Monetización, pagos, notificaciones y back-office.

Revision ID: 0003_monetizacion
Revises: 0002_nucleo
Create Date: 2026-09-01

Última de las tres revisiones de la migración inicial. Cierra además los dos ciclos de claves
foráneas que no se podían declarar antes: `ad_campaigns.payment_id` y
`bookings.deposit_payment_id` apuntan a `payments`, y `payments` apunta a las dos. Un ciclo no
se puede crear en una sola sentencia, así que se rompe con `ALTER TABLE` al final, que es la
forma honesta de hacerlo.

Nada de este bloque se enciende en v1: la suscripción existe y vale 0, el depósito está
apagado y **ningún cobro real se activa sin OK explícito** (constitution §4).
"""

from __future__ import annotations

from alembic import op

revision = "0003_monetizacion"
down_revision = "0002_nucleo"
branch_labels = None
depends_on = None

#: Tablas de este bloque que son propiedad de un negocio y llevan política de tenant estricta.
TABLAS_CON_TENANT = (
    "subscriptions",
    "subscription_events",
    "ad_campaigns",
    "ad_metrics_daily",
    "coupon_redemptions",
    "payment_methods",
    "payments",
    "invoices",
    "feature_flag_overrides",
)

TABLAS_CON_UPDATED_AT = (
    "subscriptions",
    "ad_campaigns",
    "payment_methods",
    "payments",
)


def upgrade() -> None:
    _monetizacion()
    _pagos()
    _cerrar_ciclos()
    _notificaciones()
    _back_office()
    _disparadores()
    _seguridad_por_fila()
    _permisos()


def _monetizacion() -> None:
    op.execute(
        """
        CREATE TABLE subscriptions (
          business_id            uuid NOT NULL,
          id                     uuid NOT NULL DEFAULT uuid_generate_v7(),
          plan_id                uuid NOT NULL,
          status                 text NOT NULL,
          current_period_start   timestamptz NOT NULL,
          current_period_end     timestamptz NOT NULL,
          grace_until            timestamptz,
          grandfathered          boolean NOT NULL DEFAULT false,
          next_plan_id           uuid,
          next_plan_effective_at timestamptz,
          cancel_at_period_end   boolean NOT NULL DEFAULT false,
          created_at             timestamptz NOT NULL DEFAULT now(),
          updated_at             timestamptz NOT NULL DEFAULT now(),
          -- Una por negocio. Todo negocio tiene suscripción desde que se registra, aunque
          -- valga 0: así el motor de cobro está probado miles de veces antes de que haya
          -- dinero de por medio.
          CONSTRAINT pk_subscriptions PRIMARY KEY (business_id),
          CONSTRAINT uq_subscriptions_id UNIQUE (id),
          CONSTRAINT fk_subscriptions_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE CASCADE,
          -- Apunta a una **versión concreta** del plan: ahí vive el grandfathering.
          CONSTRAINT fk_subscriptions_plan_id_plans FOREIGN KEY (plan_id)
            REFERENCES plans(id) ON DELETE RESTRICT,
          CONSTRAINT fk_subscriptions_next_plan_id_plans FOREIGN KEY (next_plan_id)
            REFERENCES plans(id) ON DELETE RESTRICT,
          CONSTRAINT ck_subscriptions_status_valido
            CHECK (status IN ('activa','en_gracia','suspendida','cancelada')),
          CONSTRAINT ck_subscriptions_ciclo_valido
            CHECK (current_period_end > current_period_start)
        );

        CREATE TABLE subscription_events (
          id              uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id     uuid NOT NULL,
          subscription_id uuid NOT NULL,
          type            text NOT NULL,
          from_plan_id    uuid,
          to_plan_id      uuid,
          amount_minor    bigint,
          currency        char(3),
          effective_at    timestamptz NOT NULL,
          payload         jsonb NOT NULL DEFAULT '{}'::jsonb,
          actor_kind      text NOT NULL,
          actor_admin_id  uuid,
          created_at      timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_subscription_events PRIMARY KEY (id),
          CONSTRAINT fk_subscription_events_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_subscription_events_subscription_id_subscriptions
            FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE,
          CONSTRAINT fk_subscription_events_from_plan_id_plans FOREIGN KEY (from_plan_id)
            REFERENCES plans(id) ON DELETE RESTRICT,
          CONSTRAINT fk_subscription_events_to_plan_id_plans FOREIGN KEY (to_plan_id)
            REFERENCES plans(id) ON DELETE RESTRICT,
          CONSTRAINT fk_subscription_events_actor_admin_id_admin_users
            FOREIGN KEY (actor_admin_id) REFERENCES admin_users(id) ON DELETE SET NULL,
          CONSTRAINT ck_subscription_events_type_valido CHECK (
            type IN ('alta','renovacion','cambio_plan','aviso_previo','entrada_gracia',
                     'suspension','reactivacion','cancelacion','impago')
          ),
          CONSTRAINT ck_subscription_events_actor_kind_valido
            CHECK (actor_kind IN ('negocio','sistema','admin'))
        );
        CREATE INDEX ix_subscription_events_business_id ON subscription_events (business_id);
        CREATE INDEX ix_subscription_events_subscription_id
          ON subscription_events (subscription_id);

        CREATE TABLE ad_campaigns (
          id                  uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id         uuid NOT NULL,
          ad_product_id       uuid NOT NULL,
          ad_inventory_id     uuid,
          service_category_id uuid,
          zone_id             uuid,
          starts_at           timestamptz NOT NULL,
          ends_at             timestamptz NOT NULL,
          status              text NOT NULL,
          price_minor         bigint NOT NULL,
          currency            char(3) NOT NULL DEFAULT 'USD',
          payment_id          uuid,
          coupon_id           uuid,
          auto_renew          boolean NOT NULL DEFAULT false,
          created_at          timestamptz NOT NULL DEFAULT now(),
          updated_at          timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_ad_campaigns PRIMARY KEY (id),
          CONSTRAINT fk_ad_campaigns_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_ad_campaigns_ad_product_id_ad_products FOREIGN KEY (ad_product_id)
            REFERENCES ad_products(id) ON DELETE RESTRICT,
          CONSTRAINT fk_ad_campaigns_ad_inventory_id_ad_inventory FOREIGN KEY (ad_inventory_id)
            REFERENCES ad_inventory(id) ON DELETE RESTRICT,
          CONSTRAINT fk_ad_campaigns_service_category_id_service_categories
            FOREIGN KEY (service_category_id)
            REFERENCES service_categories(id) ON DELETE RESTRICT,
          CONSTRAINT fk_ad_campaigns_zone_id_zones FOREIGN KEY (zone_id)
            REFERENCES zones(id) ON DELETE RESTRICT,
          CONSTRAINT fk_ad_campaigns_coupon_id_coupons FOREIGN KEY (coupon_id)
            REFERENCES coupons(id) ON DELETE SET NULL,
          -- Una campaña **no ocupa slot** hasta que el pago está confirmado.
          CONSTRAINT ck_ad_campaigns_status_valido
            CHECK (status IN ('pendiente_pago','activa','finalizada','cancelada','rechazada')),
          CONSTRAINT ck_ad_campaigns_rango_valido CHECK (ends_at > starts_at)
        );
        CREATE INDEX ix_ad_campaigns_business_id ON ad_campaigns (business_id);
        CREATE INDEX ix_ad_campaigns_business_id_status ON ad_campaigns (business_id, status);
        -- Parcial: la consulta de patrocinados solo mira las campañas vivas. Los patrocinados
        -- se resuelven en una consulta **aparte** y se intercalan después: no hay ninguna
        -- columna que una esta tabla con `business_ranking_signals` (MKT-4, ADR-0009).
        CREATE INDEX ix_ad_campaigns_activas
          ON ad_campaigns (service_category_id, zone_id, ends_at) WHERE status = 'activa';

        CREATE TABLE ad_metrics_daily (
          ad_campaign_id      uuid NOT NULL,
          day                 date NOT NULL,
          business_id         uuid NOT NULL,
          impressions         integer NOT NULL DEFAULT 0,
          clicks              integer NOT NULL DEFAULT 0,
          attributed_bookings integer NOT NULL DEFAULT 0,
          CONSTRAINT pk_ad_metrics_daily PRIMARY KEY (ad_campaign_id, day),
          CONSTRAINT fk_ad_metrics_daily_ad_campaign_id_ad_campaigns
            FOREIGN KEY (ad_campaign_id) REFERENCES ad_campaigns(id) ON DELETE CASCADE,
          CONSTRAINT fk_ad_metrics_daily_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT
        );
        CREATE INDEX ix_ad_metrics_daily_business_id ON ad_metrics_daily (business_id);
        """
    )


def _pagos() -> None:
    op.execute(
        """
        CREATE TABLE payment_methods (
          id             uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id    uuid,
          user_id        uuid,
          provider       text NOT NULL,
          -- LO ÚNICO que se guarda del medio de pago. Aquí no hay número de tarjeta, ni CVV,
          -- y no lo va a haber (PAY-3). Como los datos no pasan por aquí, el proyecto no
          -- entra en el alcance de PCI, y eso es arquitectura, no casualidad.
          provider_token text NOT NULL,
          method         text NOT NULL,
          brand          text,
          last4          char(4),
          exp_month      smallint,
          exp_year       smallint,
          holder_label   text,
          is_default     boolean NOT NULL DEFAULT false,
          status         text NOT NULL DEFAULT 'activo',
          created_at     timestamptz NOT NULL DEFAULT now(),
          updated_at     timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_payment_methods PRIMARY KEY (id),
          CONSTRAINT fk_payment_methods_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          -- Hueco PAY-5: que un **cliente** guarde un medio de pago. Hoy siempre NULL.
          CONSTRAINT fk_payment_methods_user_id_users FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE CASCADE,
          CONSTRAINT ck_payment_methods_tiene_dueno
            CHECK (business_id IS NOT NULL OR user_id IS NOT NULL),
          CONSTRAINT ck_payment_methods_method_valido CHECK (method IN ('tarjeta','yappy'))
        );
        CREATE INDEX ix_payment_methods_business_id ON payment_methods (business_id);
        CREATE INDEX ix_payment_methods_user_id ON payment_methods (user_id);

        CREATE TABLE payments (
          id                  uuid NOT NULL DEFAULT uuid_generate_v7(),
          -- Nulable a propósito y significa siempre lo mismo: «el negocio al que se refiere
          -- el cobro». Quién paga lo dice `payer_kind`. Esa es la decisión que evita migrar
          -- la tabla del dinero el día que entre PAY-5 (§14.4).
          business_id         uuid,
          payer_kind          text NOT NULL,
          payer_user_id       uuid,
          purpose             text NOT NULL,
          subscription_id     uuid,
          ad_campaign_id      uuid,
          booking_id          uuid,
          amount_minor        bigint NOT NULL,
          currency            char(3) NOT NULL,
          status              text NOT NULL,
          method              text,
          payment_method_id   uuid,
          -- Texto libre a propósito: la pasarela es D5 y la decide Luis.
          provider            text,
          provider_payment_id text,
          provider_status     text,
          idempotency_key     text NOT NULL,
          failure_code        text,
          failure_message     text,
          paid_at             timestamptz,
          created_at          timestamptz NOT NULL DEFAULT now(),
          updated_at          timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_payments PRIMARY KEY (id),
          -- La app va a reintentar sola con 3G y **un reintento no puede cobrar dos veces**.
          CONSTRAINT uq_payments_idempotency_key UNIQUE (idempotency_key),
          CONSTRAINT fk_payments_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_payments_payer_user_id_users FOREIGN KEY (payer_user_id)
            REFERENCES users(id) ON DELETE SET NULL,
          CONSTRAINT fk_payments_subscription_id_subscriptions FOREIGN KEY (subscription_id)
            REFERENCES subscriptions(id) ON DELETE RESTRICT,
          CONSTRAINT fk_payments_ad_campaign_id_ad_campaigns FOREIGN KEY (ad_campaign_id)
            REFERENCES ad_campaigns(id) ON DELETE RESTRICT,
          CONSTRAINT fk_payments_booking_id_bookings FOREIGN KEY (booking_id)
            REFERENCES bookings(id) ON DELETE RESTRICT,
          CONSTRAINT fk_payments_payment_method_id_payment_methods
            FOREIGN KEY (payment_method_id) REFERENCES payment_methods(id) ON DELETE SET NULL,
          CONSTRAINT ck_payments_payer_kind_valido CHECK (payer_kind IN ('negocio','cliente')),
          CONSTRAINT ck_payments_purpose_valido
            CHECK (purpose IN ('suscripcion','ads','deposito_reserva','servicio')),
          CONSTRAINT ck_payments_status_valido CHECK (
            status IN ('iniciado','autorizado','pagado','fallido','reembolsado','expirado')
          ),
          CONSTRAINT ck_payments_method_valido
            CHECK (method IS NULL OR method IN ('tarjeta','yappy'))
        );
        CREATE INDEX ix_payments_business_id_created_at ON payments (business_id, created_at DESC);
        CREATE INDEX ix_payments_subscription_id ON payments (subscription_id);

        CREATE TABLE invoices (
          id               uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id      uuid NOT NULL,
          payment_id       uuid NOT NULL,
          number           text NOT NULL,
          series           text,
          issued_at        timestamptz NOT NULL,
          subtotal_minor   bigint NOT NULL,
          tax_minor        bigint NOT NULL DEFAULT 0,
          total_minor      bigint NOT NULL,
          currency         char(3) NOT NULL,
          -- Copiados, no leídos del perfil: un recibo emitido no cambia porque el negocio
          -- edite su RUC seis meses después.
          tax_id           text,
          tax_id_dv        text,
          legal_name       text,
          address_snapshot text,
          pdf_key          text,
          dgi_status       text,
          created_at       timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_invoices PRIMARY KEY (id),
          CONSTRAINT uq_invoices_payment_id UNIQUE (payment_id),
          CONSTRAINT uq_invoices_number UNIQUE (number),
          CONSTRAINT fk_invoices_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_invoices_payment_id_payments FOREIGN KEY (payment_id)
            REFERENCES payments(id) ON DELETE RESTRICT
        );
        CREATE INDEX ix_invoices_business_id ON invoices (business_id);

        CREATE TABLE coupon_redemptions (
          id               uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id      uuid NOT NULL,
          coupon_id        uuid NOT NULL,
          payment_id       uuid,
          amount_off_minor bigint,
          currency         char(3),
          created_at       timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_coupon_redemptions PRIMARY KEY (id),
          -- Un negocio canjea un cupón una vez; el límite global vive en `coupons`.
          CONSTRAINT uq_coupon_redemptions_coupon_id_business_id UNIQUE (coupon_id, business_id),
          CONSTRAINT fk_coupon_redemptions_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_coupon_redemptions_coupon_id_coupons FOREIGN KEY (coupon_id)
            REFERENCES coupons(id) ON DELETE RESTRICT,
          CONSTRAINT fk_coupon_redemptions_payment_id_payments FOREIGN KEY (payment_id)
            REFERENCES payments(id) ON DELETE SET NULL
        );

        CREATE TABLE payment_provider_events (
          id                uuid NOT NULL DEFAULT uuid_generate_v7(),
          provider          text NOT NULL,
          event_type        text NOT NULL,
          provider_event_id text NOT NULL,
          payload           jsonb NOT NULL DEFAULT '{}'::jsonb,
          signature_valid   boolean,
          received_at       timestamptz NOT NULL DEFAULT now(),
          processed_at      timestamptz,
          processing_error  text,
          payment_id        uuid,
          CONSTRAINT pk_payment_provider_events PRIMARY KEY (id),
          -- Reprocesar un webhook reenviado no duplica nada.
          CONSTRAINT uq_payment_provider_events_provider_event_id
            UNIQUE (provider, provider_event_id),
          CONSTRAINT fk_payment_provider_events_payment_id_payments FOREIGN KEY (payment_id)
            REFERENCES payments(id) ON DELETE SET NULL
        );
        CREATE INDEX ix_payment_provider_events_sin_procesar
          ON payment_provider_events (received_at) WHERE processed_at IS NULL;
        """
    )


def _cerrar_ciclos() -> None:
    """Los dos ciclos de claves foráneas que no caben en un `CREATE TABLE`."""
    op.execute(
        """
        ALTER TABLE ad_campaigns
          ADD CONSTRAINT fk_ad_campaigns_payment_id_payments
          FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE SET NULL;

        ALTER TABLE bookings
          ADD CONSTRAINT fk_bookings_deposit_payment_id_payments
          FOREIGN KEY (deposit_payment_id) REFERENCES payments(id) ON DELETE SET NULL;
        """
    )


def _notificaciones() -> None:
    op.execute(
        """
        CREATE TABLE notifications (
          id                uuid NOT NULL DEFAULT uuid_generate_v7(),
          -- Derivada del **hecho, no del momento**: 'recordatorio_24h:booking:{id}'. Encolar
          -- dos veces el mismo recordatorio es un conflicto que no inserta, no un segundo
          -- mensaje. Un recordatorio duplicado a las siete de la mañana es una queja.
          idempotency_key   text NOT NULL,
          business_id       uuid,
          recipient_user_id uuid,
          recipient_kind    text NOT NULL,
          channel           text NOT NULL,
          template_key      text NOT NULL,
          locale            text NOT NULL DEFAULT 'es-PA',
          payload           jsonb NOT NULL DEFAULT '{}'::jsonb,
          destination       text,
          status            text NOT NULL DEFAULT 'pendiente',
          scheduled_for     timestamptz NOT NULL,
          expires_at        timestamptz,
          attempts          smallint NOT NULL DEFAULT 0,
          next_attempt_at   timestamptz,
          last_error        text,
          queue             text NOT NULL DEFAULT 'default',
          sent_at           timestamptz,
          created_at        timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_notifications PRIMARY KEY (id),
          CONSTRAINT uq_notifications_idempotency_key UNIQUE (idempotency_key),
          CONSTRAINT fk_notifications_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE CASCADE,
          CONSTRAINT fk_notifications_recipient_user_id_users FOREIGN KEY (recipient_user_id)
            REFERENCES users(id) ON DELETE SET NULL,
          CONSTRAINT ck_notifications_recipient_kind_valido
            CHECK (recipient_kind IN ('cliente','negocio','staff','admin')),
          CONSTRAINT ck_notifications_channel_valido
            CHECK (channel IN ('whatsapp','email','push','sms')),
          CONSTRAINT ck_notifications_status_valido
            CHECK (status IN ('pendiente','enviando','enviada','fallida','descartada')),
          CONSTRAINT ck_notifications_queue_valida
            CHECK (queue IN ('default','programado','pesado'))
        );
        -- Parcial a propósito: la cola crece para siempre y el trabajador solo mira las
        -- pendientes; un índice completo costaría cada vez más para responder lo mismo.
        CREATE INDEX ix_notifications_pendientes ON notifications (scheduled_for)
          WHERE status = 'pendiente';
        CREATE INDEX ix_notifications_business_id ON notifications (business_id);

        CREATE TABLE notification_deliveries (
          id                  uuid NOT NULL DEFAULT uuid_generate_v7(),
          notification_id     uuid NOT NULL,
          provider            text NOT NULL,
          provider_message_id text,
          status              text NOT NULL,
          -- El coste estimado por mensaje es lo que permite decidir, con datos, si el
          -- recordatorio de 24 h vale lo que cuesta.
          cost_minor          bigint,
          currency            char(3),
          raw                 jsonb NOT NULL DEFAULT '{}'::jsonb,
          occurred_at         timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_notification_deliveries PRIMARY KEY (id),
          CONSTRAINT fk_notification_deliveries_notification_id_notifications
            FOREIGN KEY (notification_id) REFERENCES notifications(id) ON DELETE CASCADE
        );
        CREATE INDEX ix_notification_deliveries_notification_id
          ON notification_deliveries (notification_id);

        CREATE TABLE notification_preferences (
          id          uuid NOT NULL DEFAULT uuid_generate_v7(),
          user_id     uuid,
          business_id uuid,
          channel     text NOT NULL,
          category    text NOT NULL,
          enabled     boolean NOT NULL DEFAULT true,
          CONSTRAINT pk_notification_preferences PRIMARY KEY (id),
          CONSTRAINT fk_notification_preferences_user_id_users FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE CASCADE,
          CONSTRAINT fk_notification_preferences_business_id_businesses
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
          CONSTRAINT ck_notification_preferences_tiene_sujeto
            CHECK (user_id IS NOT NULL OR business_id IS NOT NULL),
          CONSTRAINT ck_notification_preferences_channel_valido
            CHECK (channel IN ('whatsapp','email','push','sms'))
        );
        CREATE UNIQUE INDEX uq_notification_preferences_sujeto
          ON notification_preferences (user_id, business_id, channel, category)
          NULLS NOT DISTINCT;
        """
    )


def _back_office() -> None:
    op.execute(
        """
        CREATE TABLE audit_logs (
          id                   uuid NOT NULL DEFAULT uuid_generate_v7(),
          actor_kind           text NOT NULL,
          actor_admin_id       uuid,
          actor_user_id        uuid,
          business_id          uuid,
          action               text NOT NULL,
          entity_type          text,
          entity_id            uuid,
          before               jsonb,
          after                jsonb,
          impersonated_user_id uuid,
          ip_hash              bytea,
          user_agent           text,
          created_at           timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_audit_logs PRIMARY KEY (id),
          CONSTRAINT fk_audit_logs_actor_admin_id_admin_users FOREIGN KEY (actor_admin_id)
            REFERENCES admin_users(id) ON DELETE SET NULL,
          CONSTRAINT fk_audit_logs_actor_user_id_users FOREIGN KEY (actor_user_id)
            REFERENCES users(id) ON DELETE SET NULL,
          CONSTRAINT fk_audit_logs_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE SET NULL,
          CONSTRAINT fk_audit_logs_impersonated_user_id_users
            FOREIGN KEY (impersonated_user_id) REFERENCES users(id) ON DELETE SET NULL,
          CONSTRAINT ck_audit_logs_actor_kind_valido
            CHECK (actor_kind IN ('admin','sistema','negocio','cliente'))
        );
        CREATE INDEX ix_audit_logs_business_id_created_at
          ON audit_logs (business_id, created_at DESC);
        CREATE INDEX ix_audit_logs_entity ON audit_logs (entity_type, entity_id);

        CREATE TABLE feature_flag_overrides (
          business_id uuid NOT NULL,
          key         text NOT NULL,
          enabled     boolean NOT NULL,
          CONSTRAINT pk_feature_flag_overrides PRIMARY KEY (business_id, key),
          CONSTRAINT fk_feature_flag_overrides_business_id_businesses
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
          CONSTRAINT fk_feature_flag_overrides_key_feature_flags FOREIGN KEY (key)
            REFERENCES feature_flags(key) ON DELETE CASCADE
        );
        CREATE INDEX ix_feature_flag_overrides_key ON feature_flag_overrides (key);

        CREATE TABLE moderation_queue (
          id                uuid NOT NULL DEFAULT uuid_generate_v7(),
          entity_type       text NOT NULL,
          entity_id         uuid NOT NULL,
          business_id       uuid,
          reason            text,
          status            text NOT NULL DEFAULT 'pendiente',
          priority          smallint NOT NULL DEFAULT 0,
          assigned_admin_id uuid,
          resolved_at       timestamptz,
          resolution        text,
          created_at        timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_moderation_queue PRIMARY KEY (id),
          CONSTRAINT uq_moderation_queue_entity_type_entity_id UNIQUE (entity_type, entity_id),
          CONSTRAINT fk_moderation_queue_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE CASCADE,
          CONSTRAINT fk_moderation_queue_assigned_admin_id_admin_users
            FOREIGN KEY (assigned_admin_id) REFERENCES admin_users(id) ON DELETE SET NULL,
          CONSTRAINT ck_moderation_queue_status_valido
            CHECK (status IN ('pendiente','en_revision','resuelta','descartada'))
        );
        -- Parcial: la bandeja del moderador solo mira lo que sigue abierto.
        CREATE INDEX ix_moderation_queue_abiertas
          ON moderation_queue (priority DESC, created_at)
          WHERE status IN ('pendiente','en_revision');

        CREATE TABLE idempotency_keys (
          id              uuid NOT NULL DEFAULT uuid_generate_v7(),
          key             text NOT NULL,
          endpoint        text NOT NULL,
          user_id         uuid,
          business_id     uuid,
          -- La misma clave con un cuerpo distinto **no** es un reintento, es un error del
          -- cliente, y responderle con la respuesta anterior sería mentirle.
          request_hash    bytea,
          response_status smallint,
          response_body   jsonb,
          expires_at      timestamptz NOT NULL,
          created_at      timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_idempotency_keys PRIMARY KEY (id),
          CONSTRAINT uq_idempotency_keys_key_endpoint UNIQUE (key, endpoint),
          CONSTRAINT fk_idempotency_keys_user_id_users FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE CASCADE,
          CONSTRAINT fk_idempotency_keys_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE CASCADE
        );
        CREATE INDEX ix_idempotency_keys_expires_at ON idempotency_keys (expires_at);
        """
    )


def _disparadores() -> None:
    for tabla in TABLAS_CON_UPDATED_AT:
        op.execute(
            f"CREATE TRIGGER {tabla}_toca_updated_at BEFORE UPDATE ON {tabla} "
            f"FOR EACH ROW EXECUTE FUNCTION tocar_updated_at()"
        )


def _seguridad_por_fila() -> None:
    for tabla in TABLAS_CON_TENANT:
        op.execute(f"ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabla} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {tabla}_tenant ON {tabla}
              FOR ALL TO agenda_api
              USING      (business_id = app_negocio_actual())
              WITH CHECK (business_id = app_negocio_actual());
            """
        )
        op.execute(
            f"CREATE POLICY {tabla}_admin ON {tabla} "
            f"FOR ALL TO agenda_admin USING (true) WITH CHECK (true)"
        )

    # `notifications` e `idempotency_keys` llevan `business_id` **nulable**: los OTP y los
    # avisos de plataforma no son de ningún negocio. Se comparan con `IS NOT DISTINCT FROM` y
    # no con `=` por una razón práctica: con un tenant fijado el resultado es idéntico —las
    # filas de plataforma quedan invisibles, que es lo que pide §13—, pero el trabajador de la
    # cola, que no tiene sesión de usuario y por tanto no fija tenant, sí puede ver y mandar
    # justamente esas filas de plataforma. Con `=` a secas el OTP no saldría nunca.
    for tabla in ("notifications", "idempotency_keys"):
        op.execute(f"ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabla} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {tabla}_tenant ON {tabla}
              FOR ALL TO agenda_api
              USING      (business_id IS NOT DISTINCT FROM app_negocio_actual())
              WITH CHECK (business_id IS NOT DISTINCT FROM app_negocio_actual());
            """
        )
        op.execute(
            f"CREATE POLICY {tabla}_admin ON {tabla} "
            f"FOR ALL TO agenda_admin USING (true) WITH CHECK (true)"
        )

    # `notification_deliveries` no tiene `business_id` y hereda el aislamiento de su
    # notificación: el intento de envío pertenece a quien pertenece el mensaje.
    op.execute(
        """
        ALTER TABLE notification_deliveries ENABLE ROW LEVEL SECURITY;
        ALTER TABLE notification_deliveries FORCE ROW LEVEL SECURITY;
        CREATE POLICY notification_deliveries_tenant ON notification_deliveries
          FOR ALL TO agenda_api
          USING (EXISTS (
            SELECT 1 FROM notifications n
             WHERE n.id = notification_deliveries.notification_id
               AND n.business_id IS NOT DISTINCT FROM app_negocio_actual()))
          WITH CHECK (EXISTS (
            SELECT 1 FROM notifications n
             WHERE n.id = notification_deliveries.notification_id
               AND n.business_id IS NOT DISTINCT FROM app_negocio_actual()));
        CREATE POLICY notification_deliveries_admin ON notification_deliveries
          FOR ALL TO agenda_admin USING (true) WITH CHECK (true);
        """
    )

    # `audit_logs` y `moderation_queue` llevan `business_id` y **no** son del negocio: son del
    # equipo interno. Se les activa RLS igualmente —para que la prueba de catálogo de ADR-0002
    # no tenga que excluirlas— y se cierran: la única política es la del back-office, y
    # `agenda_api` ni siquiera tiene permiso sobre ellas. Una de las funciones de la auditoría
    # es registrar lo que hace el equipo interno; si el propio equipo pudiera filtrarla desde
    # la API pública, no sería auditoría.
    for tabla in ("audit_logs", "moderation_queue"):
        op.execute(f"ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tabla} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {tabla}_admin ON {tabla} "
            f"FOR ALL TO agenda_admin USING (true) WITH CHECK (true)"
        )

    # `payment_provider_events` no lleva aislamiento porque un webhook **llega antes de que
    # sepamos de qué negocio es**; se procesa con el rol de sistema y de ahí sale el
    # `payment_id`. `notification_preferences` es de la persona, no del salón.


def _permisos() -> None:
    escritura_api = (
        "subscriptions",
        "subscription_events",
        "ad_campaigns",
        "ad_metrics_daily",
        "coupon_redemptions",
        "payment_methods",
        "payments",
        "invoices",
        "notifications",
        "notification_deliveries",
        "notification_preferences",
        "idempotency_keys",
        "payment_provider_events",
    )
    for tabla in escritura_api:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tabla} TO agenda_api")

    op.execute("GRANT SELECT ON feature_flag_overrides TO agenda_api")

    # El back-office llega a todo lo de este bloque, con su propio rol y auditado.
    for tabla in (*escritura_api, "feature_flag_overrides", "audit_logs", "moderation_queue"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tabla} TO agenda_admin")

    # El rol público no toca **nada** de dinero, de notificaciones ni de back-office. No hay
    # un solo GRANT a `agenda_publico` en esta revisión, y es a propósito.


def downgrade() -> None:
    op.execute("ALTER TABLE bookings DROP CONSTRAINT IF EXISTS fk_bookings_deposit_payment_id_payments")
    op.execute("ALTER TABLE ad_campaigns DROP CONSTRAINT IF EXISTS fk_ad_campaigns_payment_id_payments")
    op.execute(
        """
        DROP TABLE IF EXISTS idempotency_keys, moderation_queue, feature_flag_overrides,
          audit_logs, notification_preferences, notification_deliveries, notifications,
          payment_provider_events, coupon_redemptions, invoices, payments, payment_methods,
          ad_metrics_daily, ad_campaigns, subscription_events, subscriptions CASCADE;
        """
    )
