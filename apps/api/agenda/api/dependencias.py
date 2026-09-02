"""Lo que toda petición necesita: sesión de base de datos, quién eres y en qué negocio estás.

La regla que gobierna este archivo es la de ADR-0012: **un endpoint pertenece a una audiencia
y solo a una**. La audiencia decide con qué sesión se abre la base y, por tanto, qué se puede
ver. No hay una función que sirva para todo, y es a propósito: el día que alguien reutilice
una dependencia de negocio en una ruta pública, el tipo no encaja y se nota antes de que salga.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

import jwt
from fastapi import Depends, Header
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.ajustes import obtener_ajustes
from agenda.bd import crear_sesion, crear_sesion_publica
from agenda.errores import NoAutorizado

ajustes = obtener_ajustes()

ALGORITMO = "HS256"


async def sesion_publica() -> AsyncIterator[AsyncSession]:
    """Para las rutas públicas: **otro rol de base de datos**, no otro parámetro.

    El marketplace cruza todos los negocios, así que no puede llevar tenant fijado; y sin
    tenant, las políticas del rol de la API no devuelven ni una fila. Por eso lo público se
    sirve con `agenda_publico`, que tiene sus propias políticas: **solo lectura y solo sobre lo
    publicable**. Las reservas y las fichas de cliente le están cerradas en la base, no en el
    código, así que un endpoint público mal escrito no puede llegar a ellas ni queriendo.
    """
    async with crear_sesion_publica() as sesion, sesion.begin():
        yield sesion


class Identidad:
    """Quién hace la petición, resuelto del token de acceso."""

    def __init__(self, usuario_id: uuid.UUID, negocio_id: uuid.UUID | None, rol: str | None):
        self.usuario_id = usuario_id
        self.negocio_id = negocio_id
        self.rol = rol

    @property
    def es_dueno(self) -> bool:
        return self.rol == "dueno"


def _leer_token(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise NoAutorizado("Hace falta iniciar sesión para hacer eso.")
    bruto = authorization.split(" ", 1)[1]
    try:
        return jwt.decode(bruto, ajustes.secret_key, algorithms=[ALGORITMO])
    except jwt.ExpiredSignatureError as error:
        raise NoAutorizado("La sesión caducó. Vuelve a entrar.") from error
    except jwt.PyJWTError as error:
        raise NoAutorizado("La sesión no es válida.") from error


async def identidad_actual(
    authorization: Annotated[str | None, Header()] = None,
) -> Identidad:
    """La persona autenticada, sin negocio activo necesariamente."""
    datos = _leer_token(authorization)
    negocio = datos.get("negocio")
    return Identidad(
        usuario_id=uuid.UUID(datos["sub"]),
        negocio_id=uuid.UUID(negocio) if negocio else None,
        rol=datos.get("rol"),
    )


async def sesion_de_cliente(
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> AsyncIterator[tuple[AsyncSession, Identidad]]:
    """Para `/mi/…`: la persona ve **lo suyo**, no lo de un negocio."""
    async with crear_sesion() as sesion, sesion.begin():
        yield sesion, identidad


async def sesion_de_negocio(
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> AsyncIterator[tuple[AsyncSession, Identidad]]:
    """Para `/negocio/…`: fija el tenant y **todo lo demás depende de eso**.

    El negocio sale del token, no de un parámetro de la petición. Si viniera en la URL, bastaría
    con cambiar un identificador para pedir la agenda de otro salón, y la única barrera sería
    que a nadie se le olvidara comprobarlo en cada endpoint.

    `SET LOCAL` y no `SET`: muere con la transacción, así que la conexión vuelve al pool limpia
    y la siguiente petición no hereda este negocio.
    """
    if identidad.negocio_id is None:
        raise NoAutorizado("Cambia a modo negocio para hacer eso.")

    async with crear_sesion() as sesion, sesion.begin():
        await sesion.execute(
            text("SELECT set_config('app.current_business_id', :negocio, true)"),
            {"negocio": str(identidad.negocio_id)},
        )
        yield sesion, identidad


def exigir_dueno(identidad: Identidad) -> None:
    """Finanzas, configuración y equipo son del dueño; la agenda, de todos (STF-3)."""
    if not identidad.es_dueno:
        raise NoAutorizado("Solo quien administra el negocio puede hacer eso.")


SesionPublica = Annotated[AsyncSession, Depends(sesion_publica)]
SesionCliente = Annotated[tuple[AsyncSession, Identidad], Depends(sesion_de_cliente)]
SesionNegocio = Annotated[tuple[AsyncSession, Identidad], Depends(sesion_de_negocio)]
