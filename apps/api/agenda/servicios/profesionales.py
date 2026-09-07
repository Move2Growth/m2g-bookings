"""El profesional como entidad: su slug, cuánta gente ha atendido y su nota.

Tres cosas viven aquí porque las necesitan sitios que no se conocen entre sí —el perfil
público, la lista del salón, la búsqueda de profesionales y el panel—, y tenerlas duplicadas
sería la forma más silenciosa de que el perfil enseñara una nota y la búsqueda ordenara por
otra.

**Ni el número de atendidos ni la nota se guardan en una columna.** Es una decisión, no una
omisión: un contador guardado se desincroniza el primer día que alguien cancela una cita a
mano en la base, y entonces el perfil dice «312 clientas atendidas» mientras la agenda dice
otra cosa. Se calculan al leer, con una consulta agrupada por profesional —una para toda la
lista, no una por persona—.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.dominio.ranking import PesosRanking, rating_bayesiano
from agenda.dominio.textos import slug_desde
from agenda.modelos.equipo import StaffProfile
from agenda.modelos.reservas import Booking
from agenda.modelos.reviews import Review


@dataclass(frozen=True)
class Atendidos:
    """Cuánta gente ha pasado por sus manos. Solo citas **completadas**.

    Son dos números y no uno porque contestan a dos preguntas distintas: `citas` es cuánto
    trabajo lleva hecho y `clientes` es a cuánta gente distinta ha atendido. Una clienta que
    vuelve cada mes cuenta doce veces en el primero y una en el segundo.
    """

    citas: int = 0
    clientes: int = 0


@dataclass(frozen=True)
class Nota:
    """Su nota, en las dos formas que hacen falta.

    `media` es la media simple, que es lo que la persona espera ver de sí misma. `puntuacion`
    es la **bayesiana** (REV-5, ADR-0009), que es la que se enseña y la que ordena: una sola
    reseña de cinco estrellas no puede adelantar a quien lleva ochenta de 4,7.
    """

    numero: int = 0
    media: float | None = None
    puntuacion: float | None = None


async def slug_libre(
    sesion: AsyncSession,
    negocio_id: uuid.UUID,
    deseado: str,
    *,
    excluir_id: uuid.UUID | None = None,
) -> str:
    """Un slug que no choque **dentro de este negocio**, derivado de lo que se pidió.

    Único por negocio y no global a propósito: la misma persona puede trabajar en dos salones
    y ser `yaris` en los dos. Un único global obligaría a la segunda a llamarse `yaris-2` en
    un salón donde no hay ninguna otra Yaris, que no hay forma de explicar.

    El índice único de la base es el que manda; esto solo evita el choque previsible. Si dos
    altas simultáneas piden el mismo, una recibe el error de la base — que es lo correcto: la
    base es la que sabe la verdad.
    """
    base = slug_desde(deseado)
    tomados = set(
        (
            await sesion.execute(
                select(StaffProfile.slug).where(
                    StaffProfile.business_id == negocio_id,
                    StaffProfile.slug.is_not(None),
                    StaffProfile.deleted_at.is_(None),
                    *([StaffProfile.id != excluir_id] if excluir_id else []),
                )
            )
        )
        .scalars()
        .all()
    )
    if base not in tomados:
        return base
    numero = 2
    while f"{base}-{numero}" in tomados:
        numero += 1
    return f"{base}-{numero}"


async def atendidos(
    sesion: AsyncSession, negocio_id: uuid.UUID, staff_ids: list[uuid.UUID]
) -> dict[uuid.UUID, Atendidos]:
    """Citas completadas y clientes distintos, por profesional. **Una consulta para todos.**

    Necesita una sesión con el negocio fijado: `bookings` no es pública ni puede serlo, y está
    bien que no lo sea. Quien lo llama desde una ruta pública abre esa sesión igual que hace
    la disponibilidad, para el negocio concreto que la persona está mirando.
    """
    if not staff_ids:
        return {}

    filas = await sesion.execute(
        select(
            Booking.staff_id,
            func.count().label("citas"),
            func.count(func.distinct(Booking.business_client_id)).label("clientes"),
        )
        .where(
            Booking.business_id == negocio_id,
            Booking.staff_id.in_(staff_ids),
            Booking.status == "completada",
        )
        .group_by(Booking.staff_id)
    )
    return {
        staff_id: Atendidos(citas=citas, clientes=clientes)
        for staff_id, citas, clientes in filas.all()
    }


async def notas(
    sesion: AsyncSession, staff_ids: list[uuid.UUID], pesos: PesosRanking
) -> dict[uuid.UUID, Nota]:
    """La nota de cada profesional, sacada de las reseñas publicadas que le apuntan.

    `reviews.staff_rating` es la nota **de la persona** y es opcional (REV-2); cuando no la
    hay se usa la del negocio, que es la que la clienta sí dejó. Inventarse un «sin nota»
    cuando alguien puso cinco estrellas a la cita completa sería tirar el dato que hay.

    Se hace con la sesión que se reciba: con el rol público en el marketplace —las reseñas
    publicadas de un negocio publicado son dato público— y con el del negocio en el panel.
    """
    if not staff_ids:
        return {}

    puntuacion = func.coalesce(Review.staff_rating, Review.rating)
    filas = await sesion.execute(
        select(
            Review.staff_id,
            func.count().label("numero"),
            func.sum(func.cast(puntuacion, Integer)).label("suma"),
        )
        .where(
            Review.staff_id.in_(staff_ids),
            Review.status == "publicada",
            # Explícito aunque hoy sea imposible: `rating` es obligatorio, así que el
            # `coalesce` nunca da nulo. Si algún día lo diera, sin esta línea la suma entera
            # saldría nula y la nota desaparecería sin que fallara nada.
            puntuacion.is_not(None),
        )
        .group_by(Review.staff_id)
    )

    salida: dict[uuid.UUID, Nota] = {}
    for staff_id, numero, suma in filas.all():
        total = int(suma or 0)
        salida[staff_id] = Nota(
            numero=int(numero),
            media=round(total / numero, 2) if numero else None,
            puntuacion=round(rating_bayesiano(total, int(numero), pesos), 2),
        )
    return salida
