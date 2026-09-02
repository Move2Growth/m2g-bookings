"""Extensiones, funciones y catálogos globales.

Revision ID: 0001_extensiones
Revises:
Create Date: 2026-09-01

Primera de tres revisiones que forman la migración inicial. Está escrita **a mano y en SQL
literal**, no autogenerada, porque casi nada de lo que hay aquí lo sabe producir el
autogenerador de Alembic: extensiones, funciones, columnas generadas, restricciones de
exclusión, políticas de seguridad por fila, disparadores e índices por expresión.

Esta revisión trae lo que no depende de ningún negocio: las tres extensiones, las funciones de
las que dependen las columnas generadas y las políticas, los catálogos globales que administra
M2G y la identidad de las personas. La partición en tres es por legibilidad; la cadena corre
entera de un tirón desde una base vacía, que es el criterio de ADR-0014.
"""

from __future__ import annotations

from alembic import op

revision = "0001_extensiones"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    _extensiones_y_funciones()
    _catalogos_globales()
    _identidad()
    _permisos()


def _extensiones_y_funciones() -> None:
    # Las tres son obligatorias desde el primer día: PostGIS por ADR-0005, btree_gist porque
    # sin ella la restricción de exclusión no puede mezclar `staff_id WITH =` con un rango
    # (ADR-0004), y pgcrypto para hashes y bytes aleatorios.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # PostgreSQL 16 no trae uuidv7() nativo. Se instala para que el DEFAULT exista aunque
    # alguna ruta inserte sin generar el identificador en la aplicación.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION uuid_generate_v7() RETURNS uuid
        LANGUAGE plpgsql VOLATILE PARALLEL SAFE AS $$
        BEGIN
          -- Se toma un UUID v4 aleatorio, se le sobreescriben los 48 primeros bits con la
          -- marca de tiempo en milisegundos y se corrige el nibble de versión de 4 a 7.
          RETURN encode(
            set_bit(
              set_bit(
                overlay(
                  uuid_send(gen_random_uuid())
                  PLACING substring(
                    int8send(floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint) FROM 3
                  )
                  FROM 1 FOR 6
                ),
                52, 1),
              53, 1),
            'hex')::uuid;
        END $$;
        """
    )

    # Existe por una razón concreta: `timestamptz + interval` está marcado STABLE (un
    # intervalo con días o meses depende del huso) y una columna generada exige IMMUTABLE.
    # Con `secs =>` el intervalo no tiene componente de día ni de mes, así que la suma es
    # aritmética pura sobre el instante y sí es inmutable de verdad. Esto es lo que permite
    # que blocked_from y blocked_to sean columnas generadas y persistidas por la base, como
    # manda ADR-0004, y no calculadas por la aplicación.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION desplazar_minutos(t timestamptz, minutos integer)
        RETURNS timestamptz
        LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS $$
          SELECT t + make_interval(secs => minutos * 60);
        $$;
        """
    )

    # Devuelve NULL si nadie fijó el tenant, y una política que compara contra NULL no
    # devuelve filas: el fallo es **cerrado**, no abierto.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_negocio_actual() RETURNS uuid
        LANGUAGE sql STABLE PARALLEL SAFE AS $$
          SELECT nullif(current_setting('app.current_business_id', true), '')::uuid;
        $$;
        """
    )

    # Mantiene `updated_at` sin depender de que la aplicación se acuerde. Los trabajos en
    # segundo plano y el propio seed escriben, y el único reloj que arbitra es el de la base.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION tocar_updated_at() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          NEW.updated_at = now();
          RETURN NEW;
        END $$;
        """
    )


