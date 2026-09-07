"""Entrar y salir: correo y contraseña, sesión con refresco rotatorio y cambio a modo negocio.

Tres decisiones de ADR-0006 se materializan aquí y conviene no deshacerlas sin leerlo:

* **El código nunca se guarda en claro.** Si la base se filtra, un OTP en claro es una sesión
  regalada. Se guarda su hash y se compara en tiempo constante.
* **El refresco es opaco y rotatorio.** Cada uso emite uno nuevo e invalida el anterior; volver
  a presentar uno ya rotado invalida **toda la familia**, porque eso solo pasa cuando alguien
  copió el token. Sin familias, el ladrón y la víctima se turnan indefinidamente.
* **El token de acceso no lleva permisos**, solo quién eres y en qué negocio estás. Los
  permisos se resuelven contra la membresía en cada petición, así que echar a un profesional
  surte efecto en la siguiente llamada y no cuando caduque su token.

Desde la migración 0008 la puerta principal es **correo y contraseña**. El código de un solo
uso sigue existiendo, pero para lo que siempre debió ser: **verificar el teléfono** antes de la
primera reserva, porque el salón tiene que poder llamar. Más adelante entran el segundo factor
opcional y Google y Apple, y por eso `password_hash` admite nulo: una cuenta puede demostrar
quién es por otra vía.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.ajustes import obtener_ajustes
from agenda.errores import (
    CredencialesInvalidas,
    DatoInvalido,
    DemasiadosIntentos,
    NoAutorizado,
    OtpInvalido,
    YaExiste,
)
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
#: Diez caracteres. No se piden mayúsculas ni símbolos a propósito: esas reglas producen
#: «Panama1!» en todas las cuentas del país, y una frase larga y fácil de recordar es mejor
#: contraseña que un jeroglífico corto que acaba en un papel pegado al espejo.
LARGO_MINIMO_CONTRASENA = 10
#: argon2 hashea lo que le des, y darle un megabyte es una forma barata de tumbar el servidor.
LARGO_MAXIMO_CONTRASENA = 128
#: Fallos seguidos antes de cerrar la puerta un rato. Una contraseña sin freno se prueba a
#: miles por segundo; el código de un solo uso traía su límite de fábrica y al cambiar de
#: método hay que traérselo, o esto es un retroceso de seguridad disfrazado de comodidad.
MAXIMO_FALLOS = 8
BLOQUEO_TRAS_FALLOS = timedelta(minutes=15)

_hasher = PasswordHasher()

#: Un hash real de una contraseña que no es de nadie. Se verifica contra él cuando el correo no
#: existe, para que «no hay cuenta» y «la contraseña está mal» tarden lo mismo. Sin esto, el
#: tiempo de respuesta dice si un correo está registrado, y eso es media filtración.
_HASH_SENUELO = _hasher.hash("una contrasena que no es de nadie")


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
    #
    # Se invalidan **todos los vivos**, no solo los de la ventana de envíos. El índice
    # `uq_otp_codes_vivo` cubre cualquier código vivo del mismo destino y finalidad, así que uno
    # emitido hace media hora y nunca usado hacía chocar al nuevo con una violación de unicidad
    # que salía como **500 en la pantalla de acceso**. La lista de recientes sirve para contar
    # el límite de envíos; para invalidar hace falta mirar más atrás.
    ahora = datetime.now(UTC)
    vivos = (
        (
            await sesion.execute(
                select(OtpCode).where(
                    OtpCode.destination == telefono,
                    OtpCode.purpose == proposito,
                    OtpCode.consumed_at.is_(None),
                    OtpCode.invalidated_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for anterior in vivos:
        anterior.invalidated_at = ahora
    # El `UPDATE` tiene que llegar a la base antes del `INSERT` o el índice parcial sigue viendo
    # el código viejo como vivo.
    if vivos:
        await sesion.flush()

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
        # El intento se apunta **en otra transacción**. Escribirlo aquí y lanzar acto seguido
        # no servía de nada: `sesion.begin()` deshace todo al salir con excepción, así que el
        # contador volvía a cero en cada intento y `max_attempts` no llegaba a dispararse
        # nunca. Un límite de cinco intentos que no cuenta es un límite que no existe.
        await _apuntar_intento_de_otp(sesion, vigente.id)
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


@asynccontextmanager
async def _transaccion_aparte(sesion: AsyncSession) -> AsyncIterator[AsyncSession]:
    """Una transacción propia **en la misma base y con el mismo rol** que la que ya está abierta.

    Sirve para lo que tiene que sobrevivir a un `raise`: los contadores de intentos fallidos.
    La transacción de la petición se abre con `sesion.begin()`, que **deshace todo al salir con
    excepción**, así que un contador incrementado ahí y seguido de un `raise` se borra solo.

    El motor sale de la sesión que se pasa, y no de la fábrica global, porque si no las pruebas
    escribirían sus contadores en la base de desarrollo mientras leen de la de pruebas: pasarían
    en verde sin comprobar nada.
    """
    aparte = AsyncSession(bind=sesion.bind, expire_on_commit=False)
    try:
        async with aparte.begin():
            yield aparte
    finally:
        await aparte.close()


async def _apuntar_intento_de_otp(sesion: AsyncSession, codigo_id: uuid.UUID) -> None:
    """Suma un intento fallido al código, en su propia transacción y sin pisar el resto."""
    async with _transaccion_aparte(sesion) as aparte:
        fila = await aparte.get(OtpCode, codigo_id)
        if fila is None:
            return
        fila.attempts += 1
        if fila.attempts >= fila.max_attempts:
            fila.invalidated_at = datetime.now(UTC)


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


# ---------------------------------------------------------------------------------------------
# Correo y contraseña
# ---------------------------------------------------------------------------------------------


def normalizar_correo(correo: str) -> str:
    """Un correo es una credencial, así que se compara siempre en minúsculas y sin espacios.

    El único de la base es sobre `lower(email)`. Si el código no normaliza al escribir,
    «Ana@x.com» y «ana@x.com» son la misma fila para el índice y dos cadenas distintas para
    cualquier comparación: así se cuela un «no existe» con la contraseña correcta.
    """
    return correo.strip().lower()


def revisar_contrasena(contrasena: str) -> None:
    if len(contrasena) < LARGO_MINIMO_CONTRASENA:
        raise DatoInvalido(f"La contraseña necesita al menos {LARGO_MINIMO_CONTRASENA} caracteres.")
    if len(contrasena) > LARGO_MAXIMO_CONTRASENA:
        raise DatoInvalido(f"La contraseña no puede pasar de {LARGO_MAXIMO_CONTRASENA} caracteres.")
    if contrasena.isdigit():
        raise DatoInvalido("Una contraseña de solo números se adivina. Mezcla letras.")


async def _apuntar_fallo(sesion: AsyncSession, usuario_id: uuid.UUID) -> None:
    """Suma un intento fallido **en su propia transacción**, y bloquea al llegar al límite.

    Que sea otra transacción no es un capricho: ver `_transaccion_aparte`. Un bloqueo por
    intentos escrito dentro de la transacción que se deshace es un bloqueo de adorno, y eso se
    descubre el día que alguien prueba diez mil contraseñas y entra.
    """
    ahora = datetime.now(UTC)
    async with _transaccion_aparte(sesion) as aparte:
        usuario = await aparte.get(User, usuario_id)
        if usuario is None:
            return
        usuario.failed_logins = (usuario.failed_logins or 0) + 1
        if usuario.failed_logins >= MAXIMO_FALLOS:
            usuario.failed_logins = 0
            usuario.locked_until = ahora + BLOQUEO_TRAS_FALLOS


async def registrar(
    sesion: AsyncSession,
    *,
    nombre: str,
    correo: str,
    contrasena: str,
    telefono: str | None = None,
    superficie: str = "web",
) -> Credenciales:
    """Da de alta una cuenta con correo y contraseña, y la deja dentro.

    **No se pide el teléfono aquí.** Se pide y se verifica antes de la primera reserva, que es
    donde de verdad hace falta porque el salón tiene que poder llamar (D9). Exigirlo en el alta
    devolvería el trámite que este cambio venía a quitar.
    """
    correo = normalizar_correo(correo)
    nombre = nombre.strip()
    if not nombre:
        raise DatoInvalido("Hace falta un nombre.")
    if "@" not in correo or correo.startswith("@") or correo.endswith("@"):
        raise DatoInvalido("Ese correo no parece un correo.")
    revisar_contrasena(contrasena)

    # El único de la base es la garantía de verdad —dos altas a la vez pasarían las dos por
    # aquí—, pero comprobarlo antes convierte un 500 por violación de unicidad en un mensaje
    # que se entiende.
    repetido = (
        await sesion.execute(select(User.id).where(func.lower(User.email) == correo))
    ).scalar_one_or_none()
    if repetido is not None:
        raise YaExiste("Ya hay una cuenta con ese correo. Entra con tu contraseña.")

    if telefono:
        ocupado = (
            await sesion.execute(select(User.id).where(User.phone_e164 == telefono))
        ).scalar_one_or_none()
        if ocupado is not None:
            raise YaExiste("Ya hay una cuenta con ese teléfono.")

    usuario = User(
        full_name=nombre,
        email=correo,
        password_hash=_hasher.hash(contrasena),
        phone_e164=telefono or None,
    )
    sesion.add(usuario)
    await sesion.flush()
    sesion.add(AuthIdentity(user_id=usuario.id, provider="email", subject=correo))

    return await _abrir_sesion(sesion, usuario=usuario, superficie=superficie)


async def entrar(
    sesion: AsyncSession, *, correo: str, contrasena: str, superficie: str = "web"
) -> Credenciales:
    """Correo y contraseña. **Los dos fallan con el mismo mensaje**, a propósito.

    Distinguir «ese correo no existe» de «la contraseña está mal» le regala a quien prueba
    combinaciones la mitad del trabajo: le confirma qué cuentas existen. Por eso, además del
    mensaje, cuando el correo no existe se verifica igualmente contra un hash señuelo: si no,
    lo que no dice el texto lo dice el cronómetro.
    """
    correo = normalizar_correo(correo)
    ahora = datetime.now(UTC)

    usuario = (
        await sesion.execute(select(User).where(func.lower(User.email) == correo))
    ).scalar_one_or_none()

    if usuario is None or usuario.password_hash is None:
        with suppress(VerifyMismatchError, VerificationError):
            _hasher.verify(_HASH_SENUELO, contrasena)
        raise CredencialesInvalidas("Correo o contraseña incorrectos.")

    if usuario.locked_until is not None and usuario.locked_until > ahora:
        raise DemasiadosIntentos(
            "Demasiados intentos fallidos. Prueba otra vez dentro de unos minutos."
        )

    if usuario.status != "activo":
        raise NoAutorizado("Esta cuenta no está activa.")

    try:
        _hasher.verify(usuario.password_hash, contrasena)
    except (VerifyMismatchError, VerificationError):
        await _apuntar_fallo(sesion, usuario.id)
        raise CredencialesInvalidas("Correo o contraseña incorrectos.") from None

    # argon2 sube sus parámetros con los años. Rehashear al entrar es el único momento en que
    # se tiene la contraseña en claro para poder hacerlo.
    if _hasher.check_needs_rehash(usuario.password_hash):
        usuario.password_hash = _hasher.hash(contrasena)

    if usuario.failed_logins or usuario.locked_until is not None:
        usuario.failed_logins = 0
        usuario.locked_until = None

    identidad = (
        await sesion.execute(
            select(AuthIdentity).where(
                AuthIdentity.user_id == usuario.id, AuthIdentity.provider == "email"
            )
        )
    ).scalar_one_or_none()
    if identidad is None:
        sesion.add(AuthIdentity(user_id=usuario.id, provider="email", subject=correo))
    else:
        identidad.last_used_at = ahora

    return await _abrir_sesion(sesion, usuario=usuario, superficie=superficie)


async def cambiar_contrasena(
    sesion: AsyncSession, *, usuario_id: uuid.UUID, actual: str | None, nueva: str
) -> None:
    """Cambia la contraseña. Quien ya tiene una, la demuestra antes.

    `actual` solo puede venir vacío cuando la cuenta **no tiene contraseña todavía** —entró con
    código y ahora se pone una—. Si no se comprobara, una sesión robada bastaría para
    quedarse con la cuenta para siempre.
    """
    revisar_contrasena(nueva)
    usuario = await sesion.get(User, usuario_id)
    if usuario is None:
        raise NoAutorizado("La sesión no es válida.")

    if usuario.password_hash is not None:
        if not actual:
            raise CredencialesInvalidas("Escribe tu contraseña actual.")
        try:
            _hasher.verify(usuario.password_hash, actual)
        except (VerifyMismatchError, VerificationError):
            await _apuntar_fallo(sesion, usuario.id)
            raise CredencialesInvalidas("La contraseña actual no es correcta.") from None

    usuario.password_hash = _hasher.hash(nueva)
    usuario.failed_logins = 0
    usuario.locked_until = None

    # Cambiar la contraseña cierra las demás sesiones. Es lo que hace la gente cuando cree que
    # alguien entró en su cuenta, y si el intruso sigue dentro el gesto no sirvió de nada.
    await sesion.execute(
        update(Session)
        .where(Session.user_id == usuario_id, Session.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC), revoked_reason="cierre_sesion")
    )


async def verificar_telefono_de(
    sesion: AsyncSession, *, usuario_id: uuid.UUID, telefono: str, codigo: str
) -> None:
    """Ata un teléfono verificado a **la cuenta que ya está dentro**.

    Es lo que hay que llamar antes de la primera reserva, y **no** `verificar_otp`. La
    diferencia parece de matiz y no lo es: `verificar_otp` es *entrar*, así que busca la cuenta
    de ese número y, si no existe, **crea una nueva**. Llamarlo desde una sesión ya abierta
    dejaba a la persona dentro de otra cuenta —vacía, sin su nombre, sin sus favoritos y sin sus
    citas— sin un solo error por ninguna parte. Es de los peores fallos posibles porque parece
    que funcionó.

    Aquí no se abre ninguna sesión: solo se verifica el número y se guarda en su sitio.
    """
    ahora = datetime.now(UTC)

    usuario = await sesion.get(User, usuario_id)
    if usuario is None:
        raise NoAutorizado("La sesión no es válida.")

    # El número no puede estar en otra cuenta. Si se dejara, dos personas compartirían el
    # identificador natural y el salón llamaría a quien no es.
    duenno = (
        await sesion.execute(select(User).where(User.phone_e164 == telefono))
    ).scalar_one_or_none()
    if duenno is not None and duenno.id != usuario_id:
        raise YaExiste("Ese número ya está en otra cuenta.")

    vigente = (
        (
            await sesion.execute(
                select(OtpCode)
                .where(
                    OtpCode.destination == telefono,
                    OtpCode.purpose == "verificacion_telefono",
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

    if not hmac.compare_digest(vigente.code_hash, _hash(codigo)):
        await _apuntar_intento_de_otp(sesion, vigente.id)
        raise OtpInvalido()

    vigente.consumed_at = ahora
    usuario.phone_e164 = telefono
    usuario.phone_verified_at = ahora

    identidad = (
        await sesion.execute(
            select(AuthIdentity).where(
                AuthIdentity.user_id == usuario.id, AuthIdentity.provider == "telefono"
            )
        )
    ).scalar_one_or_none()
    if identidad is None:
        sesion.add(AuthIdentity(user_id=usuario.id, provider="telefono", subject=telefono))
    else:
        identidad.subject = telefono
        identidad.last_used_at = ahora

    await sesion.flush()
