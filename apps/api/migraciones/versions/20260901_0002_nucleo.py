"""Núcleo: negocio, equipo, catálogo, clientes, reservas, ocupación y reviews.

Revision ID: 0002_nucleo
Revises: 0001_extensiones
Create Date: 2026-09-01

Segunda de tres revisiones de la migración inicial. Aquí viven las dos garantías del proyecto
que **son de la base de datos y no del código**:

* El **aislamiento entre negocios** (ADR-0002): cada tabla con `business_id` lleva
  `ENABLE` + `FORCE ROW LEVEL SECURITY` y su política contra `app.current_business_id`.
  `FORCE` es tan importante como `ENABLE`: sin él, el dueño de la tabla se salta su propia
  política y basta un despiste de conexión para vaciar la garantía.
* La **imposibilidad de doble reserva** (ADR-0004): la restricción de exclusión de
  `staff_occupancy` sobre las columnas generadas `blocked_from`/`blocked_to`.

La cláusula `WHERE` de esa restricción no se escribe a mano: se deriva de `ESTADOS_ACTIVOS` del
dominio. Si esa lista y la restricción se separaran, el motor y la base dejarían de estar de
acuerdo sobre qué está ocupado, que es la peor discrepancia posible.
"""

from __future__ import annotations

from alembic import op

from agenda.dominio.reservas import ESTADOS_ACTIVOS, EstadoReserva

revision = "0002_nucleo"
down_revision = "0001_extensiones"
branch_labels = None
depends_on = None

#: `'pendiente', 'confirmada'` — exactamente los estados que ocupan agenda.
_ESTADOS_QUE_OCUPAN = ", ".join(
    f"'{estado.value}'" for estado in EstadoReserva if estado in ESTADOS_ACTIVOS
)
_ESTADOS_RESERVA = ", ".join(f"'{estado.value}'" for estado in EstadoReserva)

#: Tablas de este bloque que son **propiedad de un negocio**: llevan `business_id` y por tanto
#: política de seguridad por fila. La prueba de catálogo de ADR-0002 recorre `pg_class` y falla
#: si aparece una tabla con `business_id` y sin RLS; esta lista es lo que hace que no aparezca.
TABLAS_CON_TENANT = (
    "memberships",
    "locations",
    "business_hours",
    "business_settings",
    "business_media",
    "business_categories",
    "business_attributes",
    "staff_profiles",
    "staff_hours",
    "staff_services",
    "time_block_rules",
    "services",
    "service_variants",
    "business_clients",
    "bookings",
    "booking_items",
    "staff_occupancy",
    "booking_events",
    "reviews",
    "review_media",
    "review_replies",
    "review_reports",
    "business_rating_stats",
    "business_ranking_signals",
    "listing_impressions_daily",
    "listing_clicks_daily",
)

#: Tablas cuyo `updated_at` mantiene la base y no la aplicación. Los trabajos en segundo plano
#: y el seed también escriben, y el reloj que importa es uno solo.
TABLAS_CON_UPDATED_AT = (
    "businesses",
    "locations",
    "business_hours",
    "business_settings",
    "business_media",
    "memberships",
    "staff_profiles",
    "staff_hours",
    "services",
    "time_block_rules",
    "business_clients",
    "bookings",
    "staff_occupancy",
    "reviews",
    "review_replies",
    "business_rating_stats",
)


def upgrade() -> None:
    _negocio()
    _equipo_y_catalogo()
    _clientes()
    _reservas_y_ocupacion()
    _reviews_y_senales()
    _disparadores()
    _seguridad_por_fila()
    _permisos()


