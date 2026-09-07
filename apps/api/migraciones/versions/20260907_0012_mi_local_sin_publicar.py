"""Quien tiene un salón puede verlo aunque todavía no lo haya publicado.

Revision ID: 0012_mi_local_sin_publicar
Revises: 0011_portal_del_dueno
Create Date: 2026-09-07

**Era un callejón sin salida.** `GET /mi/negocios` lee la membresía —para eso está la política
`memberships_propias` de la 0005— y la une con `businesses` para poder devolver el nombre. Pero
`businesses` solo tenía dos formas de dejarse leer: con el negocio fijado en la sesión, o siendo
público y estando publicado. Un salón en borrador no cumple ninguna, así que la unión lo tiraba y
la respuesta salía vacía.

El efecto en el producto: alguien crea su local, cierra sesión, vuelve a entrar y **su salón ya no
existe para él**. Y como publicarlo exige entrar al panel, no hay ninguna salida. Se reproduce con
la semilla sin tocar nada, con la cuenta de «Uñas por Vanessa», que está en borrador a propósito.

La política es de **solo lectura y solo de lo tuyo**: no afloja el aislamiento entre negocios,
porque no deja ver un salón ajeno ni deja escribir nada. Es la misma forma que ya usa «mis
reservas» desde la 0004: la persona se declara en `app.current_user_id` y la base filtra.
"""

from __future__ import annotations

from alembic import op

revision = "0012_mi_local_sin_publicar"
down_revision = "0011_portal_del_dueno"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE POLICY businesses_donde_trabajo ON businesses
          FOR SELECT TO agenda_api
          USING (
            app_usuario_actual() IS NOT NULL
            AND deleted_at IS NULL
            AND EXISTS (
              SELECT 1 FROM memberships m
               WHERE m.business_id = businesses.id
                 AND m.user_id = app_usuario_actual()
                 AND m.status = 'activa'
            )
          );
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS businesses_donde_trabajo ON businesses")
