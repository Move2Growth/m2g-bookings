"""Un profesional ve y gestiona su agenda, y nada más.

Revision ID: 0006_agenda_profesional
Revises: 0005_mis_negocios
Create Date: 2026-09-02

STF-3 dice que el dueño lo ve todo y el profesional ve **su agenda y sus clientes, sin
finanzas ni configuración**. Hasta ahora eso vivía en un `if` dentro del endpoint de la
agenda, y un `if` en un endpoint solo protege ese endpoint: el siguiente que alguien escriba
nace desprotegido y nadie se entera hasta que un profesional cuenta que ve las citas de su
compañera.

Aquí se mueve a la base de datos, con el mismo mecanismo que el aislamiento entre negocios:
**se declara quién pregunta** —`app.current_staff_id`, hermano de `app.current_business_id`—
y las políticas hacen el resto.

**Por qué son políticas RESTRICTIVAS y no permisivas.** En PostgreSQL las políticas normales
se suman con OR: añadir una más nunca quita acceso, solo lo amplía. Para *recortar* lo que ya
concede la política de tenant hace falta `AS RESTRICTIVE`, que se combina con AND. Escribirlas
permisivas sería el fallo silencioso perfecto: se crean, se aplican, no fallan y no restringen
nada.

Todas comparten la misma forma:

    app_profesional_actual() IS NULL  OR  <la condición que le toca>

El `IS NULL` es lo que deja intacto al dueño y a los trabajos en segundo plano: si nadie ha
declarado un profesional, la política no estorba. Un profesional no puede «desdeclararse»,
porque quien pone ese ajuste es la dependencia de sesión a partir del rol del token, no el
cliente.
"""

from __future__ import annotations

from alembic import op

revision = "0006_agenda_profesional"
down_revision = "0005_mis_negocios"
branch_labels = None
depends_on = None

#: **Su agenda, la de nadie más.** Lectura y escritura acotadas a sus propias filas.
TABLAS_DE_SU_AGENDA = {
    "bookings": "staff_id = app_profesional_actual()",
    "staff_occupancy": "staff_id = app_profesional_actual()",
    # El horario propio y sus descansos son suyos: puede ponerse el almuerzo sin pedir permiso.
    "staff_hours": "staff_id = app_profesional_actual()",
    # `time_block_rules.staff_id` es nulable y NULL significa «todo el equipo». La comparación
    # con NULL da NULL, que no es cierto, así que la regla del equipo entero le queda cerrada:
    # eso lo decide el dueño.
    "time_block_rules": "staff_id = app_profesional_actual()",
}

#: Cuelgan de una reserva y heredan su dueño. Se comprueban con un `EXISTS` sobre `bookings`
#: en vez de duplicar `staff_id`: una columna copiada es una columna que algún día no coincide.
TABLAS_COLGADAS_DE_LA_RESERVA = ("booking_items", "booking_events")

#: **La configuración se lee pero no se toca.** El profesional necesita ver los servicios para
#: entender su propia agenda —de qué es la cita de las 10— pero cambiarles el precio no es
#: cosa suya.
TABLAS_DE_SOLO_LECTURA = (
    "businesses",
    "business_settings",
    "business_hours",
    "business_media",
    "business_categories",
    "business_attributes",
    "locations",
    "services",
    "service_variants",
    "staff_profiles",
    "staff_services",
    "memberships",
    "reviews",
    "review_replies",
    "review_reports",
    "review_media",
    "business_rating_stats",
    "business_ranking_signals",
    "listing_impressions_daily",
    "listing_clicks_daily",
)

#: **Las finanzas no existen para el profesional.** Ni lectura: cuánto factura el salón, qué
#: plan tiene y qué se le ha cobrado son del dueño. Aquí no se recorta el acceso, se cierra.
TABLAS_DE_FINANZAS = (
    "subscriptions",
    "subscription_events",
    "invoices",
    "payments",
    "payment_methods",
    "coupon_redemptions",
    "ad_campaigns",
    "ad_metrics_daily",
)


