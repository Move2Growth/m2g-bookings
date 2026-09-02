"""Reseñas: cuándo se puede dejar una y qué le pasa al rating del negocio (REV-1 a REV-5).

Las tres condiciones de REV-1 no están en el mismo sitio y no pueden estarlo:

* **Una reseña por reserva** la garantiza la base con un único sobre `booking_id`. Es la única
  de las tres que no depende de nada variable, así que ahí es donde tiene que estar: dos
  peticiones simultáneas no crean dos reseñas ni aunque el código se despiste.
* **Que la cita esté completada** y **que estemos dentro de la ventana** se comprueban aquí,
  porque dependen de un parámetro configurable por negocio (`review_window_days`) y del
  reloj. Una restricción de base sobre el reloj no se puede satisfacer de forma determinista.

Y el agregado: **el rating que se enseña y el que entra en el ranking es el bayesiano**
(REV-5, ADR-0009). La fórmula ya existe en `agenda.dominio.ranking` y no se reimplementa aquí;
lo que hace este módulo es mantener actualizada la fila de `business_rating_stats` cada vez que
una reseña entra, se oculta o se retira.

Se recalcula **contando**, no sumando incrementalmente. Un contador que se incrementa se
desincroniza en cuanto una reseña se oculta desde el back-office, y entonces el número que ve
todo el mundo miente sin que nada falle. Contar cuesta una consulta y siempre dice la verdad.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.dominio.ranking import rating_bayesiano
from agenda.dominio.reservas import EstadoReserva
from agenda.errores import ResenaNoPermitida, YaExiste
from agenda.modelos.negocio import BusinessSettings
from agenda.modelos.reservas import Booking, BookingEvent
from agenda.modelos.reviews import BusinessRatingStats, Review, ReviewMedia
from agenda.servicios.pesos import pesos_vigentes

#: Ventana por defecto si el negocio todavía no tiene fila de ajustes. Es la del brief y la
#: misma que trae `business_settings.review_window_days`; aquí solo es el último recurso.
VENTANA_POR_DEFECTO = timedelta(days=14)


async def validar_que_se_puede_resenar(
    sesion: AsyncSession,
    reserva: Booking,
    *,
    autor_user_id: uuid.UUID,
    ahora: datetime | None = None,
) -> None:
    """Las tres condiciones de REV-1, con un mensaje distinto para cada una.

    El código de error es el mismo —para quien reseña todos significan «esta reseña no se
    puede dejar»— pero el mensaje sí cambia, porque «tu cita todavía no está cerrada» y «ya
    pasaron los 14 días» llevan a hacer cosas distintas.
    """
    ahora = ahora or datetime.now(UTC)

    if reserva.client_user_id != autor_user_id:
        # No se distingue de «no existe» a propósito: decir «existe pero no es tuya» convierte
        # cualquier identificador en un oráculo.
        raise ResenaNoPermitida("Esa cita no es tuya o ya no existe.")

    if EstadoReserva(reserva.status) is not EstadoReserva.COMPLETADA:
        raise ResenaNoPermitida(
            "Solo se puede opinar de una cita que el salón dio por atendida. "
            "Si ya fuiste, pídeles que la cierren.",
            estado=reserva.status,
        )

    ajustes = await sesion.get(BusinessSettings, reserva.business_id)
    ventana = timedelta(days=ajustes.review_window_days) if ajustes else VENTANA_POR_DEFECTO
    # Se cuenta desde que la cita **terminó**, no desde que se marcó completada: si el salón
    # tarda tres días en cerrarla, esos tres días no se los puede comer al cliente.
    if ahora > reserva.ends_at + ventana:
        raise ResenaNoPermitida(
            f"El plazo para opinar de esa cita era de {ventana.days} días y ya pasó.",
            limite=(reserva.ends_at + ventana).isoformat(),
        )

    ya = (
        await sesion.execute(select(Review.id).where(Review.booking_id == reserva.id))
    ).scalar_one_or_none()
    if ya is not None:
        # La base también lo impide con su único; esto es para poder decirlo con palabras en
        # vez de con un error de integridad.
        raise YaExiste("Ya dejaste tu opinión de esa cita.")


async def crear(
    sesion: AsyncSession,
    reserva: Booking,
    *,
    autor_user_id: uuid.UUID,
    nota: int,
    texto: str | None = None,
    nota_al_profesional: int | None = None,
    profesional_id: uuid.UUID | None = None,
    fotos: list[str] | None = None,
    ahora: datetime | None = None,
) -> Review:
    """Crea la reseña, sus fotos y el rastro en el historial de la cita.

    Las fotos nacen **pendientes de moderación** y no salen en el perfil hasta que se aprueban
    (la política de la migración 0007 solo deja ver las aprobadas). Es lo contrario del texto,
    que se publica en el acto: una frase desafortunada se retira; una foto inapropiada, una vez
    servida, ya la vio alguien.
    """
    ahora = ahora or datetime.now(UTC)
    await validar_que_se_puede_resenar(sesion, reserva, autor_user_id=autor_user_id, ahora=ahora)

    resena = Review(
        business_id=reserva.business_id,
        booking_id=reserva.id,
        author_user_id=autor_user_id,
        # Por defecto, al profesional que la atendió: es de quien opina quien opina.
        staff_id=profesional_id or reserva.staff_id,
        rating=nota,
        staff_rating=nota_al_profesional,
        body=(texto or "").strip() or None,
        status="publicada",
        published_at=ahora,
    )
    sesion.add(resena)
    await sesion.flush()

    for clave in fotos or []:
        sesion.add(
            ReviewMedia(
                business_id=reserva.business_id,
                review_id=resena.id,
                storage_key=clave,
                moderation_status="pendiente",
            )
        )

    sesion.add(
        BookingEvent(
            business_id=reserva.business_id,
            booking_id=reserva.id,
            type="review_solicitada",
            from_status=reserva.status,
            to_status=reserva.status,
            actor_kind="cliente",
            actor_user_id=autor_user_id,
            payload={"review_id": str(resena.id), "rating": nota},
        )
    )

    await sesion.flush()
    await recalcular_agregado(sesion, reserva.business_id, ahora=ahora)
    return resena


async def recalcular_agregado(
    sesion: AsyncSession, negocio_id: uuid.UUID, *, ahora: datetime | None = None
) -> BusinessRatingStats:
    """Recuenta las reseñas publicadas de un negocio y deja el bayesiano ya resuelto.

    Se guardan las dos medias y hacen falta las dos: `rating_avg` es la media simple, que es
    lo que el dueño espera ver en su panel, y `rating_bayesian` es lo que se enseña al público
    y lo que entra en el ranking. Explicarle la diferencia a un dueño es más fácil que
    explicarle por qué su «4,9» aparece como «4,3».
    """
    ahora = ahora or datetime.now(UTC)

    total, suma, ultima = (
        await sesion.execute(
            select(
                func.count(Review.id),
                func.coalesce(func.sum(Review.rating), 0),
                func.max(Review.created_at),
            ).where(
                Review.business_id == negocio_id,
                # Solo las publicadas: una reseña oculta por moderación no puede seguir
                # pesando en el rating, que es justamente para lo que se oculta.
                Review.status == "publicada",
            )
        )
    ).one()

    pesos = await pesos_vigentes(sesion)
    bayesiano = rating_bayesiano(int(suma), int(total), pesos)

    fila = await sesion.get(BusinessRatingStats, negocio_id)
    if fila is None:
        fila = BusinessRatingStats(business_id=negocio_id)
        sesion.add(fila)

    fila.reviews_count = int(total)
    fila.rating_sum = int(suma)
    # `Numeric(3,2)` en la base: se redondea aquí para que lo que se guarda y lo que se calcula
    # sean el mismo número y nadie tenga que preguntarse de dónde sale el último decimal.
    fila.rating_avg = Decimal(f"{suma / total:.2f}") if total else None
    fila.rating_bayesian = Decimal(f"{bayesiano:.2f}")
    fila.last_review_at = ultima
    fila.updated_at = ahora

    await sesion.flush()
    return fila
