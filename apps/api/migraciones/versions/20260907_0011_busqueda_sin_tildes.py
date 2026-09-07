"""Buscar «barberia» tiene que encontrar «Barbería».

Revision ID: 0011_busqueda_sin_tildes
Revises: 0010_portal_del_dueno
Create Date: 2026-09-07

Escribir la tilde en el teclado de un teléfono cuesta una pulsación larga, así que casi nadie
la escribe. Hasta ahora `texto=barberia` devolvía **cero resultados** y `texto=barbería` devolvía
dos: el buscador funcionaba solo para quien ya escribía perfecto. En un marketplace en español
eso no es un detalle de calidad, es la mitad de las búsquedas cayendo al vacío.

Tres piezas:

* **La extensión `unaccent`**, que ya venía en la imagen y solo había que encender.

* **`sin_tildes(text)`**, una envoltura marcada `IMMUTABLE`. Hace falta porque `unaccent()` es
  `STABLE` —depende del diccionario, que en teoría se puede recargar— y PostgreSQL no deja
  indexar una función que no promete devolver siempre lo mismo. La envoltura fija el diccionario
  por nombre y hace esa promesa; es el patrón habitual y el motivo por el que existe.

* **Dos índices** sobre `sin_tildes(lower(...))` con `gin_trgm_ops`. Sin ellos la consulta hace
  recorrido secuencial y calcula la función para cada fila: con cinco mil negocios eso se nota, y
  el presupuesto de la búsqueda es de 500 ms.
"""

from __future__ import annotations

from alembic import op

revision = "0011_busqueda_sin_tildes"
down_revision = "0008_acceso_contrasena"  # PROVISIONAL: se re-encadena a 0010 al fusionar
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    # `pg_trgm` es lo que hace que un `LIKE '%algo%'` pueda usar índice. Sin él, el índice de
    # abajo no sirve para buscar por el medio de la palabra, que es justo como se busca aquí.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION sin_tildes(texto text)
        RETURNS text
        LANGUAGE sql
        IMMUTABLE
        PARALLEL SAFE
        STRICT
        AS $$ SELECT public.unaccent('public.unaccent', texto) $$
        """
    )

    op.execute(
        "CREATE INDEX ix_businesses_nombre_sin_tildes ON businesses "
        "USING gin (sin_tildes(lower(display_name)) gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_services_nombre_sin_tildes ON services "
        "USING gin (sin_tildes(lower(name)) gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_services_nombre_sin_tildes")
    op.execute("DROP INDEX IF EXISTS ix_businesses_nombre_sin_tildes")
    op.execute("DROP FUNCTION IF EXISTS sin_tildes(text)")
    # Las extensiones no se quitan: puede haber otra cosa usándolas y quitarlas rompería más de
    # lo que arregla.