def _negocio() -> None:
    op.execute(
        """
        CREATE TABLE businesses (
          id                   uuid NOT NULL DEFAULT uuid_generate_v7(),
          slug                 text NOT NULL,
          display_name         text NOT NULL,
          legal_name           text,
          description          text,
          timezone             text NOT NULL DEFAULT 'America/Panama',
          country_code         char(2) NOT NULL DEFAULT 'PA',
          currency             char(3) NOT NULL DEFAULT 'USD',
          status               text NOT NULL DEFAULT 'borrador',
          published_at         timestamptz,
          suspended_at         timestamptz,
          suspension_reason    text,
          verified_at          timestamptz,
          whatsapp_phone_e164  text,
          instagram_handle     text,
          website_url          text,
          tax_id               text,
          tax_id_dv            text,
          owner_user_id        uuid NOT NULL,
          profile_completeness smallint NOT NULL DEFAULT 0,
          created_at           timestamptz NOT NULL DEFAULT now(),
          updated_at           timestamptz NOT NULL DEFAULT now(),
          deleted_at           timestamptz,
          CONSTRAINT pk_businesses PRIMARY KEY (id),
          -- El slug es parte de la URL pública y de la bio de Instagram: no se reutiliza.
          CONSTRAINT uq_businesses_slug UNIQUE (slug),
          CONSTRAINT fk_businesses_owner_user_id_users FOREIGN KEY (owner_user_id)
            REFERENCES users(id) ON DELETE RESTRICT,
          CONSTRAINT ck_businesses_status_valido
            CHECK (status IN ('borrador','publicado','suspendido')),
          CONSTRAINT ck_businesses_completitud_rango
            CHECK (profile_completeness BETWEEN 0 AND 100)
        );
        CREATE INDEX ix_businesses_owner_user_id ON businesses (owner_user_id);
        CREATE INDEX ix_businesses_publicados ON businesses (status)
          WHERE status = 'publicado' AND deleted_at IS NULL;

        CREATE TABLE locations (
          id               uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id      uuid NOT NULL,
          label            text NOT NULL DEFAULT 'Principal',
          is_primary       boolean NOT NULL DEFAULT true,
          address_line     text NOT NULL,
          address_details  text,
          zone_id          uuid,
          zone_source      text NOT NULL DEFAULT 'automatica',
          geo              geography(Point,4326) NOT NULL,
          geocode_accuracy text,
          timezone         text,
          created_at       timestamptz NOT NULL DEFAULT now(),
          updated_at       timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_locations PRIMARY KEY (id),
          CONSTRAINT fk_locations_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_locations_zone_id_zones FOREIGN KEY (zone_id)
            REFERENCES zones(id) ON DELETE SET NULL,
          CONSTRAINT ck_locations_zone_source_valido
            CHECK (zone_source IN ('automatica','manual'))
        );
        CREATE INDEX ix_locations_business_id ON locations (business_id);
        CREATE INDEX ix_locations_zone_id ON locations (zone_id);
        """
    )
    # El índice que sostiene «cerca de mí» (MKT-1, MKT-2). `ST_DWithin` lo usa; ordenar por
    # `ST_Distance` sin él es un recorrido secuencial sobre 5.000 negocios.
    op.execute("CREATE INDEX ix_locations_geo_gist ON locations USING gist (geo)")
    # Índice único parcial: hoy hay **exactamente una sede por negocio** (NEG-5). Quitar esta
    # línea es toda la migración de estructura que necesita multi-sede.
    op.execute(
        "CREATE UNIQUE INDEX uq_locations_una_principal ON locations (business_id) "
        "WHERE is_primary"
    )

    op.execute(
        """
        CREATE TABLE business_hours (
          id          uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id uuid NOT NULL,
          location_id uuid,
          weekday     smallint NOT NULL,
          opens_at    time NOT NULL,
          closes_at   time NOT NULL,
          created_at  timestamptz NOT NULL DEFAULT now(),
          updated_at  timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_business_hours PRIMARY KEY (id),
          CONSTRAINT fk_business_hours_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_business_hours_location_id_locations FOREIGN KEY (location_id)
            REFERENCES locations(id) ON DELETE CASCADE,
          -- 0 = lunes … 6 = domingo. Se fija aquí para que nadie lo interprete al revés: es
          -- la clase de detalle que produce un horario desplazado un día.
          CONSTRAINT ck_business_hours_weekday_rango CHECK (weekday BETWEEN 0 AND 6),
          -- Varias filas por día a propósito: la jornada partida (9-13 y 15-19) es la norma
          -- en un salón, no la excepción.
          CONSTRAINT uq_business_hours_business_id_location_id_weekday_opens_at
            UNIQUE (business_id, location_id, weekday, opens_at)
        );
        CREATE INDEX ix_business_hours_business_id ON business_hours (business_id);

        CREATE TABLE business_settings (
          business_id                uuid NOT NULL,
          slot_granularity_min       smallint NOT NULL DEFAULT 15,
          min_lead_time_min          integer  NOT NULL DEFAULT 60,
          max_lead_time_days         smallint NOT NULL DEFAULT 60,
          auto_confirm               boolean  NOT NULL DEFAULT true,
          client_cancel_window_hours smallint NOT NULL DEFAULT 2,
          review_window_days         smallint NOT NULL DEFAULT 14,
          no_show_block_threshold    smallint,
          allow_any_staff            boolean  NOT NULL DEFAULT true,
          daily_digest_enabled       boolean  NOT NULL DEFAULT false,
          deposit_enabled            boolean  NOT NULL DEFAULT false,
          updated_at                 timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_business_settings PRIMARY KEY (business_id),
          CONSTRAINT fk_business_settings_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE CASCADE,
          CONSTRAINT ck_business_settings_granularidad_positiva CHECK (slot_granularity_min > 0)
        );

        CREATE TABLE business_media (
          id                uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id       uuid NOT NULL,
          kind              text NOT NULL,
          storage_key       text NOT NULL,
          width             integer,
          height            integer,
          alt_text          text,
          position          smallint NOT NULL DEFAULT 0,
          moderation_status text NOT NULL DEFAULT 'aprobada',
          created_at        timestamptz NOT NULL DEFAULT now(),
          updated_at        timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_business_media PRIMARY KEY (id),
          CONSTRAINT fk_business_media_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT ck_business_media_kind_valido CHECK (kind IN ('portada','galeria')),
          CONSTRAINT ck_business_media_moderacion_valida
            CHECK (moderation_status IN ('pendiente','aprobada','rechazada'))
        );
        CREATE INDEX ix_business_media_business_id ON business_media (business_id);
        -- Una portada y solo una; el resto es galería ordenada por `position`.
        CREATE UNIQUE INDEX uq_business_media_una_portada ON business_media (business_id)
          WHERE kind = 'portada';

        CREATE TABLE business_categories (
          business_id         uuid NOT NULL,
          service_category_id uuid NOT NULL,
          is_primary          boolean NOT NULL DEFAULT false,
          CONSTRAINT pk_business_categories PRIMARY KEY (business_id, service_category_id),
          CONSTRAINT fk_business_categories_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_business_categories_service_category_id_service_categories
            FOREIGN KEY (service_category_id)
            REFERENCES service_categories(id) ON DELETE RESTRICT
        );
        CREATE INDEX ix_business_categories_service_category_id
          ON business_categories (service_category_id);

        CREATE TABLE business_attributes (
          business_id        uuid NOT NULL,
          attribute_value_id uuid NOT NULL,
          CONSTRAINT pk_business_attributes PRIMARY KEY (business_id, attribute_value_id),
          CONSTRAINT fk_business_attributes_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_business_attributes_attribute_value_id_attribute_values
            FOREIGN KEY (attribute_value_id)
            REFERENCES attribute_values(id) ON DELETE CASCADE
        );
        CREATE INDEX ix_business_attributes_attribute_value_id
          ON business_attributes (attribute_value_id);

        CREATE TABLE memberships (
          id                 uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id        uuid NOT NULL,
          user_id            uuid NOT NULL,
          role               text NOT NULL,
          status             text NOT NULL,
          invited_by_user_id uuid,
          invite_channel     text,
          invite_token_hash  bytea,
          invite_expires_at  timestamptz,
          accepted_at        timestamptz,
          revoked_at         timestamptz,
          created_at         timestamptz NOT NULL DEFAULT now(),
          updated_at         timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_memberships PRIMARY KEY (id),
          -- Una persona tiene **un** rol en un negocio.
          CONSTRAINT uq_memberships_business_id_user_id UNIQUE (business_id, user_id),
          CONSTRAINT fk_memberships_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_memberships_user_id_users FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE CASCADE,
          CONSTRAINT fk_memberships_invited_by_user_id_users FOREIGN KEY (invited_by_user_id)
            REFERENCES users(id) ON DELETE SET NULL,
          -- `recepcion` está desde la primera migración aunque la interfaz no lo ofrezca
          -- (§14.5): lo caro no es la migración, es que una app ya publicada no sepa
          -- interpretar un valor nuevo dentro de la misma versión de la API (ADR-0012).
          CONSTRAINT ck_memberships_role_valido
            CHECK (role IN ('dueno','profesional','recepcion')),
          CONSTRAINT ck_memberships_status_valido
            CHECK (status IN ('invitada','activa','revocada'))
        );
        CREATE INDEX ix_memberships_business_id ON memberships (business_id);
        CREATE INDEX ix_memberships_user_id ON memberships (user_id);

        CREATE TABLE sessions (
          id                 uuid NOT NULL DEFAULT uuid_generate_v7(),
          user_id            uuid NOT NULL,
          family_id          uuid NOT NULL,
          refresh_token_hash bytea NOT NULL,
          active_business_id uuid,
          surface            text NOT NULL,
          device_label       text,
          ip_hash            bytea,
          user_agent         text,
          issued_at          timestamptz NOT NULL,
          expires_at         timestamptz NOT NULL,
          rotated_at         timestamptz,
          replaced_by_id     uuid,
          revoked_at         timestamptz,
          revoked_reason     text,
          CONSTRAINT pk_sessions PRIMARY KEY (id),
          CONSTRAINT uq_sessions_refresh_token_hash UNIQUE (refresh_token_hash),
          CONSTRAINT fk_sessions_user_id_users FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE CASCADE,
          CONSTRAINT fk_sessions_active_business_id_businesses FOREIGN KEY (active_business_id)
            REFERENCES businesses(id) ON DELETE SET NULL,
          CONSTRAINT fk_sessions_replaced_by_id_sessions FOREIGN KEY (replaced_by_id)
            REFERENCES sessions(id) ON DELETE SET NULL,
          CONSTRAINT ck_sessions_surface_valida CHECK (surface IN ('web','app')),
          CONSTRAINT ck_sessions_motivo_revocacion_valido CHECK (
            revoked_reason IS NULL
            OR revoked_reason IN ('cierre_sesion','rotacion_reusada','borrado_cuenta','admin')
          )
        );
        -- Parcial: «cerrar sesión en todos los dispositivos» solo mira las vivas, y el índice
        -- completo cargaría con noventa días de sesiones muertas dentro.
        CREATE INDEX ix_sessions_vivas ON sessions (user_id) WHERE revoked_at IS NULL;
        CREATE INDEX ix_sessions_expires_at ON sessions (expires_at);

        CREATE TABLE slug_redirects (
          old_slug    text NOT NULL,
          business_id uuid NOT NULL,
          created_at  timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_slug_redirects PRIMARY KEY (old_slug),
          CONSTRAINT fk_slug_redirects_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE CASCADE
        );
        CREATE INDEX ix_slug_redirects_business_id ON slug_redirects (business_id);
        """
    )


