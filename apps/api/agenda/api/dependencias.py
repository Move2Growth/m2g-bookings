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
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.ajustes import obtener_ajustes
from agenda.bd import crear_sesion, crear_sesion_admin, crear_sesion_publica
from agenda.errores import NoAutorizado

ajustes = obtener_ajustes()

ALGORITMO = "HS256"

#: Marca de superficie que llevan **solo** los tokens del back-office. Un token de cliente no
#: la tiene, y uno de consola no vale para `/negocio` ni para `/mi`: son dos mundos y el
#: separador es un campo del token, no la buena costumbre de mirar la ruta (ADR-0006).
SUPERFICIE_CONSOLA = "consola"


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


async def sesion_de_plataforma(
    authorization: Annotated[str | None, Header()] = None,
) -> AsyncIterator[AsyncSession]:
    """Para lo que no pertenece a ningún salón: entrar, refrescar y **«mis reservas»**.

    Usa el rol de la aplicación sin negocio fijado, porque lo que toca son tablas de la
    plataforma. No exige autenticación —pedir un código es justo lo que hace quien todavía no
    la tiene—, pero **si el token viene, declara quién pregunta** en `app.current_user_id`.

    Esa declaración es lo que permite que una persona vea sus citas en todos los salones donde
    ha estado sin aflojar el aislamiento: la política que la usa es de **solo lectura y solo de
    lo suyo**. Escribir en la agenda de un salón sigue exigiendo el negocio fijado.
    """
    async with crear_sesion() as sesion, sesion.begin():
        if authorization:
            try:
                datos = _leer_token(authorization)
            except NoAutorizado:
                datos = None
            if datos:
                await sesion.execute(
                    text("SELECT set_config('app.current_user_id', :usuario, true)"),
                    {"usuario": datos["sub"]},
                )
        yield sesion


class Identidad:
    """Quién hace la petición, resuelto del token de acceso."""

    def __init__(self, usuario_id: uuid.UUID, negocio_id: uuid.UUID | None, rol: str | None):
        self.usuario_id = usuario_id
        self.negocio_id = negocio_id
        self.rol = rol
        #: El perfil de profesional de quien pide, si no es dueño. Lo rellena
        #: `sesion_de_negocio` **después** de fijar el tenant, y es lo que se declara en
        #: `app.current_staff_id` para que la base acote la agenda (STF-3).
        self.staff_id: uuid.UUID | None = None

    @property
    def es_dueno(self) -> bool:
        return self.rol == "dueno"

    @property
    def es_profesional(self) -> bool:
        """Todo lo que no es dueño se trata como profesional: ve su agenda y nada más.

        `recepcion` está en el enumerado de la base desde la primera migración pero no se
        ofrece en la interfaz (v2). Que caiga aquí es el fallo seguro: menos permisos de los
        que tendrá, nunca más.
        """
        return self.rol is not None and self.rol != "dueno"


