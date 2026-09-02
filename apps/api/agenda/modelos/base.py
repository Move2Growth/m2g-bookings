"""Cimientos del modelo de datos: base declarativa, identificadores y mezclas comunes.

Aquí no hay tablas, solo lo que todas comparten. Tres decisiones viven en este archivo y
afectan a cada tabla que se escriba después:

* **Convención de nombres de restricciones e índices.** Sin ella, PostgreSQL les pone nombres
  automáticos que cambian entre entornos, y una migración que intenta borrar un índice por su
  nombre falla en producción y funciona en local.
* **Identificadores UUID v7.** Ordenables en el tiempo —los índices no se fragmentan como con
  UUID v4— y sin revelar cuántas reservas hay ni permitir enumerarlas, que es lo que pasa con
  los enteros autoincrementales en un producto con perfiles públicos (ADR-0012).
* **La marca de tenant.** `TenantMixin` no es solo una columna: es la señal de que esa tabla
  necesita política de seguridad por fila, y hay una prueba que recorre el catálogo y falla si
  alguna la lleva sin política (ADR-0002).
"""

from __future__ import annotations

import uuid
from datetime import datetime

import uuid_utils
from sqlalchemy import DateTime, ForeignKey, MetaData, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

CONVENCION_NOMBRES = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def nuevo_id() -> uuid.UUID:
    """UUID v7: lleva la hora dentro, así que ordena por creación sin columna adicional."""
    return uuid.UUID(str(uuid_utils.uuid7()))


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCION_NOMBRES)


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=nuevo_id)


class FechasMixin:
    """Cuándo se creó y cuándo se tocó por última vez.

    El valor por defecto lo pone **el servidor**, no Python: los trabajos en segundo plano y
    las migraciones también escriben, y el reloj que importa es el de la base, uno solo.
    """

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TenantMixin:
    """Marca una tabla como **propiedad de un negocio**.

    Toda tabla que herede de aquí lleva `business_id` obligatorio y **tiene que** tener su
    política de seguridad por fila en la migración. No es una convención de estilo: es la
    garantía nº 1 del proyecto, y hay una prueba que la vigila.
    """

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # `RESTRICT` a propósito: borrar un negocio con reservas dentro no puede ser un
        # descuido de una tarde. La baja de un negocio es un procedimiento con su propio
        # tratamiento de datos (Ley 81), no un `DELETE` en cascada.
        ForeignKey("businesses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
