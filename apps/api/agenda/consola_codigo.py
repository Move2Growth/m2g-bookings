"""Imprime el código de segundo factor de una cuenta de consola. Para la demo.

`python -m agenda.consola_codigo [correo]`

Existe por una razón muy concreta: quien quiere **enseñar** la consola no tiene por qué tener
una aplicación de autenticación configurada, y sin el segundo factor no se entra —porque el
segundo factor no es opcional (ADR-0006)—.

Esto **no debilita nada**: para imprimir el código hace falta acceso de lectura a la base de
datos con el rol dueño, y quien tiene eso ya tiene los datos. Lo que no hace es un endpoint:
un `GET /consola/codigo` sí sería una puerta trasera, porque bastaría con la red.

Por si acaso, se niega a funcionar fuera de `ENTORNO=local`.
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.ajustes import obtener_ajustes
from agenda.dominio import totp
from agenda.modelos.identidad import AdminUser

ajustes = obtener_ajustes()

URL = ajustes.database_url_migraciones.replace("postgresql+psycopg", "postgresql+asyncpg")

CORREO_POR_DEFECTO = "consola@bukeo.local"


async def codigo_de(email: str) -> str:
    motor = create_async_engine(URL, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    try:
        async with crear() as sesion, sesion.begin():
            cuenta = (
                await sesion.execute(select(AdminUser).where(AdminUser.email == email))
            ).scalar_one_or_none()
            if cuenta is None:
                raise SystemExit(
                    f"No hay ninguna cuenta de consola con el correo {email}.\n"
                    "Créala con `python -m agenda.consola_alta` o recarga el seed."
                )
            return totp.codigo(bytes(cuenta.totp_secret))
    finally:
        await motor.dispose()


def principal() -> None:
    if not ajustes.es_local:
        raise SystemExit("Esto solo funciona con ENTORNO=local. Usa tu autenticador.")

    email = (sys.argv[1] if len(sys.argv) > 1 else CORREO_POR_DEFECTO).lower()
    print(asyncio.run(codigo_de(email)))


if __name__ == "__main__":
    principal()
