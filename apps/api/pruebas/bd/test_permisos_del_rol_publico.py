"""El rol del marketplace solo lee lo que es público. Vigilado en el catálogo, no en el código.

Esta prueba nace de un agujero de verdad, encontrado al escribir la del mapa. El entorno local
concede privilegios por defecto al rol público sobre **toda** tabla que cree el dueño del
esquema (`infra/local/init/01-roles.sql`), así que `agenda_publico` acabó con `SELECT` sobre las
68 tablas. En las que llevan seguridad por fila eso no se nota —sin política, cero filas— pero
en las que **no** la llevan porque no son de ningún negocio, sí: con el rol del marketplace,
`SELECT * FROM users` devolvía todos los usuarios con su teléfono, su correo y su hash de
contraseña.

La migración 0010 lo cierra, y esto es lo que impide que vuelva. La regla cabe en una frase:

> **Si una tabla no tiene política para el rol público, tampoco tiene por qué tener permiso.**

Con una sola excepción, explícita: el catálogo global —zonas, categorías, feriados, planes—, que
no lleva políticas porque no es de nadie y sí tiene que poder leerse.

Es la hermana de `test_catalogo_rls.py`, y falla por el mismo motivo: porque alguien añadió algo
y la garantía se quedó fuera. Como aquella, **no se desactiva**; si aparece una tabla nueva que
de verdad es pública, lo que se le escribe es su política.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.bd

#: Copiada de la migración 0010, a propósito y no importada: si alguien amplía la lista de allí
#: para acallar esta prueba, la copia de aquí lo enseña en el mismo diff.
CATALOGOS_PUBLICOS = {
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
    "spatial_ref_sys",
}


async def test_ninguna_tabla_sin_politica_publica_tiene_permiso_de_lectura(sesion):
    """Si esta prueba falla, hay una tabla que el marketplace puede leer entera."""
    filas = await sesion.execute(
        text(
            """
            SELECT c.relname
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = 'public'
               AND c.relkind = 'r'
               AND has_table_privilege('agenda_publico', c.oid, 'SELECT')
               AND NOT EXISTS (
                 SELECT 1 FROM pg_policy p
                  WHERE p.polrelid = c.oid
                    AND 'agenda_publico'::regrole = ANY (p.polroles)
               )
             ORDER BY c.relname
            """
        )
    )
    colgando = {fila[0] for fila in filas} - CATALOGOS_PUBLICOS

    assert not colgando, (
        "El rol del marketplace tiene permiso de lectura sobre estas tablas y ninguna política "
        f"que lo acote: {sorted(colgando)}. En las que no llevan seguridad por fila eso "
        "significa que las lee **enteras**. O se les escribe su política de marketplace, o se "
        "les quita el permiso en la migración."
    )


async def test_las_tablas_de_identidad_le_estan_cerradas_al_marketplace(sesion):
    """Las que guardan credenciales, nombradas una a una.

    La prueba de arriba las cubriría, pero esta las nombra: cuando algo se rompe, leer
    «`users` es legible por el rol del marketplace» explica el problema entero en una línea.
    """
    cerradas = (
        "users",
        "auth_identities",
        "otp_codes",
        "sessions",
        "admin_users",
        "admin_sessions",
        "client_profiles",
        "user_consents",
        "privacy_requests",
        "business_clients",
        "bookings",
        "memberships",
        "staff_clock_events",
    )
    abiertas = []
    for tabla in cerradas:
        puede = (
            await sesion.execute(
                text("SELECT has_table_privilege('agenda_publico', :tabla, 'SELECT')"),
                {"tabla": tabla},
            )
        ).scalar_one()
        if puede:
            abiertas.append(tabla)

    assert not abiertas, f"El rol del marketplace puede leer datos personales de: {abiertas}"