def _catalogos_globales() -> None:
    # --- Zonas ------------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE zones (
          id               uuid NOT NULL DEFAULT uuid_generate_v7(),
          parent_id        uuid,
          level            text NOT NULL,
          name             text NOT NULL,
          slug             text NOT NULL,
          path             text NOT NULL,
          country_code     char(2) NOT NULL DEFAULT 'PA',
          centroid         geography(Point,4326),
          boundary         geography(MultiPolygon,4326),
          businesses_count integer NOT NULL DEFAULT 0,
          active           boolean NOT NULL DEFAULT true,
          CONSTRAINT pk_zones PRIMARY KEY (id),
          CONSTRAINT fk_zones_parent_id_zones FOREIGN KEY (parent_id)
            REFERENCES zones(id) ON DELETE RESTRICT,
          CONSTRAINT ck_zones_level_valido
            CHECK (level IN ('provincia','distrito','corregimiento','barrio'))
        );
        """
    )
    # `coalesce` con un UUID imposible porque en SQL NULL no es igual a NULL: sin esto, dos
    # zonas raíz con el mismo slug pasarían el único sin que nadie se enterara.
    op.execute(
        "CREATE UNIQUE INDEX uq_zones_slug_por_padre ON zones "
        "(coalesce(parent_id, '00000000-0000-0000-0000-000000000000'::uuid), slug)"
    )
    # `text_pattern_ops` es lo que hace que 'panama/panama/%' use el índice en vez de recorrer
    # la tabla: el operador LIKE con prefijo no usa el índice btree por defecto con locales
    # distintas de C.
    op.execute("CREATE INDEX ix_zones_path ON zones (path text_pattern_ops)")
    op.execute("CREATE INDEX ix_zones_boundary_gist ON zones USING gist (boundary)")
    op.execute("CREATE INDEX ix_zones_parent_id ON zones (parent_id)")

    # --- Categorías de servicio -------------------------------------------------------
    op.execute(
        """
        CREATE TABLE service_categories (
          id              uuid NOT NULL DEFAULT uuid_generate_v7(),
          parent_id       uuid,
          slug            text NOT NULL,
          name            text NOT NULL,
          position        smallint NOT NULL DEFAULT 0,
          active          boolean NOT NULL DEFAULT true,
          icon_key        text,
          seo_title       text,
          seo_description text,
          CONSTRAINT pk_service_categories PRIMARY KEY (id),
          CONSTRAINT fk_service_categories_parent_id_service_categories FOREIGN KEY (parent_id)
            REFERENCES service_categories(id) ON DELETE RESTRICT
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_service_categories_slug_por_padre ON service_categories "
        "(coalesce(parent_id, '00000000-0000-0000-0000-000000000000'::uuid), slug)"
    )
    op.execute("CREATE INDEX ix_service_categories_parent_id ON service_categories (parent_id)")

    # --- Atributos filtrables ---------------------------------------------------------
    op.execute(
        """
        CREATE TABLE attributes (
          id         uuid NOT NULL DEFAULT uuid_generate_v7(),
          slug       text NOT NULL,
          name       text NOT NULL,
          group_key  text NOT NULL,
          input_kind text NOT NULL,
          position   smallint NOT NULL DEFAULT 0,
          active     boolean NOT NULL DEFAULT true,
          CONSTRAINT pk_attributes PRIMARY KEY (id),
          CONSTRAINT uq_attributes_slug UNIQUE (slug),
          CONSTRAINT ck_attributes_input_kind_valido
            CHECK (input_kind IN ('unico','multiple','booleano'))
        );

        CREATE TABLE attribute_values (
          id           uuid NOT NULL DEFAULT uuid_generate_v7(),
          attribute_id uuid NOT NULL,
          slug         text NOT NULL,
          name         text NOT NULL,
          position     smallint NOT NULL DEFAULT 0,
          active       boolean NOT NULL DEFAULT true,
          CONSTRAINT pk_attribute_values PRIMARY KEY (id),
          CONSTRAINT fk_attribute_values_attribute_id_attributes FOREIGN KEY (attribute_id)
            REFERENCES attributes(id) ON DELETE CASCADE,
          CONSTRAINT uq_attribute_values_attribute_id_slug UNIQUE (attribute_id, slug)
        );
        """
    )

    # --- Feriados, geocoding y ajustes de plataforma ----------------------------------
    op.execute(
        """
        CREATE TABLE holidays (
          id           uuid NOT NULL DEFAULT uuid_generate_v7(),
          country_code char(2) NOT NULL DEFAULT 'PA',
          date         date NOT NULL,
          name         text NOT NULL,
          source       text,
          CONSTRAINT pk_holidays PRIMARY KEY (id),
          CONSTRAINT uq_holidays_country_code_date UNIQUE (country_code, date)
        );

        CREATE TABLE geocoding_cache (
          id               uuid NOT NULL DEFAULT uuid_generate_v7(),
          normalized_query text NOT NULL,
          provider         text,
          geo              geography(Point,4326),
          zone_id          uuid,
          raw              jsonb NOT NULL DEFAULT '{}'::jsonb,
          hits             integer NOT NULL DEFAULT 0,
          expires_at       timestamptz,
          created_at       timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_geocoding_cache PRIMARY KEY (id),
          CONSTRAINT uq_geocoding_cache_normalized_query UNIQUE (normalized_query),
          CONSTRAINT fk_geocoding_cache_zone_id_zones FOREIGN KEY (zone_id)
            REFERENCES zones(id) ON DELETE SET NULL
        );
        """
    )

    # --- Identidad del equipo interno --------------------------------------------------
    # Va antes que el resto de catálogos porque `plans`, `coupons`, `ranking_weights`,
    # `feature_flags` y `platform_settings` guardan quién los tocó.
    op.execute(
        """
        CREATE TABLE admin_users (
          id            uuid NOT NULL DEFAULT uuid_generate_v7(),
          email         text NOT NULL,
          full_name     text NOT NULL,
          password_hash text NOT NULL,
          totp_secret   bytea NOT NULL,
          totp_enabled  boolean NOT NULL DEFAULT true,
          role          text NOT NULL,
          status        text NOT NULL DEFAULT 'activo',
          last_login_at timestamptz,
          created_at    timestamptz NOT NULL DEFAULT now(),
          updated_at    timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_admin_users PRIMARY KEY (id),
          CONSTRAINT ck_admin_users_role_valido
            CHECK (role IN ('superadmin','soporte','finanzas','moderacion'))
        );
        CREATE UNIQUE INDEX uq_admin_users_email_lower ON admin_users (lower(email));

        CREATE TABLE admin_sessions (
          id                 uuid NOT NULL DEFAULT uuid_generate_v7(),
          admin_user_id      uuid NOT NULL,
          family_id          uuid NOT NULL,
          refresh_token_hash bytea NOT NULL,
          ip_hash            bytea,
          user_agent         text,
          issued_at          timestamptz NOT NULL,
          expires_at         timestamptz NOT NULL,
          rotated_at         timestamptz,
          revoked_at         timestamptz,
          revoked_reason     text,
          created_at         timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_admin_sessions PRIMARY KEY (id),
          CONSTRAINT uq_admin_sessions_refresh_token_hash UNIQUE (refresh_token_hash),
          CONSTRAINT fk_admin_sessions_admin_user_id_admin_users FOREIGN KEY (admin_user_id)
            REFERENCES admin_users(id) ON DELETE CASCADE
        );
        CREATE INDEX ix_admin_sessions_admin_user_id ON admin_sessions (admin_user_id);
        """
    )

    # --- Planes, publicidad y cupones (catálogo global) --------------------------------
    op.execute(
        """
        CREATE TABLE plans (
          id                  uuid NOT NULL DEFAULT uuid_generate_v7(),
          code                text NOT NULL,
          version             integer NOT NULL,
          name                text NOT NULL,
          price_minor         bigint NOT NULL,
          currency            char(3) NOT NULL DEFAULT 'USD',
          period              text NOT NULL,
          trial_days          smallint NOT NULL DEFAULT 0,
          limits              jsonb NOT NULL DEFAULT '{}'::jsonb,
          features            jsonb NOT NULL DEFAULT '{}'::jsonb,
          effective_from      timestamptz NOT NULL,
          effective_to        timestamptz,
          active              boolean NOT NULL DEFAULT true,
          created_by_admin_id uuid,
          created_at          timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_plans PRIMARY KEY (id),
          CONSTRAINT uq_plans_code_version UNIQUE (code, version),
          CONSTRAINT fk_plans_created_by_admin_id_admin_users FOREIGN KEY (created_by_admin_id)
            REFERENCES admin_users(id) ON DELETE SET NULL,
          CONSTRAINT ck_plans_period_valido CHECK (period IN ('mensual','anual')),
          CONSTRAINT ck_plans_precio_no_negativo CHECK (price_minor >= 0)
        );

        CREATE TABLE ad_products (
          id             uuid NOT NULL DEFAULT uuid_generate_v7(),
          code           text NOT NULL,
          name           text NOT NULL,
          placement      text NOT NULL,
          duration_days  smallint NOT NULL,
          price_minor    bigint NOT NULL,
          currency       char(3) NOT NULL DEFAULT 'USD',
          slots          smallint NOT NULL DEFAULT 3,
          active         boolean NOT NULL DEFAULT true,
          effective_from timestamptz NOT NULL,
          effective_to   timestamptz,
          CONSTRAINT pk_ad_products PRIMARY KEY (id),
          CONSTRAINT uq_ad_products_code UNIQUE (code),
          -- En v1 solo `categoria_zona`; el home y el push a cercanos son ADS-6 y v2.
          CONSTRAINT ck_ad_products_placement_valido CHECK (placement IN ('categoria_zona'))
        );

        CREATE TABLE ad_inventory (
          id                  uuid NOT NULL DEFAULT uuid_generate_v7(),
          ad_product_id       uuid NOT NULL,
          service_category_id uuid NOT NULL,
          zone_id             uuid NOT NULL,
          period_start        date NOT NULL,
          period_end          date NOT NULL,
          slots_total         smallint NOT NULL,
          slots_taken         smallint NOT NULL DEFAULT 0,
          CONSTRAINT pk_ad_inventory PRIMARY KEY (id),
          CONSTRAINT uq_ad_inventory_producto_categoria_zona_periodo
            UNIQUE (ad_product_id, service_category_id, zone_id, period_start),
          CONSTRAINT fk_ad_inventory_ad_product_id_ad_products FOREIGN KEY (ad_product_id)
            REFERENCES ad_products(id) ON DELETE RESTRICT,
          CONSTRAINT fk_ad_inventory_service_category_id_service_categories
            FOREIGN KEY (service_category_id)
            REFERENCES service_categories(id) ON DELETE RESTRICT,
          CONSTRAINT fk_ad_inventory_zone_id_zones FOREIGN KEY (zone_id)
            REFERENCES zones(id) ON DELETE RESTRICT,
          -- Esto es lo que hace que «inventario limitado» (ADS-2) sea una verdad de la base
          -- de datos y no una carrera entre dos negocios comprando el último slot a la vez.
          CONSTRAINT ck_ad_inventory_slots_disponibles CHECK (slots_taken <= slots_total),
          CONSTRAINT ck_ad_inventory_slots_no_negativos CHECK (slots_taken >= 0),
          CONSTRAINT ck_ad_inventory_periodo_valido CHECK (period_end >= period_start)
        );

        CREATE TABLE coupons (
          id                  uuid NOT NULL DEFAULT uuid_generate_v7(),
          code                text NOT NULL,
          description         text,
          kind                text NOT NULL,
          percent_off         smallint,
          amount_off_minor    bigint,
          currency            char(3),
          applies_to          text NOT NULL,
          max_redemptions     integer,
          redemptions_count   integer NOT NULL DEFAULT 0,
          valid_from          timestamptz NOT NULL,
          valid_until         timestamptz,
          active              boolean NOT NULL DEFAULT true,
          created_by_admin_id uuid,
          created_at          timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_coupons PRIMARY KEY (id),
          CONSTRAINT uq_coupons_code UNIQUE (code),
          CONSTRAINT fk_coupons_created_by_admin_id_admin_users FOREIGN KEY (created_by_admin_id)
            REFERENCES admin_users(id) ON DELETE SET NULL,
          CONSTRAINT ck_coupons_kind_valido CHECK (kind IN ('porcentaje','importe')),
          CONSTRAINT ck_coupons_applies_to_valido
            CHECK (applies_to IN ('suscripcion','ads','ambos')),
          CONSTRAINT ck_coupons_descuento_coherente CHECK (
            (kind = 'porcentaje' AND percent_off IS NOT NULL)
            OR (kind = 'importe' AND amount_off_minor IS NOT NULL AND currency IS NOT NULL)
          ),
          CONSTRAINT ck_coupons_canjes_dentro_del_limite
            CHECK (max_redemptions IS NULL OR redemptions_count <= max_redemptions)
        );
        """
    )

    # --- Pesos del ranking -------------------------------------------------------------
    # No hay ni un número de ranking en el código (ADR-0009, ADM-4): todos viven aquí.
    op.execute(
        """
        CREATE TABLE ranking_weights (
          id                   uuid NOT NULL DEFAULT uuid_generate_v7(),
          version              integer NOT NULL,
          effective_from       timestamptz NOT NULL,
          effective_to         timestamptz,
          w_distancia          numeric NOT NULL,
          w_rating             numeric NOT NULL,
          w_reservas_recientes numeric NOT NULL,
          w_tasa_completado    numeric NOT NULL,
          w_completitud        numeric NOT NULL,
          w_actividad          numeric NOT NULL,
          w_boost_nuevo        numeric NOT NULL,
          radius_km            numeric NOT NULL,
          decay_km             numeric NOT NULL,
          recent_days          smallint NOT NULL,
          recent_cap           integer NOT NULL,
          activity_days        smallint NOT NULL,
          boost_days           smallint NOT NULL,
          bayes_m              numeric NOT NULL,
          bayes_c              integer NOT NULL,
          sponsored_per_page   smallint NOT NULL DEFAULT 2,
          page_size            smallint NOT NULL DEFAULT 10,
          notes                text,
          created_by_admin_id  uuid,
          created_at           timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_ranking_weights PRIMARY KEY (id),
          CONSTRAINT uq_ranking_weights_version UNIQUE (version),
          CONSTRAINT fk_ranking_weights_created_by_admin_id_admin_users
            FOREIGN KEY (created_by_admin_id) REFERENCES admin_users(id) ON DELETE SET NULL
        );
        """
    )
    # Hay **exactamente una** versión vigente. Se indexa la expresión y no la columna porque
    # en un índice único dos NULL se consideran distintos: con `(effective_to)` a secas
    # entrarían dos filas vigentes y el ranking cambiaría según a cuál mirara la consulta.
    op.execute(
        "CREATE UNIQUE INDEX uq_ranking_weights_vigente ON ranking_weights "
        "((effective_to IS NULL)) WHERE effective_to IS NULL"
    )

    # --- Plantillas, interruptores y ajustes -------------------------------------------
    op.execute(
        """
        CREATE TABLE notification_templates (
          id                     uuid NOT NULL DEFAULT uuid_generate_v7(),
          key                    text NOT NULL,
          channel                text NOT NULL,
          locale                 text NOT NULL,
          version                integer NOT NULL,
          provider_template_name text,
          provider_status        text NOT NULL DEFAULT 'borrador',
          subject                text,
          body                   text NOT NULL,
          variables              jsonb NOT NULL DEFAULT '{}'::jsonb,
          active                 boolean NOT NULL DEFAULT true,
          CONSTRAINT pk_notification_templates PRIMARY KEY (id),
          CONSTRAINT uq_notification_templates_clave UNIQUE (key, channel, locale, version),
          CONSTRAINT ck_notification_templates_channel_valido
            CHECK (channel IN ('whatsapp','email','push','sms')),
          -- Las plantillas de WhatsApp las aprueba Meta, no nosotros: hay que poder ver de un
          -- vistazo cuál está aprobada y cuál no.
          CONSTRAINT ck_notification_templates_provider_status_valido
            CHECK (provider_status IN ('borrador','pendiente','aprobada','rechazada'))
        );

        CREATE TABLE feature_flags (
          key                 text NOT NULL,
          description         text,
          enabled_global      boolean NOT NULL DEFAULT false,
          rollout             jsonb NOT NULL DEFAULT '{}'::jsonb,
          updated_by_admin_id uuid,
          updated_at          timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_feature_flags PRIMARY KEY (key),
          CONSTRAINT fk_feature_flags_updated_by_admin_id_admin_users
            FOREIGN KEY (updated_by_admin_id) REFERENCES admin_users(id) ON DELETE SET NULL
        );

        CREATE TABLE platform_settings (
          key                 text NOT NULL,
          value               jsonb NOT NULL,
          updated_by_admin_id uuid,
          updated_at          timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_platform_settings PRIMARY KEY (key),
          CONSTRAINT fk_platform_settings_updated_by_admin_id_admin_users
            FOREIGN KEY (updated_by_admin_id) REFERENCES admin_users(id) ON DELETE SET NULL
        );
        """
    )


