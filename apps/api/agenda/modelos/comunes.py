"""Piezas compartidas por los modelos que no caben en `base.py`.

`base.py` no se toca (es la base declarativa del proyecto), así que lo que hace falta para
todas las tablas y no está allí vive aquí.

Una nota sobre los nombres. El proyecto habla español en comentarios, mensajes y nombres de
funciones, pero **las tablas y las columnas están en inglés** porque así las fija el DDL
literal de `docs/arquitectura/fase-3-modelo-de-datos.md`, y ese documento es el contrato con
las migraciones, con las políticas de seguridad por fila y con las consultas del marketplace.
Por eso aquí hay un `MarcasDeTiempoMixin` con `created_at`/`updated_at` en vez de reutilizar
`FechasMixin` de `base.py`, que los nombra en español: dos juegos de nombres para lo mismo
sería exactamente la clase de detalle que rompe una migración escrita a mano.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class MarcasDeTiempoMixin:
    """Cuándo se creó la fila y cuándo se tocó por última vez.

    El valor lo pone **el servidor de base de datos**, no Python: los trabajos en segundo
    plano, el seed y las propias migraciones también escriben, y el único reloj que puede
    arbitrar entre todos ellos es el de la base.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CreadoEnMixin:
    """Solo `created_at`.

    Para las tablas **append-only** —eventos de reserva, consentimientos, auditoría—: no
    llevan `updated_at` porque no se actualizan nunca, y ofrecer la columna invitaría a
    hacerlo. Un registro que se puede modificar deja de ser prueba de nada.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
