"""Andamiaje de las pruebas de notificaciones.

Dos decisiones de las que depende que estas pruebas signifiquen algo:

* **La idempotencia se prueba contra PostgreSQL de verdad.** La garantiza un índice único, no
  una comprobación de Python, así que probarla con una lista en memoria demostraría que la
  lista funciona. Si no hay base, estas pruebas **fallan**; no se saltan. Un corredor que se
  salta en silencio lo que necesita base sale en verde sin haber probado nada, que es la peor
  señal posible.
* **Nunca se manda nada de verdad.** El proveedor es el de desarrollo y escribe en un archivo
  temporal por prueba, así que lo enviado se puede leer y afirmar sin depender de nadie de
  fuera. No hace falta ni una credencial de Meta para ejecutar esto.

El esquema **ya existe**: estas pruebas no migran. Comprueban que las tablas están y, si no lo
están, lo dicen con todas las letras en vez de fallar con un error de SQL a medio camino.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.notificaciones.proveedores import ProveedorDeDesarrollo

URL_APP = os.environ.get(
    "DATABASE_URL_PRUEBAS",
    "postgresql+asyncpg://agenda_api:agenda@localhost:5433/agenda_pruebas",
)
#: El rol del back-office, que es el que usa el trabajador para **enumerar negocios**. No es un
#: `BYPASSRLS`: tiene sus propias políticas y son las del back-office.
URL_SISTEMA = os.environ.get(
    "DATABASE_URL_PRUEBAS_SISTEMA",
    "postgresql+asyncpg://agenda_admin:agenda@localhost:5433/agenda_pruebas",
)

AVISO_SIN_BASE = (
    "No hay PostgreSQL escuchando o la base `agenda_pruebas` no tiene el esquema aplicado.\n"
    "La idempotencia de la cola la garantiza un índice único de la base: sin base, esta prueba "
    "no prueba nada.\n"
    "Levántala con `make arriba` y aplica las migraciones antes de volver a ejecutarla."
)


@pytest_asyncio.fixture
async def motor_api():
    motor = create_async_engine(URL_APP, poolclass=None)
    try:
        async with motor.connect() as conexion:
            await conexion.execute(text("SELECT 1 FROM notifications LIMIT 1"))
    except Exception as error:  # el motivo real se enseña tal cual, sin envolverlo
        await motor.dispose()
        pytest.fail(f"{AVISO_SIN_BASE}\n\nError:\n{error}")
    yield motor
    await motor.dispose()


@pytest_asyncio.fixture
async def motor_sistema():
    motor = create_async_engine(URL_SISTEMA, poolclass=None)
    yield motor
    await motor.dispose()


@pytest.fixture
def abrir_negocio(motor_api):
    """Fábrica de sesiones **con el tenant fijado**, igual que la de producción.

    `SET LOCAL` dentro de la transacción por el mismo motivo que en la API: una conexión que
    vuelve al pool no puede arrastrar el negocio de la prueba anterior, o una fuga se
    disfrazaría de éxito.
    """
    crear = async_sessionmaker(motor_api, class_=AsyncSession, expire_on_commit=False)

    def fabricar(negocio_id: uuid.UUID):
        class _Contexto:
            async def __aenter__(self) -> AsyncSession:
                self._sesion = crear()
                await self._sesion.__aenter__()
                self._tx = self._sesion.begin()
                await self._tx.__aenter__()
                await self._sesion.execute(
                    text("SELECT set_config('app.current_business_id', :negocio, true)"),
                    {"negocio": str(negocio_id)},
                )
                return self._sesion

            async def __aexit__(self, *excepcion) -> None:
                await self._tx.__aexit__(*excepcion)
                await self._sesion.__aexit__(*excepcion)

        return _Contexto()

    return fabricar


@pytest.fixture
def abrir_sistema(motor_sistema):
    """Sesión sin tenant con el rol del back-office: solo para enumerar negocios."""
    crear = async_sessionmaker(motor_sistema, class_=AsyncSession, expire_on_commit=False)

    def fabricar():
        class _Contexto:
            async def __aenter__(self) -> AsyncSession:
                self._sesion = crear()
                await self._sesion.__aenter__()
                self._tx = self._sesion.begin()
                await self._tx.__aenter__()
                return self._sesion

            async def __aexit__(self, *excepcion) -> None:
                await self._tx.__aexit__(*excepcion)
                await self._sesion.__aexit__(*excepcion)

        return _Contexto()

    return fabricar


@pytest.fixture
def buzon(tmp_path):
    """Un buzón por prueba: lo escrito por una no puede contaminar a la siguiente."""
    return tmp_path / "buzon.jsonl"


@pytest.fixture
def proveedor(buzon) -> ProveedorDeDesarrollo:
    return ProveedorDeDesarrollo(buzon)


@pytest.fixture
def proveedores(proveedor) -> dict[str, Any]:
    return dict.fromkeys(("whatsapp", "email", "push", "sms"), proveedor)


@pytest.fixture
def ctx(abrir_negocio, abrir_sistema, proveedores) -> dict[str, Any]:
    """El contexto del trabajador, con las fábricas y los proveedores inyectados.

    Es el mismo hueco que `on_startup` rellena en producción, y es lo que permite ejecutar los
    trabajos **llamando a la función directamente**, sin Redis: lo que se quiere probar es el
    efecto, no el transporte (ADR-0008).
    """
    return {
        "sesion_de_negocio": abrir_negocio,
        "sesion_de_sistema": abrir_sistema,
        "proveedores": proveedores,
    }