def _equipo_y_catalogo() -> None:
    op.execute(
        """
        CREATE TABLE staff_profiles (
          id                     uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id            uuid NOT NULL,
          user_id                uuid,
          display_name           text NOT NULL,
          bio                    text,
          photo_key              text,
          active                 boolean NOT NULL DEFAULT true,
          visible_in_marketplace boolean NOT NULL DEFAULT true,
          accepts_any_staff      boolean NOT NULL DEFAULT true,
          position               smallint NOT NULL DEFAULT 0,
          created_at             timestamptz NOT NULL DEFAULT now(),
          updated_at             timestamptz NOT NULL DEFAULT now(),
          deleted_at             timestamptz,
          CONSTRAINT pk_staff_profiles PRIMARY KEY (id),
          CONSTRAINT fk_staff_profiles_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          -- Nulable a propósito (ONB-4): el dueño da de alta a alguien en dos minutos y le
          -- manda la invitación después.
          CONSTRAINT fk_staff_profiles_user_id_users FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE SET NULL
        );
        CREATE INDEX ix_staff_profiles_business_id ON staff_profiles (business_id);
        CREATE UNIQUE INDEX uq_staff_profiles_business_id_user_id
          ON staff_profiles (business_id, user_id) WHERE user_id IS NOT NULL;
        CREATE INDEX ix_staff_profiles_business_id_active ON staff_profiles (business_id, active);

        CREATE TABLE staff_hours (
          id          uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id uuid NOT NULL,
          staff_id    uuid NOT NULL,
          location_id uuid,
          weekday     smallint NOT NULL,
          starts_at   time NOT NULL,
          ends_at     time NOT NULL,
          kind        text NOT NULL DEFAULT 'trabajo',
          created_at  timestamptz NOT NULL DEFAULT now(),
          updated_at  timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_staff_hours PRIMARY KEY (id),
          CONSTRAINT fk_staff_hours_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_staff_hours_staff_id_staff_profiles FOREIGN KEY (staff_id)
            REFERENCES staff_profiles(id) ON DELETE CASCADE,
          CONSTRAINT fk_staff_hours_location_id_locations FOREIGN KEY (location_id)
            REFERENCES locations(id) ON DELETE CASCADE,
          CONSTRAINT ck_staff_hours_weekday_rango CHECK (weekday BETWEEN 0 AND 6),
          CONSTRAINT ck_staff_hours_kind_valido CHECK (kind IN ('trabajo','descanso')),
          CONSTRAINT uq_staff_hours_staff_dia_tramo UNIQUE (staff_id, weekday, kind, starts_at)
        );
        CREATE INDEX ix_staff_hours_business_id ON staff_hours (business_id);
        CREATE INDEX ix_staff_hours_business_id_staff_id ON staff_hours (business_id, staff_id);

        CREATE TABLE services (
          id                   uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id          uuid NOT NULL,
          service_category_id  uuid NOT NULL,
          location_id          uuid,
          name                 text NOT NULL,
          description          text,
          duration_min         smallint NOT NULL,
          price_kind           text NOT NULL,
          price_minor          bigint,
          currency             char(3) NOT NULL DEFAULT 'USD',
          buffer_before_min    smallint NOT NULL DEFAULT 0,
          buffer_after_min     smallint NOT NULL DEFAULT 0,
          deposit_amount_minor bigint,
          photo_key            text,
          active               boolean NOT NULL DEFAULT true,
          position             smallint NOT NULL DEFAULT 0,
          created_at           timestamptz NOT NULL DEFAULT now(),
          updated_at           timestamptz NOT NULL DEFAULT now(),
          deleted_at           timestamptz,
          CONSTRAINT pk_services PRIMARY KEY (id),
          CONSTRAINT fk_services_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_services_service_category_id_service_categories
            FOREIGN KEY (service_category_id)
            REFERENCES service_categories(id) ON DELETE RESTRICT,
          CONSTRAINT fk_services_location_id_locations FOREIGN KEY (location_id)
            REFERENCES locations(id) ON DELETE CASCADE,
          CONSTRAINT ck_services_duracion_positiva CHECK (duration_min > 0),
          CONSTRAINT ck_services_buffers_no_negativos
            CHECK (buffer_before_min >= 0 AND buffer_after_min >= 0),
          CONSTRAINT ck_services_price_kind_valido
            CHECK (price_kind IN ('fijo','desde','consultar')),
          -- Evita el precio fantasma: «desde $120» tiene precio mínimo; «a consultar» no
          -- tiene ninguno y la interfaz lo dice, en vez de pintar «$0.00».
          CONSTRAINT ck_services_precio_coherente
            CHECK (price_kind = 'consultar' OR price_minor IS NOT NULL)
        );
        CREATE INDEX ix_services_business_id ON services (business_id);
        CREATE INDEX ix_services_business_id_active ON services (business_id, active);
        CREATE INDEX ix_services_service_category_id ON services (service_category_id);

        CREATE TABLE service_variants (
          id           uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id  uuid NOT NULL,
          service_id   uuid NOT NULL,
          name         text NOT NULL,
          duration_min smallint NOT NULL,
          price_kind   text NOT NULL,
          price_minor  bigint,
          position     smallint NOT NULL DEFAULT 0,
          active       boolean NOT NULL DEFAULT true,
          CONSTRAINT pk_service_variants PRIMARY KEY (id),
          CONSTRAINT fk_service_variants_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_service_variants_service_id_services FOREIGN KEY (service_id)
            REFERENCES services(id) ON DELETE CASCADE,
          CONSTRAINT uq_service_variants_service_id_name UNIQUE (service_id, name),
          CONSTRAINT ck_service_variants_duracion_positiva CHECK (duration_min > 0),
          CONSTRAINT ck_service_variants_price_kind_valido
            CHECK (price_kind IN ('fijo','desde','consultar')),
          CONSTRAINT ck_service_variants_precio_coherente
            CHECK (price_kind = 'consultar' OR price_minor IS NOT NULL)
        );
        CREATE INDEX ix_service_variants_business_id ON service_variants (business_id);

        CREATE TABLE staff_services (
          business_id           uuid NOT NULL,
          staff_id              uuid NOT NULL,
          service_id            uuid NOT NULL,
          -- v2 (SRV-3); hoy siempre NULL. Dos columnas nulables en una tabla de unión son
          -- gratis; descubrir en v2 que la relación era un array sería rehacerla.
          price_minor_override  bigint,
          duration_min_override smallint,
          CONSTRAINT pk_staff_services PRIMARY KEY (staff_id, service_id),
          CONSTRAINT fk_staff_services_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_staff_services_staff_id_staff_profiles FOREIGN KEY (staff_id)
            REFERENCES staff_profiles(id) ON DELETE CASCADE,
          CONSTRAINT fk_staff_services_service_id_services FOREIGN KEY (service_id)
            REFERENCES services(id) ON DELETE CASCADE
        );
        CREATE INDEX ix_staff_services_business_id ON staff_services (business_id);
        CREATE INDEX ix_staff_services_service_id ON staff_services (service_id);

        CREATE TABLE time_block_rules (
          id                 uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id        uuid NOT NULL,
          staff_id           uuid,
          weekday            smallint NOT NULL,
          starts_at          time NOT NULL,
          ends_at            time NOT NULL,
          reason             text,
          valid_from         date NOT NULL,
          valid_until        date,
          materialized_until date NOT NULL,
          created_at         timestamptz NOT NULL DEFAULT now(),
          updated_at         timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_time_block_rules PRIMARY KEY (id),
          CONSTRAINT fk_time_block_rules_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          -- NULL = todo el equipo del negocio.
          CONSTRAINT fk_time_block_rules_staff_id_staff_profiles FOREIGN KEY (staff_id)
            REFERENCES staff_profiles(id) ON DELETE CASCADE,
          CONSTRAINT ck_time_block_rules_weekday_rango CHECK (weekday BETWEEN 0 AND 6),
          CONSTRAINT ck_time_block_rules_vigencia_coherente
            CHECK (valid_until IS NULL OR valid_until >= valid_from)
        );
        CREATE INDEX ix_time_block_rules_business_id ON time_block_rules (business_id);
        CREATE INDEX ix_time_block_rules_business_id_staff_id
          ON time_block_rules (business_id, staff_id);
        """
    )


