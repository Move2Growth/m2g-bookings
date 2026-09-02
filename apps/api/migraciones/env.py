"""Configuración de Alembic.

Dos cosas que no son las de la plantilla por defecto y conviene no «arreglar»:

* La URL se lee de **`DATABASE_URL_MIGRACIONES`**, que apunta al rol **dueño** de las tablas.
  Migrar con el usuario de la aplicación no funcionaría: no puede crear extensiones ni
  políticas de seguridad por fila. Y usar el rol dueño en la aplicación sería peor todavía,
  porque el dueño de una tabla se salta sus propias políticas (ADR-0002).
* Se migra con un motor **síncrono** (`psycopg`), aunque la aplicación sea asíncrona. Las
  migraciones no ganan nada siendo asíncronas y sí pierden legibilidad.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from agenda.modelos.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

metadatos = Base.metadata

URL = os.environ.get(
    "DATABASE_URL_MIGRACIONES",
    "postgresql+psycopg://agenda_owner:agenda@localhost:5433/agenda",
)


def migrar_sin_conexion() -> None:
    context.configure(url=URL, target_metadata=metadatos, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def migrar_con_conexion() -> None:
    motor = create_engine(URL, poolclass=pool.NullPool)
    with motor.connect() as conexion:
        context.configure(
            connection=conexion,
            target_metadata=metadatos,
            # Sin esto, un cambio de tipo pasa desapercibido al autogenerar y la migración
            # sale vacía: el error aparece semanas después, con datos dentro.
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    migrar_sin_conexion()
else:
    migrar_con_conexion()
