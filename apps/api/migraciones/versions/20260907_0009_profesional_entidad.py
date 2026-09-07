"""El profesional pasa a ser una entidad de primera, con perfil público propio.

Revision ID: 0009_profesional_entidad
Revises: 0008_acceso_contrasena
Create Date: 2026-09-07

Hasta ahora el profesional era una fila del equipo de un salón: un nombre, una bio y una foto
que solo se veían dentro de la ficha del negocio. El encargo del 7 de septiembre lo cambia de
raíz — **la clienta elige primero con quién se quiere atender** — y eso necesita cuatro cosas
que la base no tenía.

* **`staff_profiles` gana su identidad pública**: `slug` (la URL de su perfil, **único por
  negocio y no global**, porque la misma persona puede trabajar en dos salones), `headline`
  —la descripción de una línea, distinta de la `bio` larga—, `instagram`, `facebook` y `x`, y
  `years_experience`.

  Las tres redes guardan **el usuario, no la URL**, y eso se defiende con una restricción y no
  con la buena costumbre del endpoint: en los patrones que se admiten no cabe ni una barra ni
  dos puntos, así que un enlace a cualquier sitio no entra ni aunque un endpoint futuro se
  olvide de normalizar. Un perfil público con un campo de enlace libre es un tablón de
  anuncios ajeno esperando a que alguien lo descubra.

* **`staff_media`, la tabla nueva.** `service_id` **admite nulo** y ahí está toda la idea: una
  foto atada a un servicio dice «esto lo hizo esta persona»; una foto suelta es su galería.

* **La política del rol público para `staff_media`** —patrón B de ADR-0002— atada a las dos
  condiciones que apagan un perfil de una vez: que el negocio esté **publicado** y que la
  ficha esté **activa y visible en el marketplace**. Una tabla nueva con seguridad por fila y
  sin política no significa «se ve todo»: significa que **no se ve nada**, y eso se descubre
  mirando una galería vacía sin entender por qué.

* **`staff_services` se abre al rol público.** Sin ella no se puede contestar «qué servicios
  hace esta persona», que es literalmente el segundo paso del camino nuevo —profesional →
  servicio suyo → hora—. Va con su política, atada a lo mismo.

Y un recorte que hay que **abrir** con cuidado. La migración 0006 cerró a cal y canto la
escritura de `staff_profiles` para el profesional: la ficha la gestiona el dueño. Eso sigue
siendo cierto para la ficha **de otro**, pero el encargo pide que cada quien edite **la suya**,
así que la política restrictiva de `UPDATE` pasa de «ningún profesional escribe aquí» a «cada
profesional escribe su propia fila». Sigue sin poder crear fichas ni borrarlas, y sigue sin
poder tocar la de su compañera — eso lo impide PostgreSQL, no el endpoint.

**Qué campos puede cambiar de su propia fila lo decide la aplicación**, no la base: `activo`,
`visible en el marketplace` y el orden en la lista son del dueño y el endpoint del profesional
ni los acepta. La base no puede distinguir columnas dentro de una misma fila para un mismo rol,
así que aquí se protege lo que la base sabe proteger —de quién es la fila— y el resto se
escribe además en el código, como manda ADR-0002.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_profesional_entidad"
down_revision = "0008_acceso_contrasena"
branch_labels = None
depends_on = None

#: Las tildes y la eñe **se transliteran, no se tiran**, igual que en `agenda.dominio.textos`:
#: «Marielys Peña» tiene que dar `marielys-pena` y no `marielys-pe-a`. Aquí se hace con
#: `translate` porque `unaccent` es una extensión que este proyecto no instala, y añadir una
#: extensión para rellenar una columna una vez sería pagar para siempre por un rato.
ACENTOS = "áàäâãÁÀÄÂÃéèëêÉÈËÊíìïîÍÌÏÎóòöôõÓÒÖÔÕúùüûÚÙÜÛñÑçÇ"
LLANAS = "aaaaaAAAAAeeeeEEEEiiiiIIIIoooooOOOOOuuuuUUUUnNcC"


def upgrade() -> None:
    _identidad_publica_del_profesional()
    _tabla_de_fotos()
    _lo_que_ve_el_marketplace()
    _lo_que_puede_editar_el_profesional()


# ── El perfil ─────────────────────────────────────────────────────────────────────────────


def _identidad_publica_del_profesional() -> None:
    op.add_column("staff_profiles", sa.Column("slug", sa.Text(), nullable=True))
    op.add_column("staff_profiles", sa.Column("headline", sa.Text(), nullable=True))
    op.add_column("staff_profiles", sa.Column("instagram", sa.Text(), nullable=True))
    op.add_column("staff_profiles", sa.Column("facebook", sa.Text(), nullable=True))
    op.add_column("staff_profiles", sa.Column("x", sa.Text(), nullable=True))
    op.add_column("staff_profiles", sa.Column("years_experience", sa.SmallInteger(), nullable=True))

    # El relleno va **antes** del único, o el único falla en el primer salón con dos Karolinas.
    # El desempate es por identificador y no por fecha: `id` es UUID v7 y ya ordena por
    # creación, así que la primera Karolina se queda con `karolina` y la segunda con
    # `karolina-2`, que es lo que esperaría cualquiera.
    op.execute(
        f"""
        WITH candidatos AS (
          SELECT id,
                 business_id,
                 coalesce(
                   nullif(
                     regexp_replace(
                       regexp_replace(
                         lower(translate(display_name, '{ACENTOS}', '{LLANAS}')),
                         '[^a-z0-9]+', '-', 'g'),
                       '(^-+)|(-+$)', '', 'g'),
                     ''),
                   'profesional') AS base
            FROM staff_profiles
           WHERE slug IS NULL
        ),
        numerados AS (
          SELECT id,
                 base,
                 row_number() OVER (PARTITION BY business_id, base ORDER BY id) AS puesto
            FROM candidatos
        )
        UPDATE staff_profiles s
           SET slug = CASE WHEN n.puesto = 1 THEN n.base
                           ELSE n.base || '-' || n.puesto END
          FROM numerados n
         WHERE s.id = n.id;
        """
    )

    # Único **por negocio** y solo entre los vivos: una ficha dada de baja no puede quedarse
    # ocupando el nombre bonito de quien llega en su lugar.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_staff_profiles_business_id_slug
          ON staff_profiles (business_id, slug)
          WHERE slug IS NOT NULL AND deleted_at IS NULL;
        """
    )

    for nombre, condicion in (
        ("ck_staff_profiles_slug_valido", "slug IS NULL OR slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'"),
        (
            "ck_staff_profiles_instagram_usuario",
            "instagram IS NULL OR instagram ~ '^[A-Za-z0-9._]{1,30}$'",
        ),
        (
            "ck_staff_profiles_facebook_usuario",
            "facebook IS NULL OR facebook ~ '^[A-Za-z0-9.]{1,50}$'",
        ),
        ("ck_staff_profiles_x_usuario", "x IS NULL OR x ~ '^[A-Za-z0-9_]{1,15}$'"),
        (
            "ck_staff_profiles_years_experience_rango",
            "years_experience IS NULL OR years_experience BETWEEN 0 AND 80",
        ),
    ):
        op.execute(f"ALTER TABLE staff_profiles ADD CONSTRAINT {nombre} CHECK ({condicion})")