def _clientes() -> None:
    op.execute(
        """
        CREATE TABLE business_clients (
          id              uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id     uuid NOT NULL,
          user_id         uuid,
          display_name    text NOT NULL,
          phone_e164      text,
          email           text,
          notes           text,
          completed_count integer NOT NULL DEFAULT 0,
          no_show_count   integer NOT NULL DEFAULT 0,
          cancel_count    integer NOT NULL DEFAULT 0,
          blocked         boolean NOT NULL DEFAULT false,
          blocked_reason  text,
          source          text NOT NULL DEFAULT 'marketplace',
          first_seen_at   timestamptz,
          last_booking_at timestamptz,
          created_at      timestamptz NOT NULL DEFAULT now(),
          updated_at      timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_business_clients PRIMARY KEY (id),
          CONSTRAINT fk_business_clients_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          -- NULL = «cliente rápido» del walk-in (AGD-2). Por el marketplace no se reserva sin
          -- teléfono verificado (D9); el cliente rápido solo existe en reservas del negocio.
          CONSTRAINT fk_business_clients_user_id_users FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE SET NULL,
          CONSTRAINT ck_business_clients_source_valido
            CHECK (source IN ('marketplace','manual','importado'))
        );
        CREATE INDEX ix_business_clients_business_id ON business_clients (business_id);
        CREATE UNIQUE INDEX uq_business_clients_business_id_user_id
          ON business_clients (business_id, user_id) WHERE user_id IS NOT NULL;
        -- Así encuentra el dueño a alguien: escribiendo cuatro dígitos del teléfono mientras
        -- atiende. Sin este índice el buscador de la agenda hace recorrido secuencial.
        CREATE INDEX ix_business_clients_business_id_phone_e164
          ON business_clients (business_id, phone_e164);

        CREATE TABLE favorites (
          user_id     uuid NOT NULL,
          business_id uuid NOT NULL,
          created_at  timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_favorites PRIMARY KEY (user_id, business_id),
          CONSTRAINT fk_favorites_user_id_users FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE CASCADE,
          CONSTRAINT fk_favorites_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE CASCADE
        );
        CREATE INDEX ix_favorites_business_id ON favorites (business_id);
        """
    )


