"""El portal del dueño: anuncio del salón, fichaje y la puerta de las invitaciones.

Revision ID: 0011_portal_del_dueno
Revises: 0010_busqueda_sin_tildes
Create Date: 2026-09-07

Las seis piezas del punto 6 del encargo, y solo **dos** traen tabla nueva. Las otras cuatro
—todos los calendarios, la lista de profesionales, las finanzas y el mejor del mes— son
consultas sobre las citas que ya existen, y así se quedan: un agregado guardado se desincroniza
el primer día que alguien cancela una cita a mano, y entonces el panel de finanzas miente sin
fallar.

Lo que sí entra aquí:

* **`business_banners`** — la publicidad flash. Es del salón y para su propia ficha: **no es
  `ad_campaigns`**, que es el posicionamiento pagado del marketplace y se cobra (ADR-0010).
  Lleva su política pública siguiendo el patrón B de ADR-0002 al pie de la letra: se ve solo si
  el negocio está publicado **y** el anuncio está activo **y** dentro de su vigencia, de modo
  que despublicar el salón apague también su anuncio sin que nadie tenga que acordarse.

* **`staff_clock_events`** — el fichaje. Es **dato laboral y no es público jamás**: ni política
  para `agenda_publico` ni permiso concedido, y el `REVOKE` explícito está escrito porque los
  privilegios por defecto de la base local conceden `SELECT` al rol público a toda tabla nueva.
  Una tabla nueva sin política no es «se ve todo»: es que no se ve nada — pero el permiso
  colgando sí sería una puerta esperando a que alguien escriba el endpoint.

* **`staff_profiles.clock_in_enabled`**, apagado por defecto y **encendido persona a persona**.
  No es solo que la pantalla no lo ofrezca: la política de escritura de `staff_clock_events`
  exige que esté encendido, así que ni un trabajo en segundo plano ni un endpoint futuro pueden
  dejar el rastro de alguien a quien nadie se lo pidió.

* **La puerta de las invitaciones.** `memberships` ya tenía las columnas —token con hash y
  caducidad— y le faltaba poder abrirse: quien acepta todavía no está dentro de ningún negocio,
  así que la política de tenant no le deja ni ver su propia invitación. Se resuelve como el
  resto de la casa: **declarando con qué se pregunta**. `app.current_invite` es hermano de
  `app.current_business_id`, `app.current_user_id` y `app.current_staff_id`, y solo lo puede
  fijar quien presenta el token, porque lo que se compara es su hash.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_portal_del_dueno"
# Encadenada a la 0008 a propósito: hay otra rama escribiendo la 0009 en paralelo y el
# reencadenado se hace al fusionar, no adivinando aquí un identificador que todavía no existe.
down_revision = "0010_busqueda_sin_tildes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _fichaje_apagado_por_defecto()
    _anuncio_del_salon()
    _eventos_de_fichaje()
    _puerta_de_las_invitaciones()
    _cerrar_el_rol_publico()


def _fichaje_apagado_por_defecto() -> None:
    op.add_column(
        "staff_profiles",
        sa.Column(
            "clock_in_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )


def _anuncio_del_salon() -> None:
    op.execute(
        """
        CREATE TABLE business_banners (
          id          uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id uuid NOT NULL,
          message     text NOT NULL,
          active      boolean NOT NULL DEFAULT true,
          starts_at   timestamptz NOT NULL DEFAULT now(),
          -- NULL = sin fecha de fin. Es el salón que anuncia algo permanente, no una promoción.
          ends_at     timestamptz,
          created_at  timestamptz NOT NULL DEFAULT now(),
          updated_at  timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_business_banners PRIMARY KEY (id),
          CONSTRAINT fk_business_banners_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          CONSTRAINT ck_business_banners_mensaje_con_texto
            CHECK (char_length(btrim(message)) BETWEEN 1 AND 280),
          CONSTRAINT ck_business_banners_vigencia_coherente
            CHECK (ends_at IS NULL OR ends_at > starts_at),
          -- **Un anuncio a la vez.** Misma herramienta que la no doble reserva (ADR-0004) y por
          -- el mismo motivo: si dos anuncios activos se pisaran, la ficha pública tendría que
          -- elegir uno y el dueño no sabría cuál sale. Así se entera al guardar, no al mirar.
          CONSTRAINT ex_business_banners_sin_solape EXCLUDE USING gist (
            business_id WITH =,
            tstzrange(starts_at, coalesce(ends_at, 'infinity'::timestamptz), '[)') WITH &&
          ) WHERE (active)
        );
        CREATE INDEX ix_business_banners_business_id ON business_banners (business_id);
        CREATE INDEX ix_business_banners_vigentes
          ON business_banners (business_id, starts_at) WHERE active;

        CREATE TRIGGER business_banners_toca_updated_at BEFORE UPDATE ON business_banners
          FOR EACH ROW EXECUTE FUNCTION tocar_updated_at();
        """
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON business_banners TO agenda_api")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON business_banners TO agenda_admin")
    op.execute("GRANT SELECT ON business_banners TO agenda_publico")

    op.execute(
        """
        ALTER TABLE business_banners ENABLE ROW LEVEL SECURITY;
        ALTER TABLE business_banners FORCE ROW LEVEL SECURITY;

        CREATE POLICY business_banners_tenant ON business_banners
          FOR ALL TO agenda_api
          USING      (business_id = app_negocio_actual())
          WITH CHECK (business_id = app_negocio_actual());

        CREATE POLICY business_banners_admin ON business_banners
          FOR ALL TO agenda_admin USING (true) WITH CHECK (true);

        -- Patrón B de ADR-0002. Las tres condiciones van juntas a propósito: activo, vigente y
        -- de un negocio publicado. Dejar la vigencia para la aplicación significaría que un
        -- anuncio caducado sigue siendo legible por el rol público, y basta un endpoint
        -- distraído para publicarlo.
        CREATE POLICY business_banners_marketplace ON business_banners
          FOR SELECT TO agenda_publico
          USING (
            active
            AND starts_at <= now()
            AND (ends_at IS NULL OR ends_at > now())
            AND EXISTS (
              SELECT 1 FROM businesses b
               WHERE b.id = business_banners.business_id
                 AND b.status = 'publicado'
                 AND b.deleted_at IS NULL
            )
          );
        """
    )

    # El anuncio es configuración del salón: el profesional lo lee para saber qué se está
    # anunciando y no lo escribe (STF-3). Mismo mecanismo que la migración 0006 —restrictiva,
    # que se combina con AND— porque una política permisiva de más nunca quita acceso.
    for accion, clausulas in (
        ("INSERT", "WITH CHECK (app_profesional_actual() IS NULL)"),
        ("UPDATE", "USING (app_profesional_actual() IS NULL) "
                   "WITH CHECK (app_profesional_actual() IS NULL)"),
        ("DELETE", "USING (app_profesional_actual() IS NULL)"),
    ):
        op.execute(
            f"CREATE POLICY business_banners_profesional_no_configura_{accion.lower()} "
            f"ON business_banners AS RESTRICTIVE FOR {accion} TO agenda_api {clausulas};"
        )


def _eventos_de_fichaje() -> None:
    op.execute(
        """
        CREATE TABLE staff_clock_events (
          id                  uuid NOT NULL DEFAULT uuid_generate_v7(),
          business_id         uuid NOT NULL,
          staff_id            uuid NOT NULL,
          kind                text NOT NULL,
          occurred_at         timestamptz NOT NULL DEFAULT now(),
          source              text NOT NULL DEFAULT 'profesional',
          recorded_by_user_id uuid,
          note                text,
          created_at          timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_staff_clock_events PRIMARY KEY (id),
          CONSTRAINT fk_staff_clock_events_business_id_businesses FOREIGN KEY (business_id)
            REFERENCES businesses(id) ON DELETE RESTRICT,
          -- RESTRICT y no CASCADE: dar de baja a alguien no puede borrar su registro horario.
          -- La baja del equipo ya es lógica, así que esto no le estorba a nadie.
          CONSTRAINT fk_staff_clock_events_staff_id_staff_profiles FOREIGN KEY (staff_id)
            REFERENCES staff_profiles(id) ON DELETE RESTRICT,
          CONSTRAINT fk_staff_clock_events_recorded_by_user_id_users
            FOREIGN KEY (recorded_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
          CONSTRAINT ck_staff_clock_events_kind_valido CHECK (kind IN ('entrada','salida')),
          CONSTRAINT ck_staff_clock_events_source_valido
            CHECK (source IN ('profesional','dueno'))
        );
        CREATE INDEX ix_staff_clock_events_business_id ON staff_clock_events (business_id);
        CREATE INDEX ix_staff_clock_events_business_id_staff_id_occurred_at
          ON staff_clock_events (business_id, staff_id, occurred_at DESC);
        """
    )

    # **Append-only**, igual que `booking_events`: `SELECT` e `INSERT` y nada más. Un registro
    # horario que se puede reescribir no prueba nada, ni a favor del salón ni a favor de quien
    # trabaja allí; una equivocación se corrige con otro evento.
    #
    # El `REVOKE` no es decorativo: los privilegios por defecto de la base conceden `arwd` a
    # `agenda_api` y `SELECT` a `agenda_publico` sobre **toda** tabla nueva. Sin quitarlos, esta
    # tabla nacería con permiso de borrado y con el rol del marketplace pudiendo leerla el día
    # que alguien le escriba una política por descuido.
    op.execute("REVOKE ALL ON staff_clock_events FROM agenda_api, agenda_publico")
    op.execute("GRANT SELECT, INSERT ON staff_clock_events TO agenda_api")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON staff_clock_events TO agenda_admin")

    op.execute(
        """
        ALTER TABLE staff_clock_events ENABLE ROW LEVEL SECURITY;
        ALTER TABLE staff_clock_events FORCE ROW LEVEL SECURITY;

        -- La condición de escritura lleva dentro el interruptor del dueño: **no se puede
        -- apuntar el fichaje de quien no lo tiene encendido**, lo intente la pantalla, un
        -- trabajo en segundo plano o un endpoint que se escriba dentro de seis meses.
        CREATE POLICY staff_clock_events_tenant ON staff_clock_events
          FOR ALL TO agenda_api
          USING (business_id = app_negocio_actual())
          WITH CHECK (
            business_id = app_negocio_actual()
            AND EXISTS (
              SELECT 1 FROM staff_profiles s
               WHERE s.id = staff_clock_events.staff_id
                 AND s.business_id = staff_clock_events.business_id
                 AND s.clock_in_enabled
                 AND s.deleted_at IS NULL
            )
          );

        CREATE POLICY staff_clock_events_admin ON staff_clock_events
          FOR ALL TO agenda_admin USING (true) WITH CHECK (true);

        -- Su fichaje, el de nadie más. Quién entró y salió cada día es de la persona y del
        -- dueño; entre compañeros, no.
        CREATE POLICY staff_clock_events_profesional ON staff_clock_events
          AS RESTRICTIVE FOR ALL TO agenda_api
          USING      (app_profesional_actual() IS NULL
                      OR staff_id = app_profesional_actual())
          WITH CHECK (app_profesional_actual() IS NULL
                      OR staff_id = app_profesional_actual());
        """
    )

    # `staff_clock_events` **no aparece** en ninguna lista de tablas publicables, y aquí queda
    # escrito por qué: no hay dato laboral que tenga que ver un desconocido en internet.


def _puerta_de_las_invitaciones() -> None:
    op.execute(
        """
        -- Hermano de `app_negocio_actual()`, `app_usuario_actual()` y
        -- `app_profesional_actual()`. Devuelve NULL cuando nadie ha presentado una invitación,
        -- y ese NULL es lo que deja las políticas de abajo sin efecto en el resto del sistema.
        CREATE OR REPLACE FUNCTION app_invitacion_actual() RETURNS bytea
        LANGUAGE sql STABLE PARALLEL SAFE AS $$
          SELECT decode(nullif(current_setting('app.current_invite', true), ''), 'hex');
        $$;
        """
    )

    op.execute(
        """
        -- Ver **la invitación que se presenta**, y nada más. No se compara un identificador que
        -- se pueda enumerar: se compara el hash del token, así que solo la ve quien lo tiene.
        CREATE POLICY memberships_por_invitacion ON memberships
          FOR SELECT TO agenda_api
          USING (
            app_invitacion_actual() IS NOT NULL
            AND invite_token_hash IS NOT NULL
            AND invite_token_hash = app_invitacion_actual()
          );

        -- Y aceptarla. La caducidad y el estado se comprueban **en la política**, no solo en el
        -- código: un token vencido no puede abrir nada aunque el endpoint se despiste. El
        -- `WITH CHECK` obliga además a que la fila resultante quede `activa`, para que este
        -- permiso no sirva para dejar la membresía en ningún otro sitio.
        CREATE POLICY memberships_aceptar_invitacion ON memberships
          FOR UPDATE TO agenda_api
          USING (
            app_invitacion_actual() IS NOT NULL
            AND invite_token_hash IS NOT NULL
            AND invite_token_hash = app_invitacion_actual()
            AND status = 'invitada'
            AND revoked_at IS NULL
            AND invite_expires_at > now()
          )
          WITH CHECK (status = 'activa');
        """
    )


#: Catálogo global que el marketplace **sí** tiene que poder leer y que no lleva seguridad por
#: fila porque no es de ningún negocio. Sale tal cual de la lista `globales` de la migración
#: 0001: aquí no se decide qué es público, solo se respeta lo que ya estaba decidido.
CATALOGOS_PUBLICOS = (
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
    # De PostGIS, no nuestra. Sin ella no funcionan las conversiones de sistema de referencia.
    "spatial_ref_sys",
)


def _cerrar_el_rol_publico() -> None:
    """Le quita al rol del marketplace el permiso de lectura sobre lo que no es público.

    **Esto arregla un agujero real, encontrado al escribir la prueba del mapa.** El entorno
    concede privilegios por defecto —`ALTER DEFAULT PRIVILEGES … GRANT SELECT … TO
    agenda_publico` en `infra/local/init/01-roles.sql`— sobre **toda** tabla que cree
    `agenda_owner`. El efecto es que `agenda_publico` acabó con `SELECT` sobre las 68 tablas del
    esquema, incluidas las que **no llevan seguridad por fila** porque no son de ningún negocio:
    `users`, `auth_identities`, `otp_codes`, `sessions`, `admin_users`, `admin_sessions`,
    `client_profiles`, `user_consents`, `privacy_requests`, `favorites`.

    Sin política que lo pare, ahí no hay cero filas: hay **todas**. Medido en la base de
    desarrollo antes de escribir esto: con el rol del marketplace, `SELECT * FROM users`
    devolvía los 34 usuarios del seed con su teléfono, su correo y su hash de contraseña. El
    marketplace no lo consultaba —los serializadores son explícitos y la bitácora 0001 ya daba
    por hecho que «el rol del marketplace no tiene permiso sobre `users`»— pero la garantía 3 de
    la constitución dice que ningún teléfono viaja en claro, y una garantía que depende de que
    ningún endpoint futuro escriba la consulta equivocada no es una garantía.

    La regla que se aplica se puede decir en una frase y por eso se puede vigilar con una
    prueba: **si una tabla no tiene política para el rol público, tampoco tiene por qué tener
    permiso.** El catálogo global es la excepción explícita, porque no lleva políticas por
    diseño. Una tabla que alguien haga pública después seguirá teniendo su política de
    marketplace y no la toca este barrido.
    """
    # Y **el privilegio por defecto**, que es la otra mitad del agujero y la que muerde después.
    # Revocar las tablas de hoy no sirve de nada si la de mañana vuelve a nacer abierta: el
    # `ALTER DEFAULT PRIVILEGES` del entorno aplica a toda tabla que cree `agenda_owner` a
    # partir de ahora. Se quita aquí para las bases que ya existen; para las que se monten desde
    # cero se quitó en `infra/local/init/01-roles.sql`, que es donde estaba escrito.
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE agenda_owner IN SCHEMA public "
        "REVOKE SELECT ON TABLES FROM agenda_publico"
    )

    op.execute(
        f"""
        DO $$
        DECLARE tabla text;
        BEGIN
          FOR tabla IN
            SELECT c.relname
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public'
               AND c.relkind = 'r'
               AND c.relname <> ALL (ARRAY[{", ".join(f"'{t}'" for t in CATALOGOS_PUBLICOS)}])
               AND has_table_privilege('agenda_publico', c.oid, 'SELECT')
               AND NOT EXISTS (
                 SELECT 1 FROM pg_policy p
                  WHERE p.polrelid = c.oid
                    AND 'agenda_publico'::regrole = ANY (p.polroles)
               )
          LOOP
            EXECUTE format('REVOKE SELECT ON %I FROM agenda_publico', tabla);
          END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS memberships_aceptar_invitacion ON memberships")
    op.execute("DROP POLICY IF EXISTS memberships_por_invitacion ON memberships")
    op.execute("DROP FUNCTION IF EXISTS app_invitacion_actual()")

    op.execute("DROP TABLE IF EXISTS staff_clock_events")
    op.execute("DROP TABLE IF EXISTS business_banners")

    op.drop_column("staff_profiles", "clock_in_enabled")
