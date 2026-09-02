"""La cola de notificaciones: encolar, decidir y entregar (ADR-0007).

`notifications` **es la cola**. No hay una segunda cola en Redis con el estado de verdad, y eso
no es una simplificación: es lo que permite responder «¿le llegó el recordatorio?» mirando una
tabla en vez de adivinar, y lo que hace que la idempotencia sobreviva a un redespliegue a mitad
de trabajo.

Tres ideas sostienen este módulo y ninguna es decorativa:

1. **La clave de idempotencia sale del hecho, no del momento.** `recordatorio_24h:booking:{id}`
   identifica *el recordatorio de 24 h de esa cita*, exista una vez o se intente crear veinte.
   Como la columna es única, encolar dos veces no inserta dos filas: el conflicto se traga en
   silencio porque **es un reintento, no un error**. El planificador puede ejecutarse dos veces
   —y se ejecutará— sin que nadie reciba dos mensajes a las siete de la mañana.
2. **Decidir y entregar son dos pasos.** Decidir mira las preferencias de la persona y del
   negocio y elige canal; entregar habla con el proveedor. Apagar un canal es entonces
   configuración, y no toca el código que sabe de reservas.
3. **Una notificación que ya no tiene sentido se descarta, no se reintenta.** El recordatorio
   de dos horas de una cita que ya empezó no mejora por insistir: llegar tarde es peor que no
   llegar. Por eso `expires_at` se mira **antes** que los intentos.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as insert_pg
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.modelos.notificaciones import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
)
from agenda.notificaciones.proveedores import (
    MensajeSaliente,
    ProveedorDeMensajes,
    ProveedorNoConfigurado,
)

# ── El vocabulario de hechos ──────────────────────────────────────────────────────────────


class Hecho(StrEnum):
    """**Qué pasó**, que es lo que dispara un mensaje y lo que nombra su clave.

    Este enumerado es el trabajo de diseño por adelantado del que habla ADR-0007. Obliga a
    contestar «¿qué hecho manda este mensaje?» antes de escribirlo, y esa pregunta es
    exactamente la que evita el duplicado: dos hechos distintos son dos mensajes legítimos;
    el mismo hecho contado dos veces es una queja.
    """

    RESERVA_CREADA = "reserva_creada"
    RESERVA_CONFIRMADA = "reserva_confirmada"
    RESERVA_CANCELADA = "reserva_cancelada"
    RESERVA_REPROGRAMADA = "reserva_reprogramada"
    RECORDATORIO_24H = "recordatorio_24h"
    RECORDATORIO_2H = "recordatorio_2h"
    REVIEW_SOLICITADA = "review_solicitada"
    CITAS_SIN_CERRAR = "citas_sin_cerrar"


#: A qué categoría de preferencias pertenece cada hecho (NTF-3). Quien apaga «recordatorios»
#: no quiere apagar el aviso de que le cancelaron la cita, y al revés.
CATEGORIA_DEL_HECHO: dict[Hecho, str] = {
    Hecho.RESERVA_CREADA: "reservas",
    Hecho.RESERVA_CONFIRMADA: "reservas",
    Hecho.RESERVA_CANCELADA: "reservas",
    Hecho.RESERVA_REPROGRAMADA: "reservas",
    Hecho.RECORDATORIO_24H: "recordatorios",
    Hecho.RECORDATORIO_2H: "recordatorios",
    Hecho.REVIEW_SOLICITADA: "reviews",
    Hecho.CITAS_SIN_CERRAR: "operativa",
}

#: Orden en que se prueban los canales cuando nadie dice otra cosa. WhatsApp primero porque es
#: el canal del país (NTF-1) y el correo detrás porque siempre está.
ORDEN_DE_CANALES: tuple[str, ...] = ("whatsapp", "email", "push", "sms")


def clave_de_idempotencia(
    hecho: Hecho | str, entidad: str, entidad_id: uuid.UUID | str, sufijo: str | None = None
) -> str:
    """`recordatorio_24h:booking:{id}` — el hecho, sobre qué, y de qué fila.

    El sufijo existe para los hechos que se repiten legítimamente sobre la misma entidad: el
    aviso diario de citas sin cerrar es uno por negocio **y por día**, así que la fecha entra
    en la clave. Sin él, el aviso del martes impediría el del miércoles.
    """
    hecho = hecho.value if isinstance(hecho, Hecho) else hecho
    clave = f"{hecho}:{entidad}:{entidad_id}"
    return f"{clave}:{sufijo}" if sufijo else clave


# ── Decidir ───────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Decision:
    """Por dónde se manda y por qué. `canal is None` significa **no mandar**.

    El motivo se guarda aunque no se mande. «No tenía teléfono» y «lo apagó a propósito» son
    dos cosas distintas y solo una de ellas es un problema.
    """

    canal: str | None
    destino: str | None
    motivo: str

    @property
    def hay_que_mandar(self) -> bool:
        return self.canal is not None and self.destino is not None


async def decidir_canal(
    sesion: AsyncSession,
    *,
    hecho: Hecho,
    destinos: dict[str, str | None],
    usuario_id: uuid.UUID | None = None,
    negocio_id: uuid.UUID | None = None,
    candidatos: tuple[str, ...] = ORDEN_DE_CANALES,
) -> Decision:
    """Elige el primer canal que la persona no ha apagado **y** por el que se la puede alcanzar.

    Este paso no habla con ningún proveedor y no escribe nada: se puede llamar mil veces sin
    consecuencias. Es a propósito — la decisión de canal entra en pantallas de vista previa y
    en el back-office, y una función que decide y además manda no se puede enseñar.

    Ausencia de preferencia significa **sí**: el usuario que nunca tocó los ajustes recibe el
    recordatorio de su cita. Solo una fila con `enabled = false` apaga un canal.
    """
    categoria = CATEGORIA_DEL_HECHO.get(hecho, "operativa")

    sujeto = []
    if usuario_id is not None:
        sujeto.append(NotificationPreference.user_id == usuario_id)
    if negocio_id is not None:
        sujeto.append(NotificationPreference.business_id == negocio_id)
    if not sujeto:
        apagados: set[str] = set()
    else:
        filas = (
            (
                await sesion.execute(
                    select(NotificationPreference.channel).where(
                        or_(*sujeto),
                        NotificationPreference.category == categoria,
                        NotificationPreference.enabled.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        apagados = set(filas)

    sin_destino = True
    for canal in candidatos:
        destino = destinos.get(canal)
        if not destino:
            continue
        sin_destino = False
        if canal in apagados:
            continue
        return Decision(canal=canal, destino=destino, motivo="preferencia")

    if sin_destino:
        return Decision(None, None, "sin_destino")
    return Decision(None, None, "todos_los_canales_apagados")


# ── Encolar ───────────────────────────────────────────────────────────────────────────────


async def encolar(
    sesion: AsyncSession,
    *,
    hecho: Hecho,
    entidad: str,
    entidad_id: uuid.UUID | str,
    canal: str,
    destino: str | None,
    destinatario: str,
    programado_para: datetime,
    negocio_id: uuid.UUID | None = None,
    usuario_id: uuid.UUID | None = None,
    plantilla: str | None = None,
    variables: dict[str, Any] | None = None,
    caduca_en: datetime | None = None,
    locale: str = "es-PA",
    cola: str = "default",
    sufijo_de_clave: str | None = None,
) -> uuid.UUID | None:
    """Mete una fila en la cola. Devuelve su identificador, o `None` si ya estaba.

    **`None` no es un fallo.** Significa que ese hecho ya está encolado, que es el resultado
    correcto de que el planificador se haya ejecutado dos veces o de que un trabajo se
    reintentara a mitad. Por eso el conflicto se traga en silencio: quien llama no tiene nada
    que arreglar, y tratar esto como un error convertiría el funcionamiento normal en ruido.

    Quien garantiza la unicidad es **el índice único de la tabla**, no una consulta previa.
    Un `SELECT` antes del `INSERT` deja una ventana entre los dos, y dos trabajadores a la vez
    caben de sobra en esa ventana.
    """
    clave = clave_de_idempotencia(hecho, entidad, entidad_id, sufijo_de_clave)

    sentencia = (
        insert_pg(Notification)
        .values(
            idempotency_key=clave,
            business_id=negocio_id,
            recipient_user_id=usuario_id,
            recipient_kind=destinatario,
            channel=canal,
            template_key=plantilla or hecho.value,
            locale=locale,
            payload=variables or {},
            destination=destino,
            status="pendiente",
            scheduled_for=programado_para,
            expires_at=caduca_en,
            queue=cola,
        )
        .on_conflict_do_nothing(index_elements=[Notification.idempotency_key])
        .returning(Notification.id)
    )
    return (await sesion.execute(sentencia)).scalar_one_or_none()


# ── Entregar ──────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PoliticaDeReintentos:
    """Cuántas veces se insiste y cuánto se espera entre intentos.

    El retroceso es exponencial con **tope por arriba y tope en el número de intentos**. Los
    dos topes hacen falta y por motivos distintos: sin el de la espera, el quinto intento caería
    dos días después y el mensaje ya no valdría; sin el del número, una notificación rota
    seguiría costando llamadas al proveedor para siempre.
    """

    intentos_maximos: int = 5
    espera_base: timedelta = timedelta(minutes=1)
    factor: int = 4
    espera_maxima: timedelta = timedelta(hours=6)

    def espera_tras(self, intentos: int) -> timedelta:
        """Espera después del intento número `intentos` (1 → base, 2 → base×factor…)."""
        crecida = self.espera_base * (self.factor ** max(intentos - 1, 0))
        return min(crecida, self.espera_maxima)

    def agotada(self, intentos: int) -> bool:
        return intentos >= self.intentos_maximos


POLITICA_POR_DEFECTO = PoliticaDeReintentos()


@dataclass
class ResumenDeEntrega:
    """Lo que hizo una pasada del trabajador. Se registra y se enseña en el back-office."""

    enviadas: int = 0
    fallidas: int = 0
    descartadas: int = 0
    reintentables: int = 0

    @property
    def total(self) -> int:
        return self.enviadas + self.fallidas + self.descartadas + self.reintentables


def caducada(notificacion: Notification, *, ahora: datetime) -> bool:
    """Si ya no tiene sentido mandarla.

    Se mira antes que los intentos y antes que el proveedor: no se gasta una llamada de pago en
    un mensaje que, si llegara, molestaría.
    """
    return notificacion.expires_at is not None and ahora >= notificacion.expires_at


async def tomar_pendientes(
    sesion: AsyncSession, *, ahora: datetime | None = None, limite: int = 50
) -> list[Notification]:
    """Las que toca intentar ahora, **bloqueadas para este trabajador**.

    `FOR UPDATE SKIP LOCKED` es lo que permite que haya varios trabajadores sin repartirse el
    trabajo por acuerdo: cada uno se lleva las que puede bloquear y salta las que otro ya tiene.
    Sin él, dos trabajadores leerían la misma fila y el mensaje saldría dos veces — y la clave
    de idempotencia no lo impediría, porque la fila es la misma.
    """
    ahora = ahora or datetime.now(UTC)
    sentencia = (
        select(Notification)
        .where(
            Notification.status == "pendiente",
            Notification.scheduled_for <= ahora,
            or_(Notification.next_attempt_at.is_(None), Notification.next_attempt_at <= ahora),
        )
        .order_by(Notification.scheduled_for)
        .limit(limite)
        .with_for_update(skip_locked=True)
    )
    return list((await sesion.execute(sentencia)).scalars().all())


async def entregar(
    sesion: AsyncSession,
    notificacion: Notification,
    *,
    proveedores: dict[str, ProveedorDeMensajes],
    ahora: datetime | None = None,
    politica: PoliticaDeReintentos = POLITICA_POR_DEFECTO,
) -> str:
    """Intenta mandar una notificación y **deja su estado final escrito**. Devuelve ese estado.

    El orden de las comprobaciones es el contrato de este módulo:

    1. ¿Sigue teniendo sentido? Si no, `descartada` y se acabó.
    2. ¿Está en un estado desde el que se pueda mandar? Si no, se deja como está.
    3. Se intenta. Si el proveedor acepta, `enviada`. Si no, o quedan intentos y vuelve a
       `pendiente` con su próxima hora, o se agotaron y queda `fallida`.

    Lo que **no** hace es reintentar aquí mismo en un bucle. Un reintento inmediato contra un
    proveedor caído es tráfico que no ayuda; la espera está para que la siguiente pasada lo
    encuentre levantado.
    """
    ahora = ahora or datetime.now(UTC)

    if caducada(notificacion, ahora=ahora):
        notificacion.status = "descartada"
        notificacion.last_error = "Caducada: la hora del mensaje ya pasó y mandarlo tarde es peor."
        await sesion.flush()
        return notificacion.status

    if notificacion.status not in ("pendiente", "enviando"):
        return notificacion.status

    proveedor = proveedores.get(notificacion.channel)
    notificacion.status = "enviando"
    notificacion.attempts = (notificacion.attempts or 0) + 1
    await sesion.flush()

    if proveedor is None:
        estado = _anotar_fallo(
            notificacion,
            f"No hay proveedor para el canal «{notificacion.channel}».",
            ahora=ahora,
            politica=politica,
        )
        await sesion.flush()
        return estado
    if not notificacion.destination:
        # Sin destino no hay reintento que valga: insistir cinco veces sobre un teléfono que no
        # existe es gastar por gastar.
        notificacion.status = "fallida"
        notificacion.last_error = "Sin destino: la notificación se encoló sin teléfono ni correo."
        await sesion.flush()
        return notificacion.status

    mensaje = MensajeSaliente(
        canal=notificacion.channel,
        destino=notificacion.destination,
        plantilla=notificacion.template_key,
        locale=notificacion.locale,
        variables=dict(notificacion.payload or {}),
        notificacion_id=notificacion.id,
    )

    try:
        resultado = await proveedor.enviar(mensaje)
    except (ProveedorNoConfigurado, NotImplementedError) as error:
        # Configuración, no avería. Se reintenta igual: alguien puede estar poniendo el token
        # ahora mismo, y descartar el mensaje perdería lo que ya estaba encolado.
        estado = _anotar_fallo(notificacion, str(error), ahora=ahora, politica=politica)
        await sesion.flush()
        return estado
    except Exception as error:  # el proveedor falló de verdad: se anota y se reintenta
        estado = _anotar_fallo(notificacion, repr(error), ahora=ahora, politica=politica)
        await sesion.flush()
        return estado

    sesion.add(
        NotificationDelivery(
            notification_id=notificacion.id,
            provider=resultado.proveedor,
            provider_message_id=resultado.id_en_el_proveedor,
            status=resultado.estado,
            cost_minor=resultado.coste_minor,
            currency=resultado.moneda,
            raw=resultado.crudo,
        )
    )
    notificacion.status = "enviada"
    notificacion.sent_at = ahora
    notificacion.next_attempt_at = None
    notificacion.last_error = None
    await sesion.flush()
    return notificacion.status


async def entregar_pendientes(
    sesion: AsyncSession,
    *,
    proveedores: dict[str, ProveedorDeMensajes],
    ahora: datetime | None = None,
    limite: int = 50,
    politica: PoliticaDeReintentos = POLITICA_POR_DEFECTO,
) -> ResumenDeEntrega:
    """Una pasada del trabajador de la cola sobre lo que toca ahora."""
    ahora = ahora or datetime.now(UTC)
    resumen = ResumenDeEntrega()

    for notificacion in await tomar_pendientes(sesion, ahora=ahora, limite=limite):
        estado = await entregar(
            sesion, notificacion, proveedores=proveedores, ahora=ahora, politica=politica
        )
        match estado:
            case "enviada":
                resumen.enviadas += 1
            case "fallida":
                resumen.fallidas += 1
            case "descartada":
                resumen.descartadas += 1
            case _:
                resumen.reintentables += 1

    return resumen


def _anotar_fallo(
    notificacion: Notification,
    error: str,
    *,
    ahora: datetime,
    politica: PoliticaDeReintentos,
) -> str:
    """Vuelve a `pendiente` con su próxima hora, o se rinde con `fallida`."""
    notificacion.last_error = error[:1000]
    if politica.agotada(notificacion.attempts or 0):
        notificacion.status = "fallida"
        notificacion.next_attempt_at = None
        return notificacion.status

    notificacion.status = "pendiente"
    notificacion.next_attempt_at = ahora + politica.espera_tras(notificacion.attempts or 1)
    return notificacion.status