def _identidad() -> None:
    op.execute(
        """
        CREATE TABLE users (
          id                uuid NOT NULL DEFAULT uuid_generate_v7(),
          phone_e164        text NOT NULL,
          phone_verified_at timestamptz,
          email             text,
          email_verified_at timestamptz,
          full_name         text NOT NULL,
          avatar_key        text,
          locale            text NOT NULL DEFAULT 'es-PA',
          status            text NOT NULL DEFAULT 'activo',
          anonymized_at     timestamptz,
          created_at        timestamptz NOT NULL DEFAULT now(),
          updated_at        timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_users PRIMARY KEY (id),
          -- El teléfono se guarda siempre normalizado a E.164 y esa normalización ocurre en
          -- un solo sitio: dos formatos del mismo número son dos cuentas, y el día que pase
          -- el cliente jura que ya tenía cuenta y tiene razón.
          CONSTRAINT uq_users_phone_e164 UNIQUE (phone_e164),
          CONSTRAINT ck_users_status_valido CHECK (status IN ('activo','bloqueado','eliminado'))
        );
        CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email))
          WHERE email IS NOT NULL;

        CREATE TABLE auth_identities (
          id                uuid NOT NULL DEFAULT uuid_generate_v7(),
          user_id           uuid NOT NULL,
          provider          text NOT NULL,
          subject           text NOT NULL,
          email_at_provider text,
          email_verified    boolean NOT NULL DEFAULT false,
          created_at        timestamptz NOT NULL DEFAULT now(),
          last_used_at      timestamptz,
          CONSTRAINT pk_auth_identities PRIMARY KEY (id),
          CONSTRAINT fk_auth_identities_user_id_users FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE CASCADE,
          CONSTRAINT uq_auth_identities_provider_subject UNIQUE (provider, subject),
          CONSTRAINT uq_auth_identities_user_id_provider UNIQUE (user_id, provider),
          CONSTRAINT ck_auth_identities_provider_valido
            CHECK (provider IN ('telefono','google','apple'))
        );

        CREATE TABLE otp_codes (
          id              uuid NOT NULL DEFAULT uuid_generate_v7(),
          destination     text NOT NULL,
          channel         text NOT NULL,
          purpose         text NOT NULL,
          code_hash       bytea NOT NULL,
          attempts        smallint NOT NULL DEFAULT 0,
          max_attempts    smallint NOT NULL DEFAULT 5,
          request_ip_hash bytea,
          expires_at      timestamptz NOT NULL,
          consumed_at     timestamptz,
          invalidated_at  timestamptz,
          created_at      timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_otp_codes PRIMARY KEY (id),
          CONSTRAINT ck_otp_codes_channel_valido CHECK (channel IN ('whatsapp','sms','email')),
          CONSTRAINT ck_otp_codes_purpose_valido
            CHECK (purpose IN ('registro','login','verificacion_telefono','cambio_telefono'))
        );
        -- Como mucho **un** código vivo por destino y finalidad: emitir uno nuevo invalida el
        -- anterior. Es seguridad y control de gasto a la vez; cada WhatsApp se paga.
        CREATE UNIQUE INDEX uq_otp_codes_vivo ON otp_codes (destination, purpose)
          WHERE consumed_at IS NULL AND invalidated_at IS NULL;

        CREATE TABLE user_consents (
          id         uuid NOT NULL DEFAULT uuid_generate_v7(),
          user_id    uuid NOT NULL,
          kind       text NOT NULL,
          version    text NOT NULL,
          granted    boolean NOT NULL,
          granted_at timestamptz NOT NULL,
          revoked_at timestamptz,
          ip_hash    bytea,
          user_agent text,
          created_at timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_user_consents PRIMARY KEY (id),
          CONSTRAINT fk_user_consents_user_id_users FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE RESTRICT,
          CONSTRAINT ck_user_consents_kind_valido CHECK (
            kind IN ('terminos_cliente','terminos_negocio','privacidad','marketing','whatsapp')
          )
        );
        CREATE INDEX ix_user_consents_user_id_kind ON user_consents (user_id, kind);

        CREATE TABLE privacy_requests (
          id           uuid NOT NULL DEFAULT uuid_generate_v7(),
          user_id      uuid NOT NULL,
          kind         text NOT NULL,
          status       text NOT NULL,
          requested_at timestamptz NOT NULL,
          grace_until  timestamptz,
          executed_at  timestamptz,
          artifact_key text,
          notes        text,
          created_at   timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_privacy_requests PRIMARY KEY (id),
          CONSTRAINT fk_privacy_requests_user_id_users FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE RESTRICT,
          CONSTRAINT ck_privacy_requests_kind_valido
            CHECK (kind IN ('exportacion','rectificacion','borrado')),
          CONSTRAINT ck_privacy_requests_status_valido
            CHECK (status IN ('recibida','en_gracia','ejecutada','cancelada','rechazada'))
        );
        CREATE INDEX ix_privacy_requests_user_id ON privacy_requests (user_id);

        CREATE TABLE client_profiles (
          user_id          uuid NOT NULL,
          birthdate        date,
          default_zone_id  uuid,
          marketing_opt_in boolean NOT NULL DEFAULT false,
          created_at       timestamptz NOT NULL DEFAULT now(),
          updated_at       timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_client_profiles PRIMARY KEY (user_id),
          CONSTRAINT fk_client_profiles_user_id_users FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE CASCADE,
          CONSTRAINT fk_client_profiles_default_zone_id_zones FOREIGN KEY (default_zone_id)
            REFERENCES zones(id) ON DELETE SET NULL
        );
        """
    )

    for tabla in ("admin_users", "users", "client_profiles"):
        op.execute(
            f"CREATE TRIGGER {tabla}_toca_updated_at BEFORE UPDATE ON {tabla} "
            f"FOR EACH ROW EXECUTE FUNCTION tocar_updated_at()"
        )


