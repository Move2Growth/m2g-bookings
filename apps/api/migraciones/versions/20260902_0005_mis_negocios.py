"""Una persona puede ver en qué negocios trabaja.

Revision ID: 0005_mis_negocios
Revises: 0004_reservas_cliente
Create Date: 2026-09-02

Mismo caso que «mis reservas» y con la misma solución. Las membresías están aisladas por
negocio, así que para saber en qué salones trabaja alguien hay que estar dentro de uno, y para
entrar en uno hay que saber en cuáles trabaja. Sin esto, un dueño entra y aterriza en la
pantalla de clienta, que es exactamente lo que hacía.

Se resuelve declarando **quién pregunta**, no aflojando el aislamiento: solo lectura y solo las
membresías propias. Lo que sigue sin poder hacerse desde aquí es escribir; dar de alta o
revocar a alguien sigue exigiendo estar dentro del negocio.
"""

from __future__ import annotations

from alembic import op

revision = "0005_mis_negocios"
down_revision = "0004_reservas_cliente"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE POLICY memberships_propias ON memberships
          FOR SELECT TO agenda_api
          USING (user_id = app_usuario_actual());
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS memberships_propias ON memberships")