def _reservas_y_ocupacion() -> None:
    op.execute(
        f"""
        CREATE TABLE bookings (
          id                   uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id          uuid NOT NULL,
          location_id          uuid,
          staff_id             uuid NOT NULL,
          business_client_id   uuid NOT NULL,
          client_user_id       uuid,
          status               text NOT NULL DEFAULT 'pendiente',
          starts_at            timestamptz NOT NULL,
          ends_at              timestamptz NOT NULL,
          total_duration_min   smallint NOT NULL,
          total_amount_minor   bigint NOT NULL DEFAULT 0,
          currency             char(3) NOT NULL DEFAULT 'USD',
          source               text NOT NULL,
          any_staff_requested  boolean NOT NULL DEFAULT false,
          client_note          text,
          business_note        text,
          rescheduled_from_id  uuid,
          reschedule_count     smallint NOT NULL DEFAULT 0,
          confirmed_at         timestamptz,
          completed_at         timestamptz,
          no_show_at           timestamptz,
          cancelled_at         timestamptz,
          cancelled_by         text,
          cancellation_reason  text,
          deposit_amount_minor bigint,
          deposit_payment_id   uuid,
          created_by_user_id   uuid,
          created_by_admin_id  uuid,
          created_at           timestamptz NOT NULL DEFAULT now(),
          updated_at           timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_bookings PRIMARY KEY (id),
          CONSTRAINT fk_bookings_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_bookings_location_id_locations FOREIGN KEY (location_id)
            REFERENCES locations(id) ON DELETE RESTRICT,
          CONSTRAINT fk_bookings_staff_id_staff_profiles FOREIGN KEY (staff_id)
            REFERENCES staff_profiles(id) ON DELETE RESTRICT,
          -- La reserva **no copia** el nombre ni el teléfono del cliente: apunta aquí y lee.
          -- Así, anonimizar a una persona reescribe una fila por negocio y no todas sus
          -- reservas en todos los salones (§15).
          CONSTRAINT fk_bookings_business_client_id_business_clients
            FOREIGN KEY (business_client_id)
            REFERENCES business_clients(id) ON DELETE RESTRICT,
          CONSTRAINT fk_bookings_client_user_id_users FOREIGN KEY (client_user_id)
            REFERENCES users(id) ON DELETE SET NULL,
          CONSTRAINT fk_bookings_rescheduled_from_id_bookings FOREIGN KEY (rescheduled_from_id)
            REFERENCES bookings(id) ON DELETE SET NULL,
          CONSTRAINT fk_bookings_created_by_user_id_users FOREIGN KEY (created_by_user_id)
            REFERENCES users(id) ON DELETE SET NULL,
          CONSTRAINT fk_bookings_created_by_admin_id_admin_users FOREIGN KEY (created_by_admin_id)
            REFERENCES admin_users(id) ON DELETE SET NULL,
          CONSTRAINT ck_bookings_status_valido CHECK (status IN ({_ESTADOS_RESERVA})),
          CONSTRAINT ck_bookings_rango_valido CHECK (ends_at > starts_at),
          CONSTRAINT ck_bookings_source_valido
            CHECK (source IN ('cliente_web','cliente_app','negocio_manual','admin')),
          CONSTRAINT ck_bookings_cancelled_by_valido CHECK (
            cancelled_by IS NULL
            OR cancelled_by IN ('cliente','negocio','sistema','admin')
          )
        );
        CREATE INDEX ix_bookings_business_id ON bookings (business_id);
        -- La agenda del día y de la semana. Es **la** consulta del producto.
        CREATE INDEX ix_bookings_business_id_starts_at ON bookings (business_id, starts_at);
        -- La agenda de un profesional, que es lo que ve en la app.
        CREATE INDEX ix_bookings_business_id_staff_id_starts_at
          ON bookings (business_id, staff_id, starts_at);
        CREATE INDEX ix_bookings_business_id_status_starts_at
          ON bookings (business_id, status, starts_at);
        -- El historial del cliente y «reservar de nuevo» (RSV-7).
        CREATE INDEX ix_bookings_client_user_id_starts_at
          ON bookings (client_user_id, starts_at DESC);
        CREATE INDEX ix_bookings_business_client_id_starts_at
          ON bookings (business_client_id, starts_at DESC);
        -- Parcial para que el barrido de recordatorios a 24 h y 2 h mire un índice pequeño y
        -- no el histórico entero.
        CREATE INDEX ix_bookings_recordatorios ON bookings (starts_at)
          WHERE status IN ({_ESTADOS_QUE_OCUPAN});

        CREATE TABLE booking_items (
          id                         uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id                uuid NOT NULL,
          booking_id                 uuid NOT NULL,
          position                   smallint NOT NULL,
          service_id                 uuid NOT NULL,
          service_variant_id         uuid,
          staff_id                   uuid,
          name_snapshot              text NOT NULL,
          duration_min_snapshot      smallint NOT NULL,
          price_kind_snapshot        text NOT NULL,
          price_minor_snapshot       bigint,
          currency                   char(3) NOT NULL,
          buffer_before_min_snapshot smallint NOT NULL,
          buffer_after_min_snapshot  smallint NOT NULL,
          CONSTRAINT pk_booking_items PRIMARY KEY (id),
          CONSTRAINT uq_booking_items_booking_id_position UNIQUE (booking_id, position),
          CONSTRAINT fk_booking_items_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_booking_items_booking_id_bookings FOREIGN KEY (booking_id)
            REFERENCES bookings(id) ON DELETE CASCADE,
          CONSTRAINT fk_booking_items_service_id_services FOREIGN KEY (service_id)
            REFERENCES services(id) ON DELETE RESTRICT,
          CONSTRAINT fk_booking_items_service_variant_id_service_variants
            FOREIGN KEY (service_variant_id)
            REFERENCES service_variants(id) ON DELETE RESTRICT,
          -- Hueco RSV-2 v2: servicios de la misma cita con distintos profesionales.
          CONSTRAINT fk_booking_items_staff_id_staff_profiles FOREIGN KEY (staff_id)
            REFERENCES staff_profiles(id) ON DELETE RESTRICT
        );
        CREATE INDEX ix_booking_items_business_id ON booking_items (business_id);
        CREATE INDEX ix_booking_items_service_id ON booking_items (service_id);
        """
    )

    # --- staff_occupancy: la garantía nº 2 de la constitución --------------------------
    op.execute(
        """
        CREATE TABLE staff_occupancy (
          id                 uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id        uuid NOT NULL,
          staff_id           uuid NOT NULL,

          -- Qué clase de fila es. Reservas y bloqueos comparten tabla justamente para que
          -- compartan restricción: si el almuerzo viviera en otra tabla, PostgreSQL no podría
          -- impedir que le encajaran una cita encima.
          kind               text NOT NULL,
          -- Para kind='reserva': espejo de bookings.status, mantenido por disparador.
          -- Para kind='bloqueo': activo | levantado.
          status             text NOT NULL,

          booking_id         uuid,
          rule_id            uuid,
          occurrence_date    date,
          reason             text,

          -- Hueco STF-4 / D17: la persona detrás del profesional, si tiene cuenta. Hoy solo
          -- se rellena; en v2 sostiene la exclusión entre negocios sin tener que rellenar
          -- millones de filas con bloqueos largos sobre la tabla más caliente del sistema.
          staff_user_id      uuid,

          starts_at          timestamptz NOT NULL,
          ends_at            timestamptz NOT NULL,

          -- Buffers COPIADOS del servicio en el momento de reservar, no leídos del catálogo.
          buffer_before_min  smallint NOT NULL DEFAULT 0,
          buffer_after_min   smallint NOT NULL DEFAULT 0,

          created_at timestamptz NOT NULL DEFAULT now(),
          updated_at timestamptz NOT NULL DEFAULT now(),

          CONSTRAINT pk_staff_occupancy PRIMARY KEY (id),
          CONSTRAINT uq_staff_occupancy_booking_id UNIQUE (booking_id),
          CONSTRAINT fk_staff_occupancy_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_staff_occupancy_staff_id_staff_profiles FOREIGN KEY (staff_id)
            REFERENCES staff_profiles(id) ON DELETE CASCADE,
          CONSTRAINT fk_staff_occupancy_booking_id_bookings FOREIGN KEY (booking_id)
            REFERENCES bookings(id) ON DELETE CASCADE,
          CONSTRAINT fk_staff_occupancy_rule_id_time_block_rules FOREIGN KEY (rule_id)
            REFERENCES time_block_rules(id) ON DELETE CASCADE,
          CONSTRAINT fk_staff_occupancy_staff_user_id_users FOREIGN KEY (staff_user_id)
            REFERENCES users(id) ON DELETE SET NULL,
          CONSTRAINT ck_staff_occupancy_kind_valido CHECK (kind IN ('reserva','bloqueo')),
          CONSTRAINT ck_staff_occupancy_buffer_before_no_negativo
            CHECK (buffer_before_min >= 0),
          CONSTRAINT ck_staff_occupancy_buffer_after_no_negativo CHECK (buffer_after_min >= 0),
          CONSTRAINT ck_staff_occupancy_rango_valido CHECK (ends_at > starts_at),
          CONSTRAINT ck_staff_occupancy_reserva_coherente CHECK (
            (kind = 'reserva' AND booking_id IS NOT NULL AND rule_id IS NULL)
            OR
            (kind = 'bloqueo' AND booking_id IS NULL)
          )
        );
        """
    )
    # El rango que de verdad bloquea la agenda: el servicio MÁS sus buffers. Generadas y
    # persistidas por la base (ADR-0004), nunca calculadas por la aplicación. Se añaden con
    # ALTER porque así queda a la vista que dependen de `desplazar_minutos`, que es IMMUTABLE
    # justamente para poder aparecer aquí.
    op.execute(
        """
        ALTER TABLE staff_occupancy
          ADD COLUMN blocked_from timestamptz
            GENERATED ALWAYS AS (desplazar_minutos(starts_at, -buffer_before_min)) STORED,
          ADD COLUMN blocked_to timestamptz
            GENERATED ALWAYS AS (desplazar_minutos(ends_at, buffer_after_min)) STORED;
        """
    )
    # LA restricción. Es de la base de datos, no de la aplicación: aunque el código de reserva
    # esté mal, esto no se puede violar.
    #
    # Cinco detalles que son la decisión y no la sintaxis:
    #   1. Se excluye sobre blocked_from/blocked_to, no sobre starts_at/ends_at: el rango que
    #      ocupa la agenda incluye los buffers.
    #   2. El rango es semiabierto '[)': una cita que acaba a las 10:00 y otra que empieza a
    #      las 10:00 no se solapan. Con '[]' la agenda perdería un slot cada hora.
    #   3. El WHERE deja fuera los estados terminales: cancelar libera el hueco de inmediato
    #      **sin borrar la fila**.
    #   4. La exclusión es por staff_id **solo**, sin business_id: cuando llegue STF-4 la
    #      persona podrá trabajar en dos salones y la restricción tiene que seguir impidiendo
    #      que le reserven a la misma hora en los dos.
    #   5. Una reserva multi-servicio es UNA fila: tres filas sueltas dejarían que otra cita
    #      se colara en medio de la cadena.
    op.execute(
        f"""
        ALTER TABLE staff_occupancy
          ADD CONSTRAINT staff_occupancy_sin_solape
          EXCLUDE USING gist (
            staff_id WITH =,
            tstzrange(blocked_from, blocked_to, '[)') WITH &&
          )
          WHERE (
               (kind = 'reserva' AND status IN ({_ESTADOS_QUE_OCUPAN}))
            OR (kind = 'bloqueo' AND status = 'activo')
          );
        """
    )
    op.execute(
        """
        -- Materialización idempotente de los bloqueos recurrentes: ejecutar el trabajo dos
        -- veces no crea dos almuerzos.
        CREATE UNIQUE INDEX uq_staff_occupancy_regla_ocurrencia
          ON staff_occupancy (rule_id, staff_id, occurrence_date)
          WHERE rule_id IS NOT NULL;

        -- Lecturas de agenda: el día de un profesional y el día del negocio entero.
        CREATE INDEX ix_staff_occupancy_business_id ON staff_occupancy (business_id);
        CREATE INDEX ix_staff_occupancy_agenda_staff
          ON staff_occupancy (business_id, staff_id, blocked_from);
        CREATE INDEX ix_staff_occupancy_agenda_negocio
          ON staff_occupancy (business_id, blocked_from);

        CREATE TABLE booking_events (
          id             uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id    uuid NOT NULL,
          booking_id     uuid NOT NULL,
          type           text NOT NULL,
          from_status    text,
          to_status      text,
          actor_kind     text NOT NULL,
          actor_user_id  uuid,
          actor_admin_id uuid,
          payload        jsonb NOT NULL DEFAULT '{}'::jsonb,
          created_at     timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_booking_events PRIMARY KEY (id),
          CONSTRAINT fk_booking_events_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_booking_events_booking_id_bookings FOREIGN KEY (booking_id)
            REFERENCES bookings(id) ON DELETE CASCADE,
          CONSTRAINT fk_booking_events_actor_user_id_users FOREIGN KEY (actor_user_id)
            REFERENCES users(id) ON DELETE SET NULL,
          CONSTRAINT fk_booking_events_actor_admin_id_admin_users FOREIGN KEY (actor_admin_id)
            REFERENCES admin_users(id) ON DELETE SET NULL,
          CONSTRAINT ck_booking_events_type_valido CHECK (
            type IN ('creada','confirmada','reprogramada','cancelada','completada','no_show',
                     'recordatorio_encolado','review_solicitada','nota_anadida')
          ),
          CONSTRAINT ck_booking_events_actor_kind_valido
            CHECK (actor_kind IN ('cliente','negocio','sistema','admin'))
        );
        CREATE INDEX ix_booking_events_business_id ON booking_events (business_id);
        CREATE INDEX ix_booking_events_booking_id_created_at
          ON booking_events (booking_id, created_at);
        """
    )


