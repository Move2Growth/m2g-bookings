"""Crea la primera cuenta de la consola interna. `python -m agenda.consola_alta`.

Existe porque la cuenta del back-office **no puede venir en el seed con una contraseña
escrita**: eso sería un secreto en el repositorio, y da igual que el entorno sea local — el
día que alguien copie el seed a staging, la contraseña de la consola de M2G está en git.

Así que la contraseña sale de dos sitios, en este orden:

1. Las variables `CONSOLA_EMAIL_INICIAL` y `CONSOLA_PASSWORD_INICIAL`, documentadas en
   `.env.example` y en `docs/operacion/SECRETOS-Y-VARIABLES.md`, **sin valor**.
2. Si no están, se genera una al azar y **se imprime una sola vez** por pantalla, junto con el
   secreto del segundo factor en formato base32 y su URI `otpauth://` para el QR.

Lo que se imprime no se guarda en ningún sitio y no se puede volver a ver: el secreto del
segundo factor se almacena, pero enseñarlo otra vez sería regalar el 2FA a quien tenga acceso
al servidor. Si se pierde, se rota la cuenta.
"""

from __future__ import annotations

import asyncio
import os
import secrets
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.ajustes import obtener_ajustes
from agenda.dominio import totp
from agenda.modelos.identidad import AdminUser
from agenda.servicios.consola import hashear_password

ajustes = obtener_ajustes()

#: Se conecta con el rol dueño porque está creando la fila fundacional: todavía no hay ninguna
#: cuenta de consola con la que autorizar nada. Es el mismo caso que el seed.
URL = ajustes.database_url_migraciones.replace("postgresql+psycopg", "postgresql+asyncpg")

EMISOR_2FA = "Bukeo Consola"


async def crear(email: str, password: str, nombre: str, rol: str) -> tuple[str, str]:
    """Crea la cuenta y devuelve la contraseña y la URI del QR, para enseñarlas una vez."""
    motor = create_async_engine(URL, poolclass=None)
    crear_sesion = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    try:
        async with crear_sesion() as sesion, sesion.begin():
            ya = (
                await sesion.execute(select(AdminUser).where(AdminUser.email == email))
            ).scalar_one_or_none()
            if ya is not None:
                raise SystemExit(f"Ya existe una cuenta de consola con el correo {email}.")

            secreto = totp.secreto_nuevo()
            sesion.add(
                AdminUser(
                    email=email,
                    full_name=nombre,
                    password_hash=hashear_password(password),
                    # El secreto se guarda tal cual en `bytea`. El modelo lo anota como
                    # «cifrado en reposo»: **eso todavía no está**, y cifrarlo aquí sin un
                    # gestor de claves de verdad sería teatro. Queda anotado como deuda en el
                    # tablero en vez de fingir que está resuelto.
                    totp_secret=secreto,
                    totp_enabled=True,
                    role=rol,
                    status="activo",
                )
            )
        return password, totp.uri_de_provisionamiento(secreto, cuenta=email, emisor=EMISOR_2FA)
    finally:
        await motor.dispose()


def principal() -> None:
    email = (os.environ.get("CONSOLA_EMAIL_INICIAL") or ajustes.consola_email_inicial).strip()
    if not email:
        print(
            "Falta el correo. Pon CONSOLA_EMAIL_INICIAL en el .env o pásalo como argumento:\n"
            "  python -m agenda.consola_alta correo@m2g.dev 'Nombre Apellido'",
            file=sys.stderr,
        )
        if len(sys.argv) < 2:
            raise SystemExit(1)

    if len(sys.argv) > 1:
        email = sys.argv[1]
    nombre = sys.argv[2] if len(sys.argv) > 2 else "Equipo M2G"
    rol = sys.argv[3] if len(sys.argv) > 3 else "superadmin"

    password = (
        os.environ.get("CONSOLA_PASSWORD_INICIAL")
        or ajustes.consola_password_inicial
        or secrets.token_urlsafe(18)
    )

    clara, uri = asyncio.run(crear(email.lower(), password, nombre, rol))

    print("Cuenta de consola creada.")
    print(f"  Correo:     {email.lower()}")
    print(f"  Contraseña: {clara}")
    print(f"  2FA (QR):   {uri}")
    print()
    print("Apunta las dos cosas AHORA: no se vuelven a enseñar.")
    print("Mete la URI del 2FA en el autenticador antes de cerrar esta ventana.")


if __name__ == "__main__":
    principal()