def upgrade() -> None:
    # Espejo de `app_negocio_actual()` y de `app_usuario_actual()`. Devuelve NULL cuando nadie
    # lo ha declarado, y ese NULL es el que desactiva todas las políticas de abajo para el
    # dueño y para los trabajos.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_profesional_actual() RETURNS uuid
        LANGUAGE sql STABLE PARALLEL SAFE AS $$
          SELECT nullif(current_setting('app.current_staff_id', true), '')::uuid;
        $$;
        """
    )

    for tabla, condicion in TABLAS_DE_SU_AGENDA.items():
        _restrictiva_total(tabla, f"app_profesional_actual() IS NULL OR ({condicion})")

    for tabla in TABLAS_COLGADAS_DE_LA_RESERVA:
        _restrictiva_total(
            tabla,
            "app_profesional_actual() IS NULL OR EXISTS ("
            f"  SELECT 1 FROM bookings b WHERE b.id = {tabla}.booking_id"
            "     AND b.staff_id = app_profesional_actual())",
        )

    # La ficha del cliente **se lee si es tuyo**: tuyo = te ha reservado alguna vez. El alta
    # queda abierta a propósito, porque el profesional apunta al que entra por la puerta
    # (AGD-2) y en ese instante todavía no hay reserva que lo relacione con él; la fila que
    # acaba de crear la ve enseguida, en cuanto la cita entra en la misma transacción.
    _restrictiva(
        "business_clients",
        "solo_sus_clientes",
        acciones=("SELECT", "UPDATE", "DELETE"),
        condicion=(
            "app_profesional_actual() IS NULL OR EXISTS ("
            "  SELECT 1 FROM bookings b WHERE b.business_client_id = business_clients.id"
            "     AND b.staff_id = app_profesional_actual())"
        ),
    )

    for tabla in TABLAS_DE_SOLO_LECTURA:
        # `SELECT` no aparece: leer sí puede. Lo que se cierra es escribir, y hay que cerrarlo
        # en las tres formas — `INSERT` mira `WITH CHECK`, `DELETE` mira `USING` y `UPDATE`
        # mira las dos. Cerrar solo una deja la puerta de al lado abierta.
        _restrictiva(
            tabla,
            "profesional_no_configura",
            acciones=("INSERT", "UPDATE", "DELETE"),
            condicion="app_profesional_actual() IS NULL",
        )

    for tabla in TABLAS_DE_FINANZAS:
        _restrictiva_total(tabla, "app_profesional_actual() IS NULL")


def _restrictiva_total(tabla: str, condicion: str) -> None:
    """Una sola política `FOR ALL`: la misma condición para leer y para escribir."""
    op.execute(
        f"""
        CREATE POLICY {tabla}_profesional ON {tabla}
          AS RESTRICTIVE FOR ALL TO agenda_api
          USING      ({condicion})
          WITH CHECK ({condicion});
        """
    )


def _restrictiva(tabla: str, sufijo: str, *, acciones: tuple[str, ...], condicion: str) -> None:
    """Una política por acción.

    PostgreSQL no deja escribir `FOR INSERT` con `USING` ni `FOR DELETE` con `WITH CHECK`, así
    que cada acción lleva la cláusula que le corresponde y ninguna más.
    """
    for accion in acciones:
        nombre = f"{tabla}_{sufijo}_{accion.lower()}"
        if accion == "INSERT":
            clausulas = f"WITH CHECK ({condicion})"
        elif accion == "UPDATE":
            clausulas = f"USING ({condicion}) WITH CHECK ({condicion})"
        else:
            clausulas = f"USING ({condicion})"
        op.execute(
            f"CREATE POLICY {nombre} ON {tabla} "
            f"AS RESTRICTIVE FOR {accion} TO agenda_api {clausulas};"
        )


def downgrade() -> None:
    for tabla in (*TABLAS_DE_SU_AGENDA, *TABLAS_COLGADAS_DE_LA_RESERVA, *TABLAS_DE_FINANZAS):
        op.execute(f"DROP POLICY IF EXISTS {tabla}_profesional ON {tabla}")

    for accion in ("select", "update", "delete"):
        op.execute(
            f"DROP POLICY IF EXISTS business_clients_solo_sus_clientes_{accion} "
            "ON business_clients"
        )

    for tabla in TABLAS_DE_SOLO_LECTURA:
        for accion in ("insert", "update", "delete"):
            op.execute(f"DROP POLICY IF EXISTS {tabla}_profesional_no_configura_{accion} ON {tabla}")

    op.execute("DROP FUNCTION IF EXISTS app_profesional_actual()")
