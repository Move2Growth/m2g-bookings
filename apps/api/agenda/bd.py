"""Acceso a la base de datos y **fijación del tenant**.

Aquí está la pieza de la que depende la garantía nº 1 del proyecto: ninguna consulta devuelve
datos de otro negocio. El mecanismo es el de ADR-0002 — políticas de seguridad por fila en
PostgreSQL comparando contra el ajuste de sesión `app.current_business_id`.

Dos detalles que parecen menores y son la diferencia entre que funcione y que no:

* Se usa **`SET LOCAL`**, no `SET`. `SET LOCAL` muere al terminar la transacción, así que una
  conexión que vuelve al pool no arrastra el negocio del usuario anterior. Con `SET` a secas,
  la siguiente petición que reutilizara esa conexión heredaría el tenant ajeno.
* El usuario con el que se conecta la aplicación **no es dueño de las tablas y no tiene
  `BYPASSRLS`**. El dueño de una tabla se salta sus propias políticas, así que conectarse como
  dueño desactivaría el aislamiento sin que nada fallara ni avisara.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.ajustes import obtener_ajustes

_ajustes = obtener_ajustes()

motor = create_async_engine(
    _ajustes.database_url,
    pool_pre_ping=True,
    # El pool tiene que ser transaccional para que `SET LOCAL` signifique lo que creemos.
    # Si algún día entra PgBouncer delante, va en modo `transaction` por la misma razón.
    pool_size=10,
    max_overflow=10,
)

crear_sesion = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)

# El marketplace **no puede usar el rol de la API**. Sus consultas cruzan todos los negocios y
# por tanto no llevan tenant fijado, y sin tenant las políticas de `agenda_api` no devuelven ni
# una fila. El rol `agenda_publico` tiene sus propias políticas: solo lectura y solo sobre lo
# publicable —negocios publicados, sus servicios activos, su equipo visible y sus reseñas—,
# nunca reservas ni fichas de cliente.
#
# Son dos conexiones distintas a propósito. Con una sola y un `SET ROLE` por petición, un
# olvido dejaría una consulta pública corriendo con permisos de negocio, y ese olvido no falla:
# devuelve de más.
motor_publico = create_async_engine(
    _ajustes.database_url_publico,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
)

crear_sesion_publica = async_sessionmaker(
    motor_publico, class_=AsyncSession, expire_on_commit=False
)


@asynccontextmanager
async def sesion_de_negocio(negocio_id: str) -> AsyncIterator[AsyncSession]:
    """Abre una transacción con el tenant fijado. **Toda** lectura o escritura de datos de un
    negocio pasa por aquí, incluidas las de los trabajos en segundo plano.

    Los trabajos son justamente donde más fácil se cuela una consulta sin tenant: no tienen
    sesión de usuario de la que heredarlo, así que hay que fijarlo a mano (ADR-0008).
    """
    async with crear_sesion() as sesion, sesion.begin():
        await sesion.execute(
            text("SELECT set_config('app.current_business_id', :negocio, true)"),
            {"negocio": str(negocio_id)},
        )
        yield sesion


@asynccontextmanager
async def sesion_sin_tenant() -> AsyncIterator[AsyncSession]:
    """Para lo que legítimamente cruza negocios: el marketplace y los catálogos globales.

    No es una puerta trasera: sin `app.current_business_id` fijado, las políticas de seguridad
    por fila **no dejan ver nada** de las tablas aisladas. Lo único accesible desde aquí son
    las tablas globales y las vistas públicas del marketplace, que solo exponen columnas
    publicables — nunca teléfonos ni datos de clientes.
    """
    async with crear_sesion() as sesion, sesion.begin():
        yield sesion
