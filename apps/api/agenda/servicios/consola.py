"""Entrar en la consola interna de M2G (ADM-5, ADR-0006).

**Es otro sistema de acceso, no el de clientes con una casilla marcada.** Otras tablas
(`admin_users`, `admin_sessions`), otro rol de base de datos (`agenda_admin`), otra caducidad
y **segundo factor obligatorio**. Si un superadministrador fuera un usuario con un permiso, un
fallo de escalada en la aplicación de la clienta sería una escalada al back-office de toda la
plataforma; siendo dos sistemas, no hay ninguna escalera que suba de uno al otro.

Tres decisiones que se ven en el código:

* **La contraseña se guarda con argon2id**, que es lo que hay que usar hoy para contraseñas y
  no un SHA de nada.
* **El refresco es opaco, se guarda con hash y rota**, igual que el de la aplicación: lo que
  viaja no vale nada guardado, y presentar uno ya rotado cierra la familia entera.
* **Correo, contraseña y segundo factor fallan con el mismo error.** Distinguirlos le diría a
  quien prueba combinaciones por dónde va bien.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.ajustes import obtener_ajustes
from agenda.dominio import totp
from agenda.errores import CredencialesInvalidas, NoAutorizado
from agenda.modelos.identidad import AdminSession, AdminUser

ajustes = obtener_ajustes()

ALGORITMO = "HS256"
SUPERFICIE = "consola"

_hasher = PasswordHasher()


@dataclass(frozen=True)
class CredencialesDeConsola:
    acceso: str
    refresco: str
    expira_en_segundos: int
    admin_id: uuid.UUID
    rol: str
    nombre: str


def hashear_password(clara: str) -> str:
    return _hasher.hash(clara)


def _hash(valor: str) -> bytes:
    return hashlib.sha256(valor.encode()).digest()


async def entrar(
    sesion: AsyncSession,
    *,
    email: str,
    password: str,
    codigo_2fa: str,
    ip_hash: bytes | None = None,
    agente: str | None = None,
    ahora: datetime | None = None,
) -> CredencialesDeConsola:
    """Correo, contraseña y segundo factor. Los tres, siempre.

    El 2FA no es opcional y la columna `totp_enabled` existe **para poder auditar que está
    activo**, no para poder apagarlo: quien entra aquí ve los datos de todos los negocios de la
    plataforma.
    """
    ahora = ahora or datetime.now(UTC)

    cuenta = (
        await sesion.execute(
            select(AdminUser).where(
                AdminUser.email == email.strip().lower(), AdminUser.status == "activo"
            )
        )
    ).scalar_one_or_none()

    if cuenta is None:
        # Se verifica una contraseña falsa igualmente para que responder «no existe» tarde lo
        # mismo que responder «contraseña mala». Sin esto, el tiempo de respuesta dice qué
        # correos son de verdad.
        _verificar_en_vano(password)
        raise CredencialesInvalidas()

    try:
        _hasher.verify(cuenta.password_hash, password)
    except VerifyMismatchError as error:
        raise CredencialesInvalidas() from error

    if not totp.verificar(bytes(cuenta.totp_secret), codigo_2fa, momento=ahora.timestamp()):
        raise CredencialesInvalidas()

    cuenta.last_login_at = ahora
    return await _emitir(sesion, cuenta, ahora=ahora, ip_hash=ip_hash, agente=agente)


async def refrescar(
    sesion: AsyncSession, *, refresco: str, ahora: datetime | None = None
) -> CredencialesDeConsola:
    """Rota el refresco. Reutilizar uno ya rotado **cierra la familia entera**."""
    ahora = ahora or datetime.now(UTC)

    fila = (
        await sesion.execute(
            select(AdminSession).where(AdminSession.refresh_token_hash == _hash(refresco))
        )
    ).scalar_one_or_none()
    if fila is None:
        raise NoAutorizado("Esa sesión no es válida.")

    if fila.revoked_at is not None or fila.rotated_at is not None:
        # Solo pasa cuando alguien copió el token: el legítimo ya rotó y sigue su camino. Se
        # cierra la familia entera, que es la única forma de cortar la cadena.
        await _revocar_familia(sesion, fila.family_id, ahora, motivo="rotacion_reusada")
        raise NoAutorizado("La sesión se cerró por seguridad. Vuelve a entrar.")

    if fila.expires_at <= ahora:
        raise NoAutorizado("La sesión caducó. Vuelve a entrar.")

    cuenta = await sesion.get(AdminUser, fila.admin_user_id)
    if cuenta is None or cuenta.status != "activo":
        raise NoAutorizado("Esa cuenta ya no está activa.")

    fila.rotated_at = ahora
    return await _emitir(
        sesion,
        cuenta,
        ahora=ahora,
        familia=fila.family_id,
        ip_hash=fila.ip_hash,
        agente=fila.user_agent,
    )


async def salir(sesion: AsyncSession, *, refresco: str, ahora: datetime | None = None) -> None:
    """Cerrar sesión **surte efecto ya**, no cuando caduque el acceso."""
    ahora = ahora or datetime.now(UTC)
    fila = (
        await sesion.execute(
            select(AdminSession).where(AdminSession.refresh_token_hash == _hash(refresco))
        )
    ).scalar_one_or_none()
    if fila is None:
        return
    await _revocar_familia(sesion, fila.family_id, ahora, motivo="cierre_sesion")


async def _emitir(
    sesion: AsyncSession,
    cuenta: AdminUser,
    *,
    ahora: datetime,
    familia: uuid.UUID | None = None,
    ip_hash: bytes | None = None,
    agente: str | None = None,
) -> CredencialesDeConsola:
    vida_acceso = timedelta(minutes=ajustes.acceso_admin_minutos)
    vida_refresco = timedelta(hours=ajustes.refresco_admin_horas)

    refresco = secrets.token_urlsafe(48)
    sesion.add(
        AdminSession(
            admin_user_id=cuenta.id,
            family_id=familia or uuid.uuid4(),
            refresh_token_hash=_hash(refresco),
            ip_hash=ip_hash,
            user_agent=agente,
            issued_at=ahora,
            expires_at=ahora + vida_refresco,
        )
    )
    await sesion.flush()

    acceso = jwt.encode(
        {
            "sub": str(cuenta.id),
            "sup": SUPERFICIE,
            "rol": cuenta.role,
            "email": cuenta.email,
            "iat": int(ahora.timestamp()),
            "exp": int((ahora + vida_acceso).timestamp()),
        },
        ajustes.secret_key,
        algorithm=ALGORITMO,
    )
    return CredencialesDeConsola(
        acceso=acceso,
        refresco=refresco,
        expira_en_segundos=int(vida_acceso.total_seconds()),
        admin_id=cuenta.id,
        rol=cuenta.role,
        nombre=cuenta.full_name,
    )


async def _revocar_familia(
    sesion: AsyncSession, familia: uuid.UUID, ahora: datetime, *, motivo: str
) -> None:
    filas = (
        (
            await sesion.execute(
                select(AdminSession).where(
                    AdminSession.family_id == familia, AdminSession.revoked_at.is_(None)
                )
            )
        )
        .scalars()
        .all()
    )
    for fila in filas:
        fila.revoked_at = ahora
        fila.revoked_reason = motivo
    await sesion.flush()


def _verificar_en_vano(password: str) -> None:
    """Quema el mismo tiempo que una verificación real, para no filtrar qué correos existen."""
    with suppress(VerifyMismatchError):
        _hasher.verify(_hasher.hash("no-existe"), password)
