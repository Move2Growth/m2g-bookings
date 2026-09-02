"""Entrar y salir: OTP por teléfono, sesión con refresco rotatorio y cambio a modo negocio.

Tres decisiones de ADR-0006 se materializan aquí y conviene no deshacerlas sin leerlo:

* **El código nunca se guarda en claro.** Si la base se filtra, un OTP en claro es una sesión
  regalada. Se guarda su hash y se compara en tiempo constante.
* **El refresco es opaco y rotatorio.** Cada uso emite uno nuevo e invalida el anterior; volver
  a presentar uno ya rotado invalida **toda la familia**, porque eso solo pasa cuando alguien
  copió el token. Sin familias, el ladrón y la víctima se turnan indefinidamente.
* **El token de acceso no lleva permisos**, solo quién eres y en qué negocio estás. Los
  permisos se resuelven contra la membresía en cada petición, así que echar a un profesional
  surte efecto en la siguiente llamada y no cuando caduque su token.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.ajustes import obtener_ajustes
from agenda.errores import DemasiadosIntentos, NoAutorizado, OtpInvalido
from agenda.modelos.identidad import AuthIdentity, Membership, OtpCode, Session, User

ajustes = obtener_ajustes()

ALGORITMO = "HS256"
#: Cinco minutos. Suficiente para leer un WhatsApp y teclear seis dígitos; poco para que un
#: código olvidado en una bandeja sirva de algo.
VALIDEZ_OTP = timedelta(minutes=5)
#: El acceso es corto porque no se puede revocar; lo que se revoca es el refresco.
VIDA_ACCESO = timedelta(minutes=15)
VIDA_REFRESCO = timedelta(days=30)
#: Cuántos códigos se pueden pedir por teléfono en una ventana. Es seguridad y es coste: cada
#: mensaje de WhatsApp se paga, y el SMS de respaldo es el vector clásico de fraude.
MAXIMO_ENVIOS = 5
VENTANA_ENVIOS = timedelta(minutes=15)


@dataclass(frozen=True)
class Credenciales:
    """Lo que se le devuelve a quien acaba de entrar."""

    acceso: str
    refresco: str
    expira_en_segundos: int
    usuario_id: uuid.UUID
    negocio_activo: uuid.UUID | None = None


def _hash(valor: str) -> bytes:
    return hashlib.sha256(valor.encode()).digest()


def _codigo_nuevo() -> str:
    """Seis dígitos de un generador criptográfico, no de `random`."""
    return f"{secrets.randbelow(1_000_000):06d}"


async def solicitar_otp(
    sesion: AsyncSession, *, telefono: str, proposito: str = "login", canal: str = "whatsapp"
) -> str:
    """Emite un código y devuelve **el código en claro solo para el proveedor de desarrollo**.

    En producción quien lo recibe es el canal, no la respuesta HTTP: devolverlo por la API
    convertiría el OTP en un adorno. Por eso el endpoint que llama a esto **no lo enseña**
    salvo en local.
    """
    limite = datetime.now(UTC) - VENTANA_ENVIOS
    recientes = (
        (
            await sesion.execute(
                select(OtpCode).where(
                    OtpCode.destination == telefono,
                    OtpCode.created_at >= limite,
                )
            )
        )
        .scalars()
        .all()
    )

    if len(recientes) >= MAXIMO_ENVIOS:
        raise DemasiadosIntentos(
            "Pediste muchos códigos seguidos. Espera unos minutos y vuelve a intentarlo."
        )

    # Emitir uno nuevo invalida los anteriores: si no, el código viejo seguiría sirviendo y la
    # ventana de ataque sería la suma de todas las ventanas.
    ahora = datetime.now(UTC)
    for anterior in recientes:
        if anterior.consumed_at is None and anterior.invalidated_at is None:
            anterior.invalidated_at = ahora

    codigo = _codigo_nuevo()
    sesion.add(
        OtpCode(
            destination=telefono,
            channel=canal,
            purpose=proposito,
            code_hash=_hash(codigo),
            expires_at=ahora + VALIDEZ_OTP,
        )
    )
    await sesion.flush()
    return codigo


async def verificar_otp(
    sesion: AsyncSession, *, telefono: str, codigo: str, superficie: str = "web"
) -> Credenciales:
    """Canjea el código por una sesión. Crea la cuenta si es la primera vez (ONB-1).

    El mismo mensaje para «código incorrecto» y «código caducado»: distinguirlos le diría a
    quien prueba a ciegas cuándo va por buen camino.
    """
    ahora = datetime.now(UTC)
    vigente = (
        (
            await sesion.execute(
                select(OtpCode)
                .where(
                    OtpCode.destination == telefono,
                    OtpCode.consumed_at.is_(None),
                    OtpCode.invalidated_at.is_(None),
                    OtpCode.expires_at > ahora,
                )
                .order_by(OtpCode.created_at.desc())
            )
        )
        .scalars()
        .first()
    )

    if vigente is None:
        raise OtpInvalido()

    if vigente.attempts >= vigente.max_attempts:
        vigente.invalidated_at = ahora
        raise DemasiadosIntentos("Ese código se bloqueó por demasiados intentos. Pide uno nuevo.")

    # Comparación en tiempo constante: comparar hashes con `==` filtra información por el
    # tiempo que tarda en fallar.
    if not hmac.compare_digest(vigente.code_hash, _hash(codigo)):
        vigente.attempts += 1
        await sesion.flush()
        raise OtpInvalido()

    vigente.consumed_at = ahora

    usuario = (
        await sesion.execute(select(User).where(User.phone_e164 == telefono))
    ).scalar_one_or_none()

    if usuario is None:
        usuario = User(phone_e164=telefono, full_name="", phone_verified_at=ahora)
        sesion.add(usuario)
        await sesion.flush()
        sesion.add(AuthIdentity(user_id=usuario.id, provider="telefono", subject=telefono))
    elif usuario.phone_verified_at is None:
        usuario.phone_verified_at = ahora

    return await _abrir_sesion(sesion, usuario=usuario, superficie=superficie)


async def _abrir_sesion(
    sesion: AsyncSession,
    *,
    usuario: User,
    superficie: str,
    negocio_id: uuid.UUID | None = None,
    familia: uuid.UUID | None = None,
) -> Credenciales:
    ahora = datetime.now(UTC)
    refresco = secrets.token_urlsafe(48)

    fila = Session(
        user_id=usuario.id,
        family_id=familia or uuid.uuid4(),
        refresh_token_hash=_hash(refresco),
        active_business_id=negocio_id,
        surface=superficie,
        issued_at=ahora,
        expires_at=ahora + VIDA_REFRESCO,
    )
    sesion.add(fila)
    await sesion.flush()

    rol = None
    if negocio_id is not None:
        rol = await _rol_en(sesion, usuario.id, negocio_id)

    return Credenciales(
        acceso=_firmar_acceso(usuario.id, negocio_id, rol, ahora),
        refresco=refresco,
        expira_en_segundos=int(VIDA_ACCESO.total_seconds()),
        usuario_id=usuario.id,
        negocio_activo=negocio_id,
    )


def _firmar_acceso(
    usuario_id: uuid.UUID, negocio_id: uuid.UUID | None, rol: str | None, ahora: datetime
) -> str:
    carga = {
        "sub": str(usuario_id),
        "iat": int(ahora.timestamp()),
        "exp": int((ahora + VIDA_ACCESO).timestamp()),
    }
    if negocio_id is not None:
        carga["negocio"] = str(negocio_id)
        carga["rol"] = rol or ""
    return jwt.encode(carga, ajustes.secret_key, algorithm=ALGORITMO)


async def _rol_en(sesion: AsyncSession, usuario_id: uuid.UUID, negocio_id: uuid.UUID) -> str:
    """Qué rol tiene esta persona en ese negocio, si es que tiene alguno.

    Hay que **fijar el tenant antes de poder leer la membresía**, y eso parece el huevo y la
    gallina: para entrar al negocio hace falta la membresía, y para ver la membresía hace falta
    estar en el negocio. No lo es. Fijar el tenant no autoriza nada por sí solo —solo acota lo
    que la consulta puede ver a ese negocio—; quien autoriza es la fila que aparece o no
    aparece a continuación, filtrada además por el usuario que pregunta. Sin membresía, la
    consulta vuelve vacía y esto lanza.
    """
    await sesion.execute(
        text("SELECT set_config('app.current_business_id', :negocio, true)"),
        {"negocio": str(negocio_id)},
    )
    membresia = (
        await sesion.execute(
            select(Membership).where(
                Membership.user_id == usuario_id,
                Membership.business_id == negocio_id,
                Membership.status == "activa",
            )
        )
    ).scalar_one_or_none()

    if membresia is None:
        raise NoAutorizado("No tienes acceso a ese negocio.")
    return membresia.role


async def cambiar_a_negocio(
    sesion: AsyncSession, *, usuario_id: uuid.UUID, negocio_id: uuid.UUID, superficie: str = "web"
) -> Credenciales:
    """«Modo negocio» (ONB-3): **otro token**, no un parámetro de la petición.

    Si el negocio activo viajara en cada llamada, cambiar de salón sería cambiar un número en
    la URL, y el aislamiento pasaría a depender de que nadie se equivocara nunca.
    """
    usuario = await sesion.get(User, usuario_id)
    if usuario is None:
        raise NoAutorizado("La sesión no es válida.")
    return await _abrir_sesion(
        sesion, usuario=usuario, superficie=superficie, negocio_id=negocio_id
    )


async def refrescar(sesion: AsyncSession, *, refresco: str) -> Credenciales:
    """Rota el refresco. Reutilizar uno ya rotado mata **toda la familia**.

    Esa es la señal de que el token se copió: el legítimo y el ladrón acaban presentando el
    mismo, y el segundo en llegar delata al primero. Cortar solo ese token dejaría al ladrón
    dentro con el siguiente.
    """
    ahora = datetime.now(UTC)
    fila = (
        await sesion.execute(select(Session).where(Session.refresh_token_hash == _hash(refresco)))
    ).scalar_one_or_none()

    if fila is None:
        raise NoAutorizado("La sesión no es válida.")

    if fila.revoked_at is not None or fila.rotated_at is not None:
        familia = (
            (await sesion.execute(select(Session).where(Session.family_id == fila.family_id)))
            .scalars()
            .all()
        )
        for hermana in familia:
            if hermana.revoked_at is None:
                hermana.revoked_at = ahora
                hermana.revoked_reason = "rotacion_reusada"
        await sesion.flush()
        raise NoAutorizado("Tu sesión se cerró por seguridad. Vuelve a entrar.")

    if fila.expires_at <= ahora:
        raise NoAutorizado("La sesión caducó. Vuelve a entrar.")

    usuario = await sesion.get(User, fila.user_id)
    if usuario is None:
        raise NoAutorizado("La sesión no es válida.")

    nuevas = await _abrir_sesion(
        sesion,
        usuario=usuario,
        superficie=fila.surface,
        negocio_id=fila.active_business_id,
        familia=fila.family_id,
    )
    fila.rotated_at = ahora
    await sesion.flush()
    return nuevas


async def cerrar_sesion(sesion: AsyncSession, *, refresco: str) -> None:
    """Cerrar sesión **surte efecto ya**, no cuando caduque el token.

    Es requisito de la Ley 81 tanto como de sentido común: si borrar la cuenta no cierra las
    sesiones abiertas, el borrado no significa nada durante treinta días.
    """
    fila = (
        await sesion.execute(select(Session).where(Session.refresh_token_hash == _hash(refresco)))
    ).scalar_one_or_none()

    if fila is not None and fila.revoked_at is None:
        fila.revoked_at = datetime.now(UTC)
        fila.revoked_reason = "cierre_sesion"
        await sesion.flush()