def _reviews_y_senales() -> None:
    op.execute(
        """
        CREATE TABLE reviews (
          id                 uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id        uuid NOT NULL,
          booking_id         uuid NOT NULL,
          author_user_id     uuid,
          staff_id           uuid,
          rating             smallint NOT NULL,
          staff_rating       smallint,
          body               text,
          status             text NOT NULL DEFAULT 'publicada',
          hidden_reason      text,
          hidden_by_admin_id uuid,
          published_at       timestamptz,
          created_at         timestamptz NOT NULL DEFAULT now(),
          updated_at         timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_reviews PRIMARY KEY (id),
          -- Una review por reserva, y lo garantiza la base de datos, no la interfaz.
          CONSTRAINT uq_reviews_booking_id UNIQUE (booking_id),
          CONSTRAINT fk_reviews_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_reviews_booking_id_bookings FOREIGN KEY (booking_id)
            REFERENCES bookings(id) ON DELETE RESTRICT,
          -- Nulable **solo** para sostener el borrado de cuenta: mientras la persona existe,
          -- nunca es nulo.
          CONSTRAINT fk_reviews_author_user_id_users FOREIGN KEY (author_user_id)
            REFERENCES users(id) ON DELETE SET NULL,
          CONSTRAINT fk_reviews_staff_id_staff_profiles FOREIGN KEY (staff_id)
            REFERENCES staff_profiles(id) ON DELETE SET NULL,
          CONSTRAINT fk_reviews_hidden_by_admin_id_admin_users FOREIGN KEY (hidden_by_admin_id)
            REFERENCES admin_users(id) ON DELETE SET NULL,
          CONSTRAINT ck_reviews_rating_rango CHECK (rating BETWEEN 1 AND 5),
          CONSTRAINT ck_reviews_staff_rating_rango
            CHECK (staff_rating IS NULL OR staff_rating BETWEEN 1 AND 5),
          CONSTRAINT ck_reviews_status_valido
            CHECK (status IN ('publicada','oculta','retirada'))
        );
        CREATE INDEX ix_reviews_business_id ON reviews (business_id);
        CREATE INDEX ix_reviews_business_id_created_at ON reviews (business_id, created_at DESC);
        CREATE INDEX ix_reviews_staff_id ON reviews (staff_id);

        CREATE TABLE review_media (
          id                uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id       uuid NOT NULL,
          review_id         uuid NOT NULL,
          storage_key       text NOT NULL,
          moderation_status text NOT NULL DEFAULT 'pendiente',
          created_at        timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_review_media PRIMARY KEY (id),
          CONSTRAINT fk_review_media_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_review_media_review_id_reviews FOREIGN KEY (review_id)
            REFERENCES reviews(id) ON DELETE CASCADE,
          CONSTRAINT ck_review_media_moderacion_valida
            CHECK (moderation_status IN ('pendiente','aprobada','rechazada'))
        );
        CREATE INDEX ix_review_media_business_id ON review_media (business_id);
        CREATE INDEX ix_review_media_review_id ON review_media (review_id);

        CREATE TABLE review_replies (
          id             uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id    uuid NOT NULL,
          review_id      uuid NOT NULL,
          author_user_id uuid,
          body           text NOT NULL,
          created_at     timestamptz NOT NULL DEFAULT now(),
          updated_at     timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_review_replies PRIMARY KEY (id),
          -- El único implementa REV-3 literalmente: **una** respuesta por review.
          CONSTRAINT uq_review_replies_review_id UNIQUE (review_id),
          CONSTRAINT fk_review_replies_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_review_replies_review_id_reviews FOREIGN KEY (review_id)
            REFERENCES reviews(id) ON DELETE CASCADE,
          CONSTRAINT fk_review_replies_author_user_id_users FOREIGN KEY (author_user_id)
            REFERENCES users(id) ON DELETE SET NULL
        );
        CREATE INDEX ix_review_replies_business_id ON review_replies (business_id);

        CREATE TABLE review_reports (
          id                   uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id          uuid NOT NULL,
          review_id            uuid NOT NULL,
          reporter_user_id     uuid,
          reporter_kind        text NOT NULL,
          reason               text NOT NULL,
          status               text NOT NULL DEFAULT 'abierto',
          resolved_by_admin_id uuid,
          resolution_note      text,
          created_at           timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_review_reports PRIMARY KEY (id),
          CONSTRAINT fk_review_reports_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT fk_review_reports_review_id_reviews FOREIGN KEY (review_id)
            REFERENCES reviews(id) ON DELETE CASCADE,
          CONSTRAINT fk_review_reports_reporter_user_id_users FOREIGN KEY (reporter_user_id)
            REFERENCES users(id) ON DELETE SET NULL,
          CONSTRAINT fk_review_reports_resolved_by_admin_id_admin_users
            FOREIGN KEY (resolved_by_admin_id)
            REFERENCES admin_users(id) ON DELETE SET NULL,
          CONSTRAINT ck_review_reports_reporter_kind_valido
            CHECK (reporter_kind IN ('cliente','negocio','sistema')),
          CONSTRAINT ck_review_reports_status_valido
            CHECK (status IN ('abierto','en_revision','resuelto','descartado'))
        );
        CREATE INDEX ix_review_reports_business_id ON review_reports (business_id);
        CREATE INDEX ix_review_reports_review_id ON review_reports (review_id);

        CREATE TABLE business_rating_stats (
          business_id     uuid NOT NULL,
          reviews_count   integer NOT NULL DEFAULT 0,
          rating_sum      integer NOT NULL DEFAULT 0,
          rating_avg      numeric(3,2),
          -- Lo que se muestra y lo que ordena (REV-5, ADR-0009). Se guarda `rating_avg`
          -- **además** porque son cosas distintas y las dos hacen falta.
          rating_bayesian numeric(3,2),
          last_review_at  timestamptz,
          updated_at      timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_business_rating_stats PRIMARY KEY (business_id),
          CONSTRAINT fk_business_rating_stats_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE CASCADE,
          CONSTRAINT ck_business_rating_stats_conteo_no_negativo CHECK (reviews_count >= 0)
        );

        CREATE TABLE business_ranking_signals (
          business_id     uuid NOT NULL,
          computed_at     timestamptz NOT NULL,
          weights_version integer NOT NULL,
          bookings_recent integer NOT NULL DEFAULT 0,
          completion_rate numeric(4,3),
          completeness    numeric(4,3),
          activity_score  numeric(4,3),
          rating_bayesian numeric(3,2),
          new_boost       numeric(4,3),
          base_score      numeric NOT NULL,
          signals         jsonb NOT NULL DEFAULT '{}'::jsonb,
          CONSTRAINT pk_business_ranking_signals PRIMARY KEY (business_id),
          CONSTRAINT fk_business_ranking_signals_business_id_businesses
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
        );
        CREATE INDEX ix_business_ranking_signals_base_score
          ON business_ranking_signals (base_score DESC);

        CREATE TABLE listing_impressions_daily (
          id                  uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id         uuid NOT NULL,
          day                 date NOT NULL,
          surface             text NOT NULL,
          placement           text NOT NULL,
          zone_id             uuid,
          service_category_id uuid,
          count               integer NOT NULL DEFAULT 0,
          CONSTRAINT pk_listing_impressions_daily PRIMARY KEY (id),
          CONSTRAINT fk_listing_impressions_daily_business_id_businesses
            FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE,
          CONSTRAINT fk_listing_impressions_daily_zone_id_zones FOREIGN KEY (zone_id)
            REFERENCES zones(id) ON DELETE SET NULL,
          CONSTRAINT fk_listing_impressions_daily_service_category_id_service_categories
            FOREIGN KEY (service_category_id)
            REFERENCES service_categories(id) ON DELETE SET NULL,
          CONSTRAINT ck_listing_impressions_daily_placement_valido
            CHECK (placement IN ('organico','patrocinado'))
        );
        CREATE INDEX ix_listing_impressions_daily_business_id
          ON listing_impressions_daily (business_id);
        CREATE INDEX ix_listing_impressions_daily_business_id_day
          ON listing_impressions_daily (business_id, day);

        CREATE TABLE listing_clicks_daily (
          id                  uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id         uuid NOT NULL,
          day                 date NOT NULL,
          surface             text NOT NULL,
          kind                text NOT NULL,
          zone_id             uuid,
          service_category_id uuid,
          count               integer NOT NULL DEFAULT 0,
          CONSTRAINT pk_listing_clicks_daily PRIMARY KEY (id),
          CONSTRAINT fk_listing_clicks_daily_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE CASCADE,
          CONSTRAINT fk_listing_clicks_daily_zone_id_zones FOREIGN KEY (zone_id)
            REFERENCES zones(id) ON DELETE SET NULL,
          CONSTRAINT fk_listing_clicks_daily_service_category_id_service_categories
            FOREIGN KEY (service_category_id)
            REFERENCES service_categories(id) ON DELETE SET NULL,
          -- El clic `whatsapp` registra el salto en servidor del click-to-chat: el número
          -- nunca viaja al cliente (ADR-0007).
          CONSTRAINT ck_listing_clicks_daily_kind_valido
            CHECK (kind IN ('perfil','whatsapp','mapa','reservar'))
        );
        CREATE INDEX ix_listing_clicks_daily_business_id ON listing_clicks_daily (business_id);
        CREATE INDEX ix_listing_clicks_daily_business_id_day
          ON listing_clicks_daily (business_id, day);
        """
    )
    # `NULLS NOT DISTINCT` es lo que hace que dos impresiones «sin zona» del mismo día sumen
    # en la misma fila: con el comportamiento por defecto, cada NULL sería una fila nueva y el
    # `ON CONFLICT DO UPDATE SET count = count + 1` no encontraría nunca su conflicto.
    op.execute(
        "CREATE UNIQUE INDEX uq_listing_impressions_daily_clave "
        "ON listing_impressions_daily (business_id, day, surface, placement, zone_id, "
        "service_category_id) NULLS NOT DISTINCT"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_listing_clicks_daily_clave "
        "ON listing_clicks_daily (business_id, day, surface, kind, zone_id, "
        "service_category_id) NULLS NOT DISTINCT"
    )