def _permisos() -> None:
    """Permisos de esta tanda.

    Las tablas de catálogo global son **de solo lectura** para la API y para el marketplace:
    la taxonomía la administra M2G desde el back-office, no un negocio desde un endpoint.
    """
    globales = (
        "zones",
        "service_categories",
        "attributes",
        "attribute_values",
        "holidays",
        "plans",
        "ad_products",
        "ad_inventory",
        "coupons",
        "ranking_weights",
        "notification_templates",
        "feature_flags",
        "platform_settings",
    )
    for tabla in globales:
        op.execute(f"GRANT SELECT ON {tabla} TO agenda_api, agenda_publico")
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tabla} TO agenda_admin")

    # `ad_inventory.slots_taken` sí lo mueve la API: es el contador que se incrementa en la
    # misma transacción en la que el pago de una campaña pasa a `pagado`.
    op.execute("GRANT UPDATE ON ad_inventory TO agenda_api")
    op.execute("GRANT UPDATE ON coupons TO agenda_api")
    op.execute("GRANT UPDATE ON zones TO agenda_api")  # `businesses_count` cacheado

    # Identidad: la API escribe; el marketplace **no ve nada** de esto.
    for tabla in (
        "users",
        "auth_identities",
        "otp_codes",
        "user_consents",
        "privacy_requests",
        "client_profiles",
        "geocoding_cache",
    ):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tabla} TO agenda_api, agenda_admin")

    # El back-office tiene sus propias tablas y la API no las toca en absoluto.
    for tabla in ("admin_users", "admin_sessions"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tabla} TO agenda_admin")


def downgrade() -> None:
    # Se dejan caer en el orden inverso al de creación. `CASCADE` en las funciones no hace
    # falta: al llegar aquí ya no queda ninguna tabla que dependa de ellas.
    op.execute(
        """
        DROP TABLE IF EXISTS client_profiles, privacy_requests, user_consents, otp_codes,
          auth_identities, users, platform_settings, feature_flags, notification_templates,
          ranking_weights, coupons, ad_inventory, ad_products, plans, admin_sessions,
          admin_users, geocoding_cache, holidays, attribute_values, attributes,
          service_categories, zones CASCADE;
        """
    )
    op.execute("DROP FUNCTION IF EXISTS tocar_updated_at()")
    op.execute("DROP FUNCTION IF EXISTS app_negocio_actual()")
    op.execute("DROP FUNCTION IF EXISTS desplazar_minutos(timestamptz, integer)")
    op.execute("DROP FUNCTION IF EXISTS uuid_generate_v7()")
