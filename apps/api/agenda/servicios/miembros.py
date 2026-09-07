"""Asignar personas al local: invitar por correo, aceptar y repartir papeles (punto 4 del encargo).

`memberships` ya tenía todo lo que hace falta —el rol, el estado, el token con hash y su
caducidad—: lo que faltaba era **la puerta**. Y la puerta tiene una dificultad real que conviene
dejar escrita, porque es la que decide el diseño entero:

> Quien acepta una invitación **todavía no está dentro de ningún negocio**, así que la política
> de aislamiento por tenant no le deja ni ver su propia invitación. Y no puede estar dentro
> antes de aceptar, porque aceptar es justamente lo que le mete.

Se resuelve como el resto de la casa: **declarando con qué se pregunta**. La migración 0010
añade `app.current_invite`, hermano de `app.current_business_id`, `app.current_user_id` y
`app.current_staff_id`, y dos políticas que solo dejan ver y aceptar **la fila cuyo token se
presenta**. Lo que se compara es el hash, así que la única forma de abrir esa puerta es tener el
token; y el token viaja al correo de la persona, que es la prueba de que el correo es suyo.

Y la regla que no se negocia: **un salón no puede quedarse sin ningún dueño.** Quitarle el papel
al último —cambiándoselo, revocándolo o dándolo de baja del equipo— es un error, no una casilla
que se marca y ya se verá. Un negocio sin dueño no lo puede arreglar nadie desde dentro: no
queda nadie que pueda invitar.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.ajustes import obtener_ajustes
from agenda.errores import DatoInvalido, NoAutorizado, NoExiste, SinDueno, YaExiste
from agenda.modelos.equipo import StaffProfile
from agenda.modelos.identidad import AuthIdentity, Membership, User
from agenda.modelos.negocio import Business
from agenda.notificaciones import cola
from agenda.servicios import identidad as servicio_identidad

ajustes = obtener_ajustes()
_hasher = PasswordHasher()

#: Una semana. Larga para que a nadie se le caduque mientras está de viaje, corta para que un
#: enlace olvidado en una bandeja no siga abriendo un salón dentro de seis meses.
VALIDEZ_INVITACION = timedelta(days=7)

#: Los dos papeles que se pueden repartir hoy. `recepcion` existe en la base desde la primera
#: migración y **no se ofrece**: es v2 (§14.5 del modelo de datos), y ofrecer un papel cuya
#: pantalla no existe es prometer permisos que nadie ha escrito.
ROLES_INVITABLES: tuple[str, ...] = ("dueno", "profesional")


@dataclass(frozen=True)
class Miembro:
    """Una persona del local, con su papel y en qué punto está."""

    id: uuid.UUID
    usuario_id: uuid.UUID
    nombre: str
    correo: str | None
    rol: str
    estado: str
    invitacion_caduca: datetime | None
    aceptada_en: datetime | None
    #: Su ficha de profesional en este salón, si la tiene. El dueño que además atiende la
    #: tiene; el dueño que solo lleva la caja, no.
    profesional_id: uuid.UUID | None
    #: Si es el único dueño activo. Lo usa la pantalla para no ofrecer un botón que va a
    #: fallar; la regla la impone el servidor igualmente.
    ultimo_dueno: bool


@dataclass(frozen=True)
class Invitacion:
    """Lo que se le enseña a quien abre el enlace, **antes** de que tenga cuenta."""

    negocio: str
    rol: str
    correo: str
    nombre: str
    caduca: datetime
    #: Si la cuenta ya existe con contraseña. Cuando es `False`, aceptar incluye elegir una: el
    #: token del correo es lo que demuestra que ese buzón es suyo.
    cuenta_con_contrasena: bool


@dataclass(frozen=True)
class InvitacionEnviada:
    miembro: Miembro
    #: El token en claro. **Solo se devuelve con el proveedor de desarrollo**, igual que el
    #: código de un solo uso: en cualquier otro entorno viaja al correo y esta respuesta no lo
    #: lleva. Si la API lo enseñara, el correo dejaría de demostrar nada.
    token: str
    enlace: str


def _hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


async def declarar_invitacion(sesion: AsyncSession, token: str) -> None:
    """Declara **con qué invitación** se pregunta, para esta transacción y solo para esta.

    `SET LOCAL`, como el negocio y el profesional: muere al terminar la transacción, así que la
    conexión vuelve al pool sin arrastrar el token de nadie.
    """
    await sesion.execute(
        text("SELECT set_config('app.current_invite', :token, true)"),
        {"token": _hash(token).hex()},
    )


# ── Leer el equipo ────────────────────────────────────────────────────────────────────────


async def listar(sesion: AsyncSession, *, negocio_id: uuid.UUID) -> list[Miembro]:
    """Todas las personas asignadas al local: activas, invitadas y revocadas."""
    filas = (
        await sesion.execute(
            select(Membership, User, StaffProfile.id)
            .join(User, User.id == Membership.user_id)
            .join(
                StaffProfile,
                (StaffProfile.user_id == Membership.user_id)
                & (StaffProfile.business_id == Membership.business_id)
                & (StaffProfile.deleted_at.is_(None)),
                isouter=True,
            )
            .where(Membership.business_id == negocio_id)
            .order_by(Membership.role, User.full_name)
        )
    ).all()

    duenos = _duenos_activos([m for m, _, _ in filas])
    return [
        _pintar(membresia, usuario, profesional_id, duenos)
        for membresia, usuario, profesional_id in filas
    ]


def _duenos_activos(membresias: list[Membership]) -> list[uuid.UUID]:
    return [m.id for m in membresias if m.role == "dueno" and m.status == "activa"]


def _pintar(
    membresia: Membership,
    usuario: User,
    profesional_id: uuid.UUID | None,
    duenos: list[uuid.UUID],
) -> Miembro:
    return Miembro(
        id=membresia.id,
        usuario_id=membresia.user_id,
        nombre=usuario.full_name,
        correo=usuario.email,
        rol=membresia.role,
        estado=membresia.status,
        invitacion_caduca=membresia.invite_expires_at,
        aceptada_en=membresia.accepted_at,
        profesional_id=profesional_id,
        ultimo_dueno=duenos == [membresia.id],
    )


# ── La regla del último dueño ─────────────────────────────────────────────────────────────


async def exigir_que_quede_un_dueno(
    sesion: AsyncSession, *, negocio_id: uuid.UUID, membresia_id: uuid.UUID
) -> None:
    """Falla si quitar a esa persona dejaría el salón sin ningún dueño activo.

    Se cuenta **en la base y en la misma transacción**, no con la lista que la pantalla tenía
    cargada: entre que se pintó el equipo y se pulsó el botón puede haber pasado cualquier cosa.
    """
    otros = (
        await sesion.execute(
            select(func.count())
            .select_from(Membership)
            .where(
                Membership.business_id == negocio_id,
                Membership.role == "dueno",
                Membership.status == "activa",
                Membership.id != membresia_id,
            )
        )
    ).scalar_one()

    if otros == 0:
        raise SinDueno(
            "Este salón se quedaría sin ningún dueño. Nombra dueño a otra persona antes."
        )


async def exigir_que_quede_un_dueno_por_usuario(
    sesion: AsyncSession, *, negocio_id: uuid.UUID, usuario_id: uuid.UUID | None
) -> None:
    """La misma regla, cuando lo que se tiene a mano es la persona y no su membresía.

    Es el caso de dar de baja del equipo a alguien que además es dueño — el dueño que corta el
    pelo, que en un salón de barrio es la norma. Sin esto, la baja del equipo revoca su
    membresía por la puerta de atrás y el salón se queda sin quien pueda invitar a nadie.
    """
    if usuario_id is None:
        return
    membresia = (
        await sesion.execute(
            select(Membership).where(
                Membership.business_id == negocio_id,
                Membership.user_id == usuario_id,
                Membership.status == "activa",
            )
        )
    ).scalar_one_or_none()

    if membresia is not None and membresia.role == "dueno":
        await exigir_que_quede_un_dueno(sesion, negocio_id=negocio_id, membresia_id=membresia.id)


# ── Invitar ───────────────────────────────────────────────────────────────────────────────


async def invitar(
    sesion: AsyncSession,
    *,
    negocio_id: uuid.UUID,
    invitado_por: uuid.UUID,
    correo: str,
    rol: str,
    nombre: str | None = None,
    profesional_id: uuid.UUID | None = None,
) -> InvitacionEnviada:
    """Invita a alguien al local con su papel, tenga cuenta o no.

    Cuando el correo no tiene cuenta se crea una **sin contraseña**. No es una cuenta a medias
    ni un hueco de seguridad: sin `password_hash` no se puede entrar con contraseña por ninguna
    vía (`entrar` lo comprueba explícitamente), y la única forma de activarla es presentar el
    token que llegó a ese correo. Es lo que permite que el dueño reparta los papeles del salón
    un domingo sin que nadie tenga que registrarse antes.

    Si el papel es `profesional`, la persona queda además **enlazada a una ficha de equipo**: o
    a una que el dueño ya había creado «sin cuenta» (ONB-4), o a una nueva. Sin ficha, aceptar
    la invitación dejaría a alguien con permiso para entrar en un salón donde no tiene agenda.
    """
    if rol not in ROLES_INVITABLES:
        raise DatoInvalido(f"El papel tiene que ser uno de: {', '.join(ROLES_INVITABLES)}.")

    correo = servicio_identidad.normalizar_correo(correo)
    if "@" not in correo or correo.startswith("@") or correo.endswith("@"):
        raise DatoInvalido("Ese correo no parece un correo.")

    usuario = await _usuario_para(sesion, correo=correo, nombre=nombre)
    membresia = await _membresia_para(sesion, negocio_id=negocio_id, usuario=usuario, rol=rol)

    if rol == "profesional":
        await _ficha_de_equipo(
            sesion,
            negocio_id=negocio_id,
            usuario=usuario,
            profesional_id=profesional_id,
        )

    token = secrets.token_urlsafe(32)
    ahora = datetime.now(UTC)
    membresia.role = rol
    membresia.status = "invitada"
    membresia.invited_by_user_id = invitado_por
    membresia.invite_channel = "email"
    membresia.invite_token_hash = _hash(token)
    membresia.invite_expires_at = ahora + VALIDEZ_INVITACION
    membresia.accepted_at = None
    membresia.revoked_at = None
    await sesion.flush()

    enlace = await _avisar(
        sesion,
        negocio_id=negocio_id,
        membresia=membresia,
        usuario=usuario,
        correo=correo,
        token=token,
    )

    miembro = _pintar(membresia, usuario, None, [])
    # El token en claro solo sale con el proveedor de desarrollo, y por el mismo motivo que el
    # código de un solo uso: si la API lo devuelve siempre, tener acceso al endpoint equivale a
    # tener acceso al buzón, y entonces el correo no demuestra nada.
    return InvitacionEnviada(
        miembro=miembro,
        token=token if ajustes.usa_proveedores_de_desarrollo else "",
        enlace=enlace if ajustes.usa_proveedores_de_desarrollo else "",
    )


async def _usuario_para(sesion: AsyncSession, *, correo: str, nombre: str | None) -> User:
    usuario = (
        await sesion.execute(select(User).where(func.lower(User.email) == correo))
    ).scalar_one_or_none()
    if usuario is not None:
        return usuario

    usuario = User(
        full_name=(nombre or correo.split("@", 1)[0]).strip() or correo,
        email=correo,
        # Sin contraseña **a propósito**: la cuenta existe para poder colgarle la membresía, y
        # solo se activa con el token que llega al correo.
        password_hash=None,
    )
    sesion.add(usuario)
    await sesion.flush()
    return usuario


async def _membresia_para(
    sesion: AsyncSession, *, negocio_id: uuid.UUID, usuario: User, rol: str
) -> Membership:
    membresia = (
        await sesion.execute(
            select(Membership).where(
                Membership.business_id == negocio_id, Membership.user_id == usuario.id
            )
        )
    ).scalar_one_or_none()

    if membresia is None:
        membresia = Membership(
            business_id=negocio_id, user_id=usuario.id, role=rol, status="invitada"
        )
        sesion.add(membresia)
        await sesion.flush()
        return membresia

    if membresia.status == "activa":
        raise YaExiste("Esa persona ya trabaja en este salón. Cámbiale el papel si hace falta.")

    # Estaba invitada o revocada: se reutiliza la fila. Crear otra chocaría con el único de
    # negocio y persona, y volver a invitar a alguien que se fue es lo normal.
    return membresia


async def _ficha_de_equipo(
    sesion: AsyncSession,
    *,
    negocio_id: uuid.UUID,
    usuario: User,
    profesional_id: uuid.UUID | None,
) -> StaffProfile:
    """Enlaza a la persona con su ficha de equipo, o se la crea."""
    ya_tiene = (
        await sesion.execute(
            select(StaffProfile).where(
                StaffProfile.business_id == negocio_id,
                StaffProfile.user_id == usuario.id,
                StaffProfile.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if ya_tiene is not None:
        return ya_tiene

    if profesional_id is not None:
        ficha = (
            await sesion.execute(
                select(StaffProfile).where(
                    StaffProfile.id == profesional_id,
                    StaffProfile.business_id == negocio_id,
                    StaffProfile.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if ficha is None:
            raise NoExiste("Ese profesional no existe en este negocio.")
        if ficha.user_id is not None:
            raise YaExiste("Esa ficha de profesional ya está enlazada a otra cuenta.")
        ficha.user_id = usuario.id
        await sesion.flush()
        return ficha

    ficha = StaffProfile(business_id=negocio_id, user_id=usuario.id, display_name=usuario.full_name)
    sesion.add(ficha)
    await sesion.flush()
    return ficha


async def _avisar(
    sesion: AsyncSession,
    *,
    negocio_id: uuid.UUID,
    membresia: Membership,
    usuario: User,
    correo: str,
    token: str,
) -> str:
    """Encola el correo de la invitación. **Encolar no es enviar** (ADR-0007).

    La clave de idempotencia lleva dentro la membresía y el instante de emisión del token: dos
    pulsaciones del mismo botón no mandan dos correos, y reinvitar de verdad —token nuevo—
    manda uno nuevo, que es lo que se espera.
    """
    enlace = f"{ajustes.url_publica_web.rstrip('/')}/invitacion/{token}"
    negocio = await sesion.get(Business, negocio_id)

    await cola.encolar(
        sesion,
        hecho=cola.Hecho.INVITACION_AL_EQUIPO,
        entidad="membership",
        entidad_id=membresia.id,
        canal="email",
        destino=correo,
        destinatario="staff" if membresia.role == "profesional" else "negocio",
        programado_para=datetime.now(UTC),
        negocio_id=negocio_id,
        usuario_id=usuario.id,
        caduca_en=membresia.invite_expires_at,
        variables={
            "negocio": negocio.display_name if negocio else "",
            "rol": membresia.role,
            "enlace": enlace,
        },
        sufijo_de_clave=membresia.invite_token_hash.hex()[:16],
    )
    return enlace


# ── Cambiar el papel y quitar a alguien ───────────────────────────────────────────────────


async def cambiar_papel(
    sesion: AsyncSession, *, negocio_id: uuid.UUID, membresia_id: uuid.UUID, rol: str
) -> Miembro:
    """Sube o baja de papel. Bajar al último dueño **no se puede**."""
    if rol not in ROLES_INVITABLES:
        raise DatoInvalido(f"El papel tiene que ser uno de: {', '.join(ROLES_INVITABLES)}.")

    membresia, usuario = await _membresia_del_negocio(sesion, negocio_id, membresia_id)
    if membresia.role == "dueno" and rol != "dueno" and membresia.status == "activa":
        await exigir_que_quede_un_dueno(sesion, negocio_id=negocio_id, membresia_id=membresia_id)

    membresia.role = rol
    if rol == "profesional":
        await _ficha_de_equipo(sesion, negocio_id=negocio_id, usuario=usuario, profesional_id=None)
    await sesion.flush()
    return await _recargar(sesion, negocio_id, membresia, usuario)


async def revocar(
    sesion: AsyncSession, *, negocio_id: uuid.UUID, membresia_id: uuid.UUID
) -> Miembro:
    """Quita a alguien del local. Surte efecto **en la siguiente llamada** (ADR-0006).

    No borra la fila: el rastro de quién trabajó aquí y hasta cuándo es lo que permite entender
    una agenda de hace tres meses. Y la ficha de equipo tampoco se toca — sus citas siguen
    ahí; darla de baja es otro gesto, con su propio aviso.
    """
    membresia, usuario = await _membresia_del_negocio(sesion, negocio_id, membresia_id)
    if membresia.role == "dueno" and membresia.status == "activa":
        await exigir_que_quede_un_dueno(sesion, negocio_id=negocio_id, membresia_id=membresia_id)

    membresia.status = "revocada"
    membresia.revoked_at = datetime.now(UTC)
    membresia.invite_token_hash = None
    membresia.invite_expires_at = None
    await sesion.flush()
    return await _recargar(sesion, negocio_id, membresia, usuario)


async def _membresia_del_negocio(
    sesion: AsyncSession, negocio_id: uuid.UUID, membresia_id: uuid.UUID
) -> tuple[Membership, User]:
    fila = (
        await sesion.execute(
            select(Membership, User)
            .join(User, User.id == Membership.user_id)
            .where(Membership.id == membresia_id, Membership.business_id == negocio_id)
        )
    ).first()
    if fila is None:
        raise NoExiste("Esa persona no está asignada a este salón.")
    return fila[0], fila[1]


async def _recargar(
    sesion: AsyncSession, negocio_id: uuid.UUID, membresia: Membership, usuario: User
) -> Miembro:
    profesional_id = (
        await sesion.execute(
            select(StaffProfile.id).where(
                StaffProfile.business_id == negocio_id,
                StaffProfile.user_id == usuario.id,
                StaffProfile.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    todas = (
        (await sesion.execute(select(Membership).where(Membership.business_id == negocio_id)))
        .scalars()
        .all()
    )
    return _pintar(membresia, usuario, profesional_id, _duenos_activos(list(todas)))


# ── Aceptar ───────────────────────────────────────────────────────────────────────────────


async def previsualizar(sesion: AsyncSession, *, token: str) -> Invitacion:
    """Lo que se enseña al abrir el enlace: qué salón, qué papel y si hay que elegir contraseña."""
    membresia, usuario = await _invitacion_viva(sesion, token)
    negocio_id = membresia.business_id
    await sesion.execute(
        text("SELECT set_config('app.current_business_id', :negocio, true)"),
        {"negocio": str(negocio_id)},
    )
    negocio = await sesion.get(Business, negocio_id)

    return Invitacion(
        negocio=negocio.display_name if negocio else "",
        rol=membresia.role,
        correo=usuario.email or "",
        nombre=usuario.full_name,
        caduca=membresia.invite_expires_at,
        cuenta_con_contrasena=usuario.password_hash is not None,
    )


async def aceptar(
    sesion: AsyncSession,
    *,
    token: str,
    contrasena: str | None = None,
    usuario_en_sesion: uuid.UUID | None = None,
    superficie: str = "web",
) -> servicio_identidad.Credenciales:
    """Acepta la invitación y devuelve una sesión **ya en modo negocio**.

    Dos caminos, y la diferencia importa:

    * **La cuenta todavía no tiene contraseña** (la creó la invitación). Se elige aquí, y con
      eso queda activada. El token es la prueba de que ese buzón es suyo, así que el correo se
      da por verificado: es exactamente lo que demuestra haber recibido el enlace.
    * **La cuenta ya existe y tiene contraseña.** Entonces hace falta **estar dentro con esa
      cuenta**. Un token de correo no puede dar acceso a una cuenta que ya tiene dueño: quien
      interceptara el enlace entraría en la cuenta de otra persona, no solo en el salón.
    """
    membresia, usuario = await _invitacion_viva(sesion, token)

    if usuario.password_hash is None:
        if not contrasena:
            raise DatoInvalido("Elige una contraseña para activar tu cuenta.")
        servicio_identidad.revisar_contrasena(contrasena)
        usuario.password_hash = _hasher.hash(contrasena)
        usuario.email_verified_at = datetime.now(UTC)
        await _identidad_de_correo(sesion, usuario)
    elif usuario_en_sesion != usuario.id:
        raise NoAutorizado(
            "Esa invitación es de otra cuenta. Entra con el correo al que llegó y vuelve a abrirla."
        )

    # **Se declara también quién es**, y no es un adorno: PostgreSQL exige que, tras un
    # `UPDATE`, la fila resultante siga siendo visible para quien la escribió. Al borrar el
    # token, la política que dejaba verla —`memberships_por_invitacion`— deja de aplicar, y sin
    # otra que la alcance el `UPDATE` sale con «new row violates row-level security policy».
    # Con el usuario declarado, quien la ve es `memberships_propias`: la membresía es suya
    # desde este momento, que es exactamente lo que se acaba de decidir.
    await sesion.execute(
        text("SELECT set_config('app.current_user_id', :usuario, true)"),
        {"usuario": str(usuario.id)},
    )

    membresia.status = "activa"
    membresia.accepted_at = datetime.now(UTC)
    membresia.invite_token_hash = None
    membresia.invite_expires_at = None
    await sesion.flush()

    return await servicio_identidad.cambiar_a_negocio(
        sesion,
        usuario_id=usuario.id,
        negocio_id=membresia.business_id,
        superficie=superficie,
    )


async def _identidad_de_correo(sesion: AsyncSession, usuario: User) -> None:
    ya = (
        await sesion.execute(
            select(AuthIdentity).where(
                AuthIdentity.user_id == usuario.id, AuthIdentity.provider == "email"
            )
        )
    ).scalar_one_or_none()
    if ya is None and usuario.email:
        sesion.add(
            AuthIdentity(
                user_id=usuario.id,
                provider="email",
                subject=usuario.email,
                email_at_provider=usuario.email,
                email_verified=True,
            )
        )
        await sesion.flush()


async def _invitacion_viva(sesion: AsyncSession, token: str) -> tuple[Membership, User]:
    """La membresía que abre ese token, o un error que no distingue casos.

    Caducada, ya usada e inventada dan **el mismo error** a propósito: separarlos le diría a
    quien prueba tokens al azar cuándo va por buen camino. La comprobación de verdad no está
    aquí de todos modos — está en las políticas de la migración 0010, que solo dejan ver y
    actualizar la fila cuyo hash coincide y sigue viva.
    """
    await declarar_invitacion(sesion, token)

    membresia = (
        await sesion.execute(select(Membership).where(Membership.invite_token_hash == _hash(token)))
    ).scalar_one_or_none()

    ahora = datetime.now(UTC)
    if (
        membresia is None
        or membresia.status != "invitada"
        or membresia.revoked_at is not None
        or membresia.invite_expires_at is None
        or membresia.invite_expires_at <= ahora
    ):
        raise NoAutorizado("Esa invitación ya no vale. Pídele al salón que te mande otra.")

    usuario = await sesion.get(User, membresia.user_id)
    if usuario is None:
        raise NoAutorizado("Esa invitación ya no vale. Pídele al salón que te mande otra.")
    return membresia, usuario
