"""Entrar con correo y contraseña, en vez de con un código de un solo uso.

Revision ID: 0008_acceso_contrasena
Revises: 0007_resenas_publicas
Create Date: 2026-09-07

El acceso por código tenía sentido cuando el teléfono verificado era **la** identidad. En
desarrollo es un estorbo: para mirar una pantalla hay que pedir un código, buscarlo y teclearlo
antes de que caduque a los cinco minutos. Decisión del director: correo y contraseña, y más
adelante segundo factor **opcional** y entrada con Google o Apple.

Tres cambios, y el segundo es el que de verdad importa:

* **`users.password_hash`**, admite nulo. Nulo no es «sin contraseña insegura»: es «esta
  persona entra por otra vía» —el código de siempre, y mañana Google o Apple—. Quien no tiene
  contraseña no puede entrar con contraseña, y punto.

* **`users.phone_e164` pasa a admitir nulo.** Si el correo es lo que identifica, exigir un
  teléfono para poder existir convierte el alta en el mismo trámite que se quería quitar. El
  único por teléfono sigue en pie: en PostgreSQL los nulos no chocan entre sí, así que muchas
  cuentas sin teléfono conviven y dos con el mismo número siguen siendo imposibles. **El
  teléfono no desaparece del producto**: se pide y se verifica antes de la primera reserva,
  que es donde de verdad hace falta (D9), porque el salón tiene que poder llamar.

* **`auth_identities` admite el proveedor `email`.** La tabla enumera con qué demuestras quién
  eres, y hasta ahora solo contemplaba teléfono, Google y Apple. Sin este valor, el alta con
  correo revienta contra la restricción en la primera fila.

* **`failed_logins` y `locked_until`.** Una contraseña sin freno se prueba a diez mil por
  segundo. El código de un solo uso traía su límite de fábrica —cinco intentos y caduca—; al
  cambiar de método hay que traerse el freno, o el cambio es un retroceso de seguridad
  disfrazado de comodidad.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_acceso_contrasena"
down_revision = "0007_resenas_publicas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column("failed_logins", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("users", "phone_e164", existing_type=sa.Text(), nullable=True)

    # El correo deja de ser un dato de contacto para ser una credencial, así que se guarda
    # siempre en minúsculas. El único ya era `lower(email)`; sin normalizar al escribir,
    # «Ana@x.com» y «ana@x.com» son la misma cuenta para el índice y dos cadenas distintas para
    # cualquier comparación del código, que es como se cuela un «no existe» con la contraseña
    # correcta.
    op.execute("UPDATE users SET email = lower(email) WHERE email IS NOT NULL")

    # En SQL crudo y no con `create_check_constraint`, que le antepone `ck_<tabla>_` por
    # convención de nombres y acabaría creando `ck_auth_identities_ck_auth_identities_...`.
    op.execute("ALTER TABLE auth_identities DROP CONSTRAINT ck_auth_identities_provider_valido")
    op.execute(
        "ALTER TABLE auth_identities ADD CONSTRAINT ck_auth_identities_provider_valido "
        "CHECK (provider IN ('telefono','email','google','apple'))"
    )


def downgrade() -> None:
    # Volver atrás con cuentas que solo tienen correo dejaría filas sin teléfono contra una
    # columna obligatoria. Se borran las sesiones y se vacían esas cuentas antes de restaurar
    # la restricción; es destructivo y por eso está escrito, no improvisado.
    op.execute("DELETE FROM auth_identities WHERE provider = 'email'")
    op.execute("ALTER TABLE auth_identities DROP CONSTRAINT ck_auth_identities_provider_valido")
    op.execute(
        "ALTER TABLE auth_identities ADD CONSTRAINT ck_auth_identities_provider_valido "
        "CHECK (provider IN ('telefono','google','apple'))"
    )
    op.execute(
        "DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE phone_e164 IS NULL)"
    )
    op.execute("DELETE FROM users WHERE phone_e164 IS NULL")
    op.alter_column("users", "phone_e164", existing_type=sa.Text(), nullable=False)
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_logins")
    op.drop_column("users", "password_hash")