def _leer_token(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise NoAutorizado("Hace falta iniciar sesión para hacer eso.")
    bruto = authorization.split(" ", 1)[1]
    try:
        datos = jwt.decode(bruto, ajustes.secret_key, algorithms=[ALGORITMO])
    except jwt.ExpiredSignatureError as error:
        raise NoAutorizado("La sesión caducó. Vuelve a entrar.") from error
    except jwt.PyJWTError as error:
        raise NoAutorizado("La sesión no es válida.") from error

    # Un token del back-office **no entra** por la puerta del cliente. Están firmados con la
    # misma clave porque es el mismo proceso, así que sin esta comprobación una sesión de
    # consola valdría también para `/mi` y `/negocio`.
    if datos.get("sup") == SUPERFICIE_CONSOLA:
        raise NoAutorizado("Esa sesión es de la consola interna y no sirve aquí.")
    return datos


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

        # Y aquí, la segunda declaración: **quién de dentro del salón pregunta** (STF-3).
        #
        # Se declara solo cuando NO es el dueño, y a partir de ese momento las políticas
        # restrictivas de la migración 0006 acotan la agenda a ese profesional y le cierran la
        # configuración. La diferencia con un `if` en el endpoint es toda: un endpoint nuevo
        # que se olvide de comprobar el rol **sigue** sin poder ver la agenda de otro, porque
        # quien filtra es PostgreSQL y no el autor del endpoint.
        #
        # El orden importa: primero el negocio —sin él no se puede leer `staff_profiles`— y
        # después el profesional.
        if identidad.es_profesional:
            identidad.staff_id = await _perfil_de_profesional(sesion, identidad)
            await sesion.execute(
                text("SELECT set_config('app.current_staff_id', :staff, true)"),
                {"staff": str(identidad.staff_id)},
            )

        yield sesion, identidad


async def _perfil_de_profesional(sesion: AsyncSession, identidad: Identidad) -> uuid.UUID:
    """El perfil de profesional de quien pide, que **no** es su identificador de usuario.

    Son dos cosas distintas: `users.id` es la persona en la plataforma y `staff_profiles.id`
    es su ficha dentro de este salón. Confundirlas dejaría a un profesional viendo una agenda
    vacía o —peor— filtrando por un identificador que casualmente exista.
    """
    from agenda.modelos.equipo import StaffProfile  # local: evita un ciclo con los modelos

    perfil = (
        await sesion.execute(
            select(StaffProfile.id).where(
                StaffProfile.business_id == identidad.negocio_id,
                StaffProfile.user_id == identidad.usuario_id,
                StaffProfile.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    if perfil is None:
        raise NoAutorizado("Tu cuenta no tiene ficha de profesional en este negocio.")
    return perfil


class IdentidadAdmin:
    """Quién pregunta desde la consola interna. **No es un `Identidad` con una casilla más.**

    Son dos clases distintas a propósito: si compartieran tipo, una dependencia de negocio
    aceptaría sin protestar una identidad de consola, y ese error no falla — devuelve de más.
    """

    def __init__(self, admin_id: uuid.UUID, rol: str, email: str):
        self.admin_id = admin_id
        self.rol = rol
        self.email = email

    @property
    def es_superadmin(self) -> bool:
        return self.rol == "superadmin"


async def identidad_de_consola(
    authorization: Annotated[str | None, Header()] = None,
) -> IdentidadAdmin:
    """Lee el token del back-office. Exige la marca de superficie, no solo una firma válida."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise NoAutorizado("Hace falta iniciar sesión en la consola.")
    try:
        datos = jwt.decode(
            authorization.split(" ", 1)[1], ajustes.secret_key, algorithms=[ALGORITMO]
        )
    except jwt.ExpiredSignatureError as error:
        raise NoAutorizado("La sesión de consola caducó. Vuelve a entrar.") from error
    except jwt.PyJWTError as error:
        raise NoAutorizado("La sesión no es válida.") from error

    if datos.get("sup") != SUPERFICIE_CONSOLA:
        raise NoAutorizado("Esa sesión no es de la consola interna.")

    return IdentidadAdmin(
        admin_id=uuid.UUID(datos["sub"]), rol=datos.get("rol", ""), email=datos.get("email", "")
    )


async def sesion_de_consola(
    identidad: Annotated[IdentidadAdmin, Depends(identidad_de_consola)],
) -> AsyncIterator[tuple[AsyncSession, IdentidadAdmin]]:
    """Para `/consola/…`: **otro rol de base de datos**, `agenda_admin`.

    Ese rol ve todos los negocios porque su trabajo es ese, pero tampoco tiene `BYPASSRLS`:
    accede por políticas escritas en la migración, igual que los demás. La diferencia con la
    API del salón no es un permiso en el código, es la conexión.
    """
    async with crear_sesion_admin() as sesion, sesion.begin():
        yield sesion, identidad


def exigir_dueno(identidad: Identidad) -> None:
    """Finanzas, configuración y equipo son del dueño; la agenda, de todos (STF-3)."""
    if not identidad.es_dueno:
        raise NoAutorizado("Solo quien administra el negocio puede hacer eso.")


SesionConsola = Annotated[tuple[AsyncSession, IdentidadAdmin], Depends(sesion_de_consola)]
SesionPublica = Annotated[AsyncSession, Depends(sesion_publica)]
SesionPlataforma = Annotated[AsyncSession, Depends(sesion_de_plataforma)]
SesionCliente = Annotated[tuple[AsyncSession, Identidad], Depends(sesion_de_cliente)]
SesionNegocio = Annotated[tuple[AsyncSession, Identidad], Depends(sesion_de_negocio)]
