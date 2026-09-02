"""Lo que le faltaba al marketplace para pintar una ficha completa.

Revision ID: 0007_resenas_publicas
Revises: 0006_agenda_profesional
Create Date: 2026-09-02

Dos huecos que se ven en cuanto se intenta pintar una tarjeta de resultado o una ficha de
salón, y que no son un olvido de nadie: hasta ahora nadie los había pedido.

* **El horario no era público.** `business_hours` tenía el permiso de lectura concedido a
  `agenda_publico` pero **ninguna política**, y con la seguridad por fila activada eso no
  significa «se ve todo»: significa que no se ve nada. Sin horario no hay «abierto ahora»
  (MKT-2) ni «hoy abre de 9 a 19» en la ficha (NEG-1).
* **Las fotos de las reseñas tampoco.** `reviews` y `review_replies` sí tenían su política de
  marketplace; `review_media` se quedó fuera y con ella las fotos de REV-2.

Las dos siguen el patrón B de ADR-0002 al pie de la letra: la política se ata a que el negocio
esté **publicado**, para que despublicar un salón apague su perfil entero de una vez y no
tabla a tabla desde la aplicación.
"""

from __future__ import annotations

from alembic import op

revision = "0007_resenas_publicas"
down_revision = "0006_agenda_profesional"
branch_labels = None
depends_on = None

#: Tabla → qué filas suyas son publicables. Misma forma que el diccionario `publicables` de la
#: migración 0002, para que las dos se lean igual.
PUBLICABLES = {
    "business_hours": "true",
    # Solo las aprobadas. Una foto pendiente de moderar en la ficha pública es exactamente el
    # incidente que la moderación existe para evitar.
    "review_media": "moderation_status = 'aprobada'",
}


def upgrade() -> None:
    for tabla, condicion in PUBLICABLES.items():
        op.execute(
            f"""
            CREATE POLICY {tabla}_marketplace ON {tabla}
              FOR SELECT TO agenda_publico
              USING (
                ({condicion})
                AND EXISTS (
                  SELECT 1 FROM businesses b
                   WHERE b.id = {tabla}.business_id
                     AND b.status = 'publicado'
                     AND b.deleted_at IS NULL
                )
              );
            """
        )

    # `business_hours` ya tenía el GRANT desde 0002; `review_media` no. Sin las dos cosas
    # —permiso y política— la consulta pública devuelve cero filas y parece un fallo del
    # código, que es de los ratos más largos que se pasan depurando.
    op.execute("GRANT SELECT ON review_media TO agenda_publico")

    # Una reseña publicada de un negocio publicado **es dato público**: está en el perfil, en
    # Google y en la tarjeta que alguien comparte por WhatsApp. Que el rol de la aplicación no
    # pueda ni leerla sin estar dentro del salón no protege nada y rompe lo evidente: una
    # clienta que quiere reportar una reseña ofensiva no está «dentro» de ningún negocio.
    #
    # Es el mismo movimiento que hizo la migración 0004 con `businesses`, y con el mismo
    # límite: **solo lectura y solo lo ya publicado**. Escribir sigue exigiendo tenant fijado.
    op.execute(
        """
        CREATE POLICY reviews_publicadas_lectura ON reviews
          FOR SELECT TO agenda_api
          USING (
            status = 'publicada'
            AND EXISTS (
              SELECT 1 FROM businesses b
               WHERE b.id = reviews.business_id
                 AND b.status = 'publicado'
                 AND b.deleted_at IS NULL
            )
          );
        """
    )

    # La ficha pública pide las reseñas por negocio ordenadas por fecha y **solo las
    # publicadas**. El índice de 0002 no lleva el estado dentro, así que en un salón con
    # historial largo la consulta recorre también las ocultas para descartarlas después.
    op.execute(
        """
        CREATE INDEX ix_reviews_publicadas
          ON reviews (business_id, created_at DESC)
          WHERE status = 'publicada';
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_reviews_publicadas")
    op.execute("DROP POLICY IF EXISTS reviews_publicadas_lectura ON reviews")
    op.execute("REVOKE SELECT ON review_media FROM agenda_publico")
    for tabla in PUBLICABLES:
        op.execute(f"DROP POLICY IF EXISTS {tabla}_marketplace ON {tabla}")