# ── Las fotos ─────────────────────────────────────────────────────────────────────────────


def _tabla_de_fotos() -> None:
    op.execute(
        """
        CREATE TABLE staff_media (
          id                uuid        NOT NULL,
          business_id       uuid        NOT NULL,
          staff_id          uuid        NOT NULL,
          service_id        uuid,
          storage_key       text        NOT NULL,
          alt_text          text,
          position          smallint    NOT NULL DEFAULT 0,
          moderation_status text        NOT NULL DEFAULT 'aprobada',
          created_at        timestamptz NOT NULL DEFAULT now(),
          CONSTRAINT pk_staff_media PRIMARY KEY (id),
          CONSTRAINT fk_staff_media_business_id_businesses
            FOREIGN KEY (business_id) REFERENCES businesses (id) ON DELETE RESTRICT,
          CONSTRAINT fk_staff_media_staff_id_staff_profiles
            FOREIGN KEY (staff_id) REFERENCES staff_profiles (id) ON DELETE CASCADE,
          -- `SET NULL` y no `CASCADE`: si el salón retira el servicio, el trabajo hecho no
          -- desaparece del portafolio de quien lo hizo, solo deja de estar atado a él.
          CONSTRAINT fk_staff_media_service_id_services
            FOREIGN KEY (service_id) REFERENCES services (id) ON DELETE SET NULL,
          CONSTRAINT ck_staff_media_moderacion_valida
            CHECK (moderation_status IN ('pendiente','aprobada','rechazada'))
        );
        """
    )
    op.execute("CREATE INDEX ix_staff_media_business_id ON staff_media (business_id)")
    op.execute(
        "CREATE INDEX ix_staff_media_business_id_staff_id "
        "ON staff_media (business_id, staff_id, position)"
    )
    op.execute(
        "CREATE INDEX ix_staff_media_service_id ON staff_media (service_id) "
        "WHERE service_id IS NOT NULL"
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON staff_media TO agenda_api, agenda_admin")
    # El permiso y la política van juntos **siempre**. Con permiso y sin política la consulta
    # devuelve cero filas y parece un fallo del código; con política y sin permiso salta un
    # error de permisos que tampoco dice lo que pasa.
    op.execute("GRANT SELECT ON staff_media TO agenda_publico")

    op.execute("ALTER TABLE staff_media ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE staff_media FORCE ROW LEVEL SECURITY")

    # Patrón A de ADR-0002 — la tabla es del negocio.
    op.execute(
        """
        CREATE POLICY staff_media_tenant ON staff_media
          FOR ALL TO agenda_api
          USING      (business_id = app_negocio_actual())
          WITH CHECK (business_id = app_negocio_actual());
        """
    )
    op.execute(
        "CREATE POLICY staff_media_admin ON staff_media "
        "FOR ALL TO agenda_admin USING (true) WITH CHECK (true)"
    )

    # Y el recorte de la 0006 aplicado a la tabla nueva: **sus fotos, no las de su compañera**.
    # Restrictiva, que es la única clase de política que quita acceso; una permisiva se
    # crearía, se aplicaría, no fallaría y no restringiría nada.
    op.execute(
        """
        CREATE POLICY staff_media_profesional ON staff_media
          AS RESTRICTIVE FOR ALL TO agenda_api
          USING      (app_profesional_actual() IS NULL
                      OR staff_id = app_profesional_actual())
          WITH CHECK (app_profesional_actual() IS NULL
                      OR staff_id = app_profesional_actual());
        """
    )


# ── La cara pública ───────────────────────────────────────────────────────────────────────


def _lo_que_ve_el_marketplace() -> None:
    """Patrón B de ADR-0002: una **segunda** política para el rol público, no una relajación.

    Las dos condiciones son las mismas que ya gobiernan `staff_profiles`: negocio publicado y
    ficha activa y visible. Así, ocultar a un profesional del marketplace apaga su galería en
    el mismo gesto, y despublicar el salón apaga el perfil entero de una vez — no tabla a
    tabla desde la aplicación, que es como se queda una encendida.
    """
    profesional_visible = """
        EXISTS (
          SELECT 1 FROM staff_profiles p
           WHERE p.id = {tabla}.staff_id
             AND p.active
             AND p.visible_in_marketplace
             AND p.deleted_at IS NULL
        )
        AND EXISTS (
          SELECT 1 FROM businesses b
           WHERE b.id = {tabla}.business_id
             AND b.status = 'publicado'
             AND b.deleted_at IS NULL
        )
    """

    op.execute(
        f"""
        CREATE POLICY staff_media_marketplace ON staff_media
          FOR SELECT TO agenda_publico
          USING (
            moderation_status = 'aprobada'
            AND {profesional_visible.format(tabla="staff_media")}
          );
        """
    )

    # «Qué servicios hace esta persona» es el segundo paso del camino nuevo. Sin esto, la
    # respuesta pública sería una lista vacía y no un error, que es la peor forma de fallar.
    op.execute("GRANT SELECT ON staff_services TO agenda_publico")
    op.execute(
        f"""
        CREATE POLICY staff_services_marketplace ON staff_services
          FOR SELECT TO agenda_publico
          USING ({profesional_visible.format(tabla="staff_services")});
        """
    )


# ── Lo que cada quien puede tocar ─────────────────────────────────────────────────────────


def _lo_que_puede_editar_el_profesional() -> None:
    """Su ficha sí; la de su compañera, no. Lo decide PostgreSQL.

    La 0006 escribió `staff_profiles_profesional_no_configura_update` con la condición
    «ningún profesional escribe aquí». Se sustituye por «cada quien escribe su propia fila».
    `INSERT` y `DELETE` **se quedan como estaban**: dar de alta y dar de baja a alguien es del
    dueño, y una ficha borrada por su propio titular se llevaría por delante su historial de
    agenda.
    """
    op.execute(
        "DROP POLICY IF EXISTS staff_profiles_profesional_no_configura_update ON staff_profiles"
    )
    op.execute(
        """
        CREATE POLICY staff_profiles_profesional_edita_lo_suyo ON staff_profiles
          AS RESTRICTIVE FOR UPDATE TO agenda_api
          USING      (app_profesional_actual() IS NULL OR id = app_profesional_actual())
          WITH CHECK (app_profesional_actual() IS NULL OR id = app_profesional_actual());
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS staff_profiles_profesional_edita_lo_suyo ON staff_profiles")
    op.execute(
        """
        CREATE POLICY staff_profiles_profesional_no_configura_update ON staff_profiles
          AS RESTRICTIVE FOR UPDATE TO agenda_api
          USING      (app_profesional_actual() IS NULL)
          WITH CHECK (app_profesional_actual() IS NULL);
        """
    )

    op.execute("DROP POLICY IF EXISTS staff_services_marketplace ON staff_services")
    op.execute("REVOKE SELECT ON staff_services FROM agenda_publico")

    op.execute("DROP TABLE IF EXISTS staff_media")

    for nombre in (
        "ck_staff_profiles_slug_valido",
        "ck_staff_profiles_instagram_usuario",
        "ck_staff_profiles_facebook_usuario",
        "ck_staff_profiles_x_usuario",
        "ck_staff_profiles_years_experience_rango",
    ):
        op.execute(f"ALTER TABLE staff_profiles DROP CONSTRAINT IF EXISTS {nombre}")
    op.execute("DROP INDEX IF EXISTS uq_staff_profiles_business_id_slug")
    for columna in ("slug", "headline", "instagram", "facebook", "x", "years_experience"):
        op.execute(f"ALTER TABLE staff_profiles DROP COLUMN IF EXISTS {columna}")
