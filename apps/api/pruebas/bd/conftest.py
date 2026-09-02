"""Andamiaje de las pruebas que necesitan una base de datos de verdad.

**Si no hay PostgreSQL, estas pruebas fallan; no se saltan.** Es deliberado y viene de un
tropiezo conocido en la casa: un corredor de pruebas que se salta en silencio todo lo que
necesita base de datos sale en verde sin haber probado nada, y esa es la peor señal posible —
un «todo bien» que no significa nada. Aquí, si falta la base, el mensaje lo dice y el proceso
falla.

Lo que estas pruebas ejercen no se puede simular: la restricción de exclusión que impide la
doble reserva, las políticas de seguridad por fila que aíslan los negocios y PostGIS. Nada de
eso existe en SQLite, así que no hay atajo posible.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

URL_APP = os.environ.get(
    "DATABASE_URL_PRUEBAS",
    "postgresql+asyncpg://agenda_api:agenda@localhost:5433/agenda_pruebas",
)
URL_DUENO = os.environ.get(
    "DATABASE_URL_PRUEBAS_DUENO",
    "postgresql+psycopg://agenda_owner:agenda@localhost:5433/agenda_pruebas",
)

AVISO_SIN_BASE = (
    "No hay PostgreSQL escuchando. Estas pruebas comprueban la restricción de exclusión, el "
    "aislamiento por fila y PostGIS, que solo existen en una base real.\n"
    "Levántala con `make arriba` (o `docker compose -f infra/local/docker-compose.yml up -d db`) "
    "y vuelve a ejecutarlas."
)


@pytest.fixture(scope="session", autouse=True)
def migraciones_aplicadas() -> Iterator[None]:
    """Migra desde cero contra la base real antes de la primera prueba.

    Que las migraciones corran de arriba abajo sobre una base limpia es un requisito del
    encargo, no un detalle: si solo se probaran de forma incremental, el día que alguien monte
    el entorno nuevo descubriría que la primera migración nunca funcionó sola.
    """
    # Se llama a Alembic con **este mismo intérprete**, no con el `alembic` del PATH: si el
    # entorno virtual no está activado, el del sistema no tiene ni las dependencias ni los
    # modelos, y el fallo que sale no se parece en nada al problema real.
    resultado = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env={**os.environ, "DATABASE_URL_MIGRACIONES": URL_DUENO},
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        pytest.fail(f"{AVISO_SIN_BASE}\n\nSalida de alembic:\n{resultado.stderr}")
    yield


@pytest_asyncio.fixture
async def motor():
    motor = create_async_engine(URL_APP, poolclass=None)
    try:
        async with motor.connect() as conexion:
            await conexion.execute(text("SELECT 1"))
    except Exception as error:  # el motivo real se enseña tal cual, sin envolverlo
        await motor.dispose()
        pytest.fail(f"{AVISO_SIN_BASE}\n\nError de conexión:\n{error}")
    yield motor
    await motor.dispose()


@pytest_asyncio.fixture
async def sesion(motor) -> AsyncIterator[AsyncSession]:
    """Sesión **sin tenant fijado**: lo que se vea desde aquí es lo que ve un desconocido."""
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    async with crear() as sesion:
        yield sesion


@pytest_asyncio.fixture
async def sesion_negocio(motor):
    """Devuelve una fábrica de sesiones con el negocio fijado, como hace la API en cada petición.

    Se usa `SET LOCAL` dentro de la transacción por la misma razón que en producción: para que
    una conexión devuelta al pool no arrastre el negocio de la prueba anterior y una fuga se
    disfrace de éxito.
    """
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)

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
