"""El cliente puede ver sus propias reservas, estén en el salón que estén.

Revision ID: 0004_reservas_cliente
Revises: 0003_monetizacion
Create Date: 2026-09-01

El aislamiento por negocio resuelve el 95 % de las consultas del producto, pero deja fuera una
que es esencial: **«mis reservas»**. Una persona que se corta el pelo en El Cangrejo y se hace
las uñas en Obarrio tiene citas en dos salones, y con el negocio fijado solo puede ver las de
uno. Con ninguno fijado, no ve ninguna.

La solución no es aflojar el aislamiento: es **declarar quién pregunta**, igual que ya se
declara en qué negocio se está. Aparece `app.current_user_id`, y con él una política que deja a
cada persona ver **sus** reservas —las que llevan su identificador— y nada más. Lo que sigue
sin poder hacer es escribir: reservar y cancelar siguen pasando por el negocio, que es donde
está la agenda.
"""

from __future__ import annotations

from alembic import op

revision = "0004_reservas_cliente"
down_revision = "0003_monetizacion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Espejo de `app_negocio_actual()`: lee el ajuste de sesión y devuelve NULL si no está.
    # `NULL` es importante — una política que compara contra NULL no deja pasar nada, que es
    # exactamente lo que debe ocurrir cuando nadie ha declarado quién pregunta.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_usuario_actual() RETURNS uuid
        LANGUAGE sql STABLE PARALLEL SAFE AS $$
          SELECT nullif(current_setting('app.current_user_id', true), '')::uuid;
        $$;
        """
    )

    # Solo lectura y solo lo suyo. Reservar y cancelar siguen exigiendo el negocio fijado: la
    # agenda es del salón, y una persona no puede escribir dentro de ella por el hecho de ser
    # su clienta.
    op.execute(
        """
        CREATE POLICY bookings_cliente ON bookings
          FOR SELECT TO agenda_api
          USING (client_user_id = app_usuario_actual());
        """
    )
    # Un negocio **publicado es dato público**: está en el marketplace, en Google y en la bio
    # de Instagram de su dueño. Que el rol de la aplicación no pueda ni resolver su slug sin
    # estar dentro de él no protege nada y rompe lo evidente: una clienta que quiere reservar
    # todavía no está «dentro» de ningún salón. Los borradores siguen invisibles.
    op.execute(
        """
        CREATE POLICY businesses_publicados_lectura ON businesses
          FOR SELECT TO agenda_api
          USING (status = 'publicado' AND deleted_at IS NULL);
        """
    )

    # El detalle de la cita —qué servicios, a qué precio— viaja con ella. Sin esto, «mis
    # reservas» enseñaría la hora pero no qué se reservó.
    op.execute(
        """
        CREATE POLICY booking_items_cliente ON booking_items
          FOR SELECT TO agenda_api
          USING (
            EXISTS (
              SELECT 1 FROM bookings b
              WHERE b.id = booking_items.booking_id
                AND b.client_user_id = app_usuario_actual()
            )
          );
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS businesses_publicados_lectura ON businesses")
    op.execute("DROP POLICY IF EXISTS booking_items_cliente ON booking_items")
    op.execute("DROP POLICY IF EXISTS bookings_cliente ON bookings")
    op.execute("DROP FUNCTION IF EXISTS app_usuario_actual()")
