"""La prueba que vigila que nadie se olvide del aislamiento.

El coste de multi-tenant con seguridad por fila (ADR-0002) no está en escribirlo la primera
vez: está en **acordarse en la migración número cuarenta**, un martes, cuando alguien añade una
tabla nueva con `business_id` y se le pasa la política. Esa tabla queda visible entre negocios y
no falla nada, no avisa nadie y no se nota hasta que un salón ve los clientes de otro.

Por eso esto no se comprueba leyendo el código: se le pregunta al catálogo de PostgreSQL, que
es la única fuente que no puede mentir sobre lo que hay de verdad en la base.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.bd

#: Tablas que llevan `business_id` como **referencia a un negocio** y no como marca de
#: propiedad. Son de la plataforma, no de ningún salón, y aislarlas por negocio sería un error:
#: dejaría a cada persona sin ver lo suyo.
#:
#: Cada excepción se justifica aquí mismo y se contrasta con la columna «RLS» del modelo de
#: datos. La lista tiene que quedarse corta: si crece, lo que está pasando es que alguien la usa
#: para silenciar la prueba en vez de escribir la política.
EXCEPCIONES: set[str] = {
    # Los negocios que una persona guardó (MKT-5). La fila es del cliente, no del salón: si se
    # aislara por negocio, nadie vería su propia lista de favoritos.
    "favorites",
    # Qué avisos quiere recibir cada persona (NTF-3). Mismo caso: la preferencia es de quien la
    # configura, y el `business_id` solo dice a qué negocio se refiere.
    "notification_preferences",
}


async def test_toda_tabla_con_business_id_tiene_seguridad_por_fila(sesion):
    """Si esta prueba falla, hay una tabla por la que se pueden ver datos de otro negocio."""
    consulta = text(
        """
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_attribute a ON a.attrelid = c.oid
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
          AND a.attname = 'business_id'
          AND a.attnum > 0
          AND NOT a.attisdropped
          AND c.relrowsecurity IS FALSE
        ORDER BY c.relname
        """
    )
    resultado = await sesion.execute(consulta)
    sin_proteger = {fila[0] for fila in resultado} - EXCEPCIONES

    assert not sin_proteger, (
        "Estas tablas guardan datos de un negocio y no tienen seguridad por fila activada, "
        f"así que cualquier consulta puede ver los de otro: {sorted(sin_proteger)}. "
        "Actívala en la migración que las creó."
    )


async def test_toda_tabla_con_seguridad_por_fila_tiene_al_menos_una_politica(sesion):
    """Activar la seguridad sin escribir política deja la tabla **invisible**, no protegida.

    Es el fallo espejo del anterior y se manifiesta al revés: en vez de fugarse datos, la
    aplicación deja de ver los suyos. Se descubre rápido, pero conviene que lo descubra una
    prueba y no alguien mirando una lista vacía sin entender por qué.
    """
    consulta = text(
        """
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
          AND c.relrowsecurity IS TRUE
          AND NOT EXISTS (SELECT 1 FROM pg_policy p WHERE p.polrelid = c.oid)
        ORDER BY c.relname
        """
    )
    resultado = await sesion.execute(consulta)
    sin_politica = [fila[0] for fila in resultado]

    assert not sin_politica, (
        "Estas tablas tienen la seguridad por fila activada pero ninguna política, así que no "
        f"devuelven ni una fila a la aplicación: {sin_politica}."
    )


async def test_el_usuario_de_la_aplicacion_no_puede_saltarse_la_seguridad(sesion):
    """`BYPASSRLS` o ser dueño de las tablas anularían el aislamiento entero, en silencio.

    Un rol dueño se salta **sus propias** políticas sin que nada falle: las consultas siguen
    funcionando, devuelven de más, y no hay error que lo delate. De ahí que esto se compruebe.
    """
    resultado = await sesion.execute(
        text("SELECT current_user, rolbypassrls FROM pg_roles WHERE rolname = current_user")
    )
    usuario, puede_saltarse = resultado.one()

    assert not puede_saltarse, f"El rol {usuario} tiene BYPASSRLS: el aislamiento no existe."

    tablas_propias = await sesion.execute(
        text(
            """
            SELECT count(*)
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
              AND pg_get_userbyid(c.relowner) = current_user
            """
        )
    )
    assert tablas_propias.scalar_one() == 0, (
        f"El rol {usuario} es dueño de tablas y se saltaría sus propias políticas. "
        "La aplicación tiene que conectarse con un rol que no sea el dueño."
    )


async def test_las_extensiones_criticas_estan_instaladas(sesion):
    """Sin `btree_gist` no hay restricción de exclusión, y sin ella hay doble reserva."""
    resultado = await sesion.execute(text("SELECT extname FROM pg_extension ORDER BY extname"))
    extensiones = {fila[0] for fila in resultado}

    assert {"postgis", "btree_gist"} <= extensiones, (
        f"Faltan extensiones en la base: hay {sorted(extensiones)}. "
        "Se activan en la migración inicial, no a mano."
    )