def _disparadores() -> None:
    for tabla in TABLAS_CON_UPDATED_AT:
        op.execute(
            f"CREATE TRIGGER {tabla}_toca_updated_at BEFORE UPDATE ON {tabla} "
            f"FOR EACH ROW EXECUTE FUNCTION tocar_updated_at()"
        )

    # Que la reserva y su ocupación tengan estados independientes es la forma más fácil de que
    # una cita cancelada siga bloqueando la agenda. No se deja a que la aplicación se acuerde.
    #
    # Tiene una propiedad que conviene entender: **reprogramar una cita a un hueco ocupado
    # falla dentro del disparador**, con la misma 23P01, dentro de la misma transacción, y el
    # UPDATE de bookings se deshace entero. El arrastrar-y-soltar de la agenda (AGD-2) hereda
    # así la garantía de no doble reserva sin escribir ni una línea de comprobación.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sincronizar_ocupacion_reserva()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          UPDATE staff_occupancy
             SET status     = NEW.status,
                 starts_at  = NEW.starts_at,
                 ends_at    = NEW.ends_at,
                 staff_id   = NEW.staff_id,
                 updated_at = now()
           WHERE booking_id = NEW.id;
          RETURN NEW;
        END $$;

        CREATE TRIGGER bookings_sincroniza_ocupacion
          AFTER UPDATE OF status, starts_at, ends_at, staff_id ON bookings
          FOR EACH ROW
          WHEN (OLD.status    IS DISTINCT FROM NEW.status
             OR OLD.starts_at IS DISTINCT FROM NEW.starts_at
             OR OLD.ends_at   IS DISTINCT FROM NEW.ends_at
             OR OLD.staff_id  IS DISTINCT FROM NEW.staff_id)
          EXECUTE FUNCTION sincronizar_ocupacion_reserva();
        """
    )


def _seguridad_por_fila() -> None:
    """Patrón A y patrón B de ADR-0002. Todo el esquema se reduce a estos dos."""
    # Patrón B — el negocio tiene una cara pública. Se resuelve con **una segunda política**
    # para el rol público, no relajando la del tenant.
    op.execute(
        """
        ALTER TABLE businesses ENABLE ROW LEVEL SECURITY;
        ALTER TABLE businesses FORCE ROW LEVEL SECURITY;

        CREATE POLICY businesses_tenant ON businesses
          FOR ALL TO agenda_api
          USING      (id = app_negocio_actual())
          WITH CHECK (id = app_negocio_actual());

        CREATE POLICY businesses_marketplace ON businesses
          FOR SELECT TO agenda_publico
          USING (status = 'publicado' AND deleted_at IS NULL);

        -- El back-office ve todo, pero con su propio rol y su propia sesión: nunca el mismo
        -- rol que la API pública (ADR-0006).
        CREATE POLICY businesses_admin ON businesses
          FOR ALL TO agenda_admin USING (true) WITH CHECK (true);
        """
    )

    # Patrón A — tabla privada del negocio. `USING` filtra lo que se lee y lo que se puede
    # modificar; `WITH CHECK` impide **escribir** una fila con el business_id de otro. Sin
    # `WITH CHECK`, un INSERT con un business_id ajeno pasaría: la fila entraría y luego el
    # propio autor no la vería, que es la peor de las dos fugas porque no da la cara.
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

    # `favorites` lleva `business_id` y **no** lleva política de tenant, y es deliberado: la
    # fila es del usuario, no del salón, y el salón no tiene por qué ver quién lo guardó. Es
    # la excepción documentada de §7, y por eso la prueba de catálogo de ADR-0002 lleva una
    # lista corta y justificada de exclusiones en vez de mirar solo el nombre de la columna.

    # La cara pública del marketplace. Cada política se ata a que el negocio esté publicado:
    # despublicar un negocio tiene que apagar su perfil entero de una sola vez, no tabla a
    # tabla desde la aplicación.
    publicables = {
        "locations": "true",
        "business_media": "moderation_status = 'aprobada'",
        "business_categories": "true",
        "business_attributes": "true",
        "services": "active AND deleted_at IS NULL",
        "service_variants": "active",
        "staff_profiles": "active AND visible_in_marketplace AND deleted_at IS NULL",
        "reviews": "status = 'publicada'",
        "review_replies": "true",
        "business_rating_stats": "true",
        "business_ranking_signals": "true",
    }
    for tabla, condicion in publicables.items():
        op.execute(
            f"""
            CREATE POLICY {tabla}_marketplace ON {tabla}
              FOR SELECT TO agenda_publico
              USING (
                ({condicion})
                AND EXISTS (
                  SELECT 1 FROM businesses b
                   WHERE b.id = {tabla}.business_id
                     AND b.status = 'publicado'
                     AND b.deleted_at IS NULL
                )
              );
            """
        )

    # Las tablas de plataforma no se aíslan por negocio, pero tampoco son de todos: `sessions`
    # y `favorites` son del usuario y la API las filtra por identidad, no por tenant.
    op.execute(
        """
        ALTER TABLE slug_redirects ENABLE ROW LEVEL SECURITY;
        ALTER TABLE slug_redirects FORCE ROW LEVEL SECURITY;
        CREATE POLICY slug_redirects_lectura ON slug_redirects
          FOR SELECT TO agenda_api, agenda_publico USING (true);
        CREATE POLICY slug_redirects_admin ON slug_redirects
          FOR ALL TO agenda_admin USING (true) WITH CHECK (true);
        """
    )


def _permisos() -> None:
    escritura = (
        "businesses",
        "locations",
        "business_hours",
        "business_settings",
        "business_media",
        "business_categories",
        "business_attributes",
        "memberships",
        "sessions",
        "staff_profiles",
        "staff_hours",
        "staff_services",
        "time_block_rules",
        "services",
        "service_variants",
        "business_clients",
        "favorites",
        "bookings",
        "booking_items",
        "staff_occupancy",
        "reviews",
        "review_media",
        "review_replies",
        "review_reports",
        "business_rating_stats",
        "business_ranking_signals",
        "listing_impressions_daily",
        "listing_clicks_daily",
        "slug_redirects",
    )
    for tabla in escritura:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tabla} TO agenda_api")
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tabla} TO agenda_admin")

    # `booking_events` es append-only: la API **no** tiene UPDATE ni DELETE. Un registro que
    # se puede modificar no sirve para responder «¿quién canceló esta cita?» (ADM-7).
    op.execute("GRANT SELECT, INSERT ON booking_events TO agenda_api")
    op.execute("GRANT SELECT, INSERT ON booking_events TO agenda_admin")

    # El rol público solo lee, y solo lo publicable. Lo que impide que el marketplace se lleve
    # un teléfono es doble: no tiene SELECT sobre las tablas sensibles —`bookings`,
    # `business_clients`, `memberships` no están en esta lista— y, además, toda respuesta
    # pública pasa por un serializador explícito (ADR-0012).
    publico = (
        "businesses",
        "locations",
        "business_hours",
        "business_media",
        "business_categories",
        "business_attributes",
        "services",
        "service_variants",
        "staff_profiles",
        "reviews",
        "review_replies",
        "business_rating_stats",
        "business_ranking_signals",
        "slug_redirects",
    )
    for tabla in publico:
        op.execute(f"GRANT SELECT ON {tabla} TO agenda_publico")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS bookings_sincroniza_ocupacion ON bookings")
    op.execute("DROP FUNCTION IF EXISTS sincronizar_ocupacion_reserva()")
    op.execute(
        """
        DROP TABLE IF EXISTS listing_clicks_daily, listing_impressions_daily,
          business_ranking_signals, business_rating_stats, review_reports, review_replies,
          review_media, reviews, booking_events, staff_occupancy, booking_items, bookings,
          favorites, business_clients, time_block_rules, staff_services, service_variants,
          services, staff_hours, staff_profiles, slug_redirects, sessions, memberships,
          business_attributes, business_categories, business_media, business_settings,
          business_hours, locations, businesses CASCADE;
        """
    )
