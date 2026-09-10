"""Darse de baja: el otro lado de la Ley 81 (ADR-0025).

La ley da dos derechos que se pisan entre sí, y esto es el sitio donde se resuelven. Una persona
puede exigir que **sus datos desaparezcan**. Un salón tiene derecho a conservar **su
contabilidad y sus opiniones**, y quien lee esas opiniones también. Borrar la fila entera
rompería lo segundo; no borrar nada incumple lo primero.

## Lo que se hace: una lápida, no un `DELETE`

La fila del usuario **sobrevive vacía**. De ella cuelgan reservas —que son la contabilidad de un
salón— y opiniones de las que dependen otras personas para elegir. Lo que se va es todo lo que
identifica: el nombre, el correo, el teléfono, la foto y cualquier forma de volver a entrar.

Queda `status = 'eliminado'` y la fecha en `anonymized_at`, que es lo que permite demostrar
**cuándo** se atendió la petición el día que alguien pregunte.

## Las fichas del salón también

Cada salón tiene su propia ficha de esa persona, con su teléfono y sus notas. Son datos suyos y
se van igual; lo que se queda es la fila —con su contador de ausencias y su historial— para que
la contabilidad del salón siga cuadrando. Una ficha sin nombre es una estadística; una ficha con
nombre y teléfono es un dato personal.

## Lo que NO hace, y por qué

**No borra las opiniones.** Se quedan con el autor anonimizado (P14): un salón que reunió
cuarenta opiniones no las pierde porque alguien se dé de baja, y quien las lee tampoco.

**No borra nada fiscal.** Ese plazo lo dice la DGI y no el producto.

**No deja irse a quien tiene un salón vivo.** Un salón publicado cuyo dueño desaparece es un
negocio con clientas reservando y nadie detrás. Hay que cerrarlo o pasarlo a otra persona
primero, y se dice cuál es.

**Cancela lo que viniera.** Irse en silencio dejando tres citas puestas le deja al salón tres
plantones y ningún aviso. Se cancelan como cancelaciones del cliente —que es lo que son— y el
salón recupera las horas.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.dominio.reservas import Actor, EstadoReserva
from agenda.errores import ErrorDeDominio
from agenda.modelos.clientes import BusinessClient, Favorite
from agenda.modelos.identidad import AuthIdentity, Membership, Session, User
from agenda.modelos.negocio import Business
from agenda.modelos.reservas import Booking
from agenda.servicios import reservas as servicio_reservas

#: Lo que se pinta donde estaba el nombre. Es una frase y no una cadena vacía: en la agenda de
#: un salón, un hueco sin nombre parece un fallo del programa y alguien acaba llamando.
NOMBRE_BORRADO = "Cliente dado de baja"


class TieneUnSalonVivo(ErrorDeDominio):
    """No se puede desaparecer dejando un salón publicado detrás.

    No es una traba administrativa: un salón sin dueño sigue aceptando reservas, y las clientas
    que reserven se encontrarán la puerta cerrada. Cerrarlo o pasarlo a otra persona es de esa
    persona, no nuestro.
    """

    codigo = "TIENE_UN_SALON_VIVO"
    estado_http = 409


@dataclass(frozen=True)
class ResumenDeBaja:
    citas_canceladas: int
    fichas_anonimizadas: int
    cuando: datetime


async def dar_de_baja(sesion: AsyncSession, usuario_id: uuid.UUID) -> ResumenDeBaja:
    """Anonimiza a esa persona y corta todo lo que le permitiría volver a entrar."""
    ahora = datetime.now(UTC)
    usuario = await sesion.get(User, usuario_id)
    if usuario is None or usuario.anonymized_at is not None:
        # Repetir la baja no es un error: ya está hecha, y decir «no existe» a alguien que
        # acaba de borrarse suena a que algo salió mal.
        return ResumenDeBaja(citas_canceladas=0, fichas_anonimizadas=0, cuando=ahora)

    salones = (
        (
            await sesion.execute(
                select(Business.display_name)
                .join(Membership, Membership.business_id == Business.id)
                .where(
                    Membership.user_id == usuario_id,
                    Membership.role == "dueno",
                    Membership.status == "activa",
                    Business.status != "cerrado",
                )
            )
        )
        .scalars()
        .all()
    )
    if salones:
        raise TieneUnSalonVivo(
            "Todavía llevas "
            + (f"«{salones[0]}»" if len(salones) == 1 else f"{len(salones)} salones")
            + ". Ciérralo o pásalo a otra persona desde el portal del salón, y entonces "
            "podrás darte de baja."
        )

    # 1 · Lo que viniera se cancela. Un plantón sin aviso es lo peor que se le puede dejar.
    futuras = (
        (
            await sesion.execute(
                select(Booking).where(
                    Booking.client_user_id == usuario_id,
                    Booking.starts_at > ahora,
                    Booking.status.in_(["pendiente", "confirmada"]),
                )
            )
        )
        .scalars()
        .all()
    )
    for cita in futuras:
        # **El negocio se fija antes de tocar cada cita**, una por una. Esta baja corre sin
        # negocio —no es de ningún salón— y sin fijarlo el `UPDATE` sobre la agenda de un salón
        # **no falla: no encuentra nada**, que es la forma de fallo que busca ADR-0002. El
        # síntoma habría sido una baja que dice haber cancelado y deja las citas en pie.
        await sesion.execute(
            text("SELECT set_config('app.current_business_id', :negocio, true)"),
            {"negocio": str(cita.business_id)},
        )
        await servicio_reservas.cambiar_estado(
            sesion,
            cita,
            EstadoReserva.CANCELADA_CLIENTE,
            actor=Actor.CLIENTE,
            actor_user_id=usuario_id,
            motivo="La persona se dio de baja",
            ahora=ahora,
        )

    # 2 · Las fichas de cada salón: se vacían de datos personales y se quedan de estadística.
    #
    # También negocio a negocio y por lo mismo. Se leen primero con el negocio puesto, porque un
    # `UPDATE` sin tenant tocaría cero filas y contaría cero, sin decir una palabra.
    negocios_con_ficha = (
        (
            await sesion.execute(
                select(Booking.business_id).where(Booking.client_user_id == usuario_id).distinct()
            )
        )
        .scalars()
        .all()
    )
    fichas = 0
    for negocio_id in negocios_con_ficha:
        await sesion.execute(
            text("SELECT set_config('app.current_business_id', :negocio, true)"),
            {"negocio": str(negocio_id)},
        )
        fichas += (
            await sesion.execute(
                update(BusinessClient)
                .where(BusinessClient.user_id == usuario_id)
                .values(display_name=NOMBRE_BORRADO, phone_e164=None, email=None, notes=None)
            )
        ).rowcount or 0

    # Y se suelta el negocio: lo que queda —la lápida, las identidades, las sesiones— es de la
    # plataforma, y dejarlo puesto haría que esas tablas se leyeran con un tenant que no les toca.
    await sesion.execute(text("SELECT set_config('app.current_business_id', '', true)"))

    # 3 · Lo que solo sirve para volver: se borra de verdad, no se vacía.
    await sesion.execute(delete(AuthIdentity).where(AuthIdentity.user_id == usuario_id))
    await sesion.execute(delete(Session).where(Session.user_id == usuario_id))
    await sesion.execute(delete(Favorite).where(Favorite.user_id == usuario_id))

    # 4 · Y la lápida. El correo y el teléfono se vacían de verdad y no se «ofuscan»: un correo
    # ofuscado sigue identificando a una persona, que es justo lo que la ley no quiere.
    usuario.full_name = NOMBRE_BORRADO
    usuario.email = None
    usuario.phone_e164 = None
    usuario.phone_verified_at = None
    usuario.email_verified_at = None
    usuario.avatar_key = None
    usuario.password_hash = None
    usuario.status = "eliminado"
    usuario.anonymized_at = ahora
    await sesion.flush()

    return ResumenDeBaja(citas_canceladas=len(futuras), fichas_anonimizadas=fichas, cuando=ahora)


async def cuantas_cosas_se_van(sesion: AsyncSession, usuario_id: uuid.UUID) -> dict[str, int]:
    """Lo que se pierde, **antes** de perderlo.

    Una pantalla de baja que solo dice «esto no se puede deshacer» no informa de nada. Decir
    «tienes dos citas puestas y catorce hechas» es lo que permite decidir de verdad.
    """
    ahora = datetime.now(UTC)

    async def contar(*condiciones) -> int:
        return (
            await sesion.execute(select(func.count()).select_from(Booking).where(*condiciones))
        ).scalar_one()

    return {
        "citas_por_venir": await contar(
            Booking.client_user_id == usuario_id,
            Booking.starts_at > ahora,
            Booking.status.in_(["pendiente", "confirmada"]),
        ),
        "citas_pasadas": await contar(
            Booking.client_user_id == usuario_id, Booking.starts_at <= ahora
        ),
    }
