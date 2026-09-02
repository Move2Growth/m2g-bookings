"""Reseñas: dejarlas, leerlas, responderlas y reportarlas (REV-1 a REV-5).

Cuatro audiencias tocan las reseñas y **cada una tiene su ruta y su serializador**:

* la **clienta** deja la suya desde su cita (`/mi/reservas/{id}/review`),
* **cualquiera** las lee en el perfil del salón (`/publico/negocios/{slug}/reviews`),
* el **negocio** las lee y responde una vez (`/negocio/reviews`),
* y **el que se topa con una ofensiva** la reporta, con sesión: reportar sin identificarse es
  regalar una herramienta de acoso a quien quiera tumbar a un competidor.

**El nombre completo de quien opina no sale nunca.** Se sirve como «Yaritza B.», que es lo que
identifica a la persona ante quien la conoce sin publicar su nombre completo junto a la
dirección del salón al que va cada mes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.api.comunes import url_de_media
from agenda.api.dependencias import (
    Identidad,
    SesionNegocio,
    SesionPlataforma,
    SesionPublica,
    identidad_actual,
)
from agenda.bd import sesion_sin_tenant
from agenda.errores import NoExiste, YaExiste
from agenda.modelos.identidad import User
from agenda.modelos.negocio import Business
from agenda.modelos.reservas import Booking
from agenda.modelos.reviews import (
    BusinessRatingStats,
    Review,
    ReviewMedia,
    ReviewReply,
    ReviewReport,
)
from agenda.servicios import resenas as servicio_resenas

router = APIRouter(prefix="/api/v1", tags=["reseñas"])

#: Cuántas reseñas se sirven por página en el perfil público.
POR_PAGINA = 20

#: Motivos que se aceptan en un reporte. Lista cerrada y no texto libre: la cola de moderación
#: se ordena por motivo, y con texto libre no se puede ordenar por nada.
MOTIVOS = ("ofensiva", "falsa", "spam", "datos_personales", "otra")


class FotoDeResena(BaseModel):
    id: uuid.UUID
    url: str


class RespuestaDelNegocio(BaseModel):
    texto: str
    fecha: datetime


class ResenaPublica(BaseModel):
    """Lo que se ve en el perfil. **Sin nombre completo y sin nada de contacto.**"""

    id: uuid.UUID
    nota: int = Field(ge=1, le=5)
    texto: str | None
    fecha: datetime
    autor: str = Field(description="Nombre de pila e inicial, por ejemplo «Yaritza B.»")
    profesional: str | None = None
    nota_al_profesional: int | None = None
    fotos: list[FotoDeResena]
    respuesta: RespuestaDelNegocio | None


class ResumenDeResenas(BaseModel):
    """El agregado del negocio, con **las dos medias** y por qué son distintas.

    `media` es la aritmética, que es la que el dueño espera ver. `puntuacion` es la bayesiana
    (REV-5): con pocas reseñas se parece a la media de la plataforma y solo con volumen el
    negocio se separa de ella. Es la que se enseña y la que entra en el ranking, porque es lo
    que impide que una sola reseña de cinco estrellas adelante a un salón con ochenta de 4,7.
    """

    total: int
    media: float | None
    puntuacion: float | None
    reparto: dict[int, int] = Field(description="Cuántas de cada nota, de 1 a 5")


class ResenasDelPerfil(BaseModel):
    resumen: ResumenDeResenas
    resenas: list[ResenaPublica]


class NuevaResena(BaseModel):
    rating: int = Field(ge=1, le=5)
    texto: str | None = Field(default=None, max_length=2000)
    profesional_id: uuid.UUID | None = Field(
        default=None, description="Por defecto, quien atendió la cita (REV-2)"
    )
    nota_al_profesional: int | None = Field(default=None, ge=1, le=5)
    fotos: list[str] = Field(
        default_factory=list,
        max_length=6,
        description="Claves de almacén. Nacen pendientes de moderar y no salen hasta aprobarse",
    )


class NuevaRespuesta(BaseModel):
    texto: str = Field(min_length=1, max_length=1500)


class NuevoReporte(BaseModel):
    motivo: str = Field(pattern="^(ofensiva|falsa|spam|datos_personales|otra)$")
    detalle: str | None = Field(default=None, max_length=1000)


class ResenaDelPanel(ResenaPublica):
    """La misma reseña vista por el salón: añade si ya la respondió y si está reportada."""

    reportes_abiertos: int
    estado: str = Field(description="publicada | oculta | retirada")


# ── La clienta ────────────────────────────────────────────────────────────────────────────


@router.post(
    "/mi/reservas/{reserva_id}/review", status_code=201, summary="Opinar de mi cita (REV-1, REV-2)"
)
async def dejar_resena(
    reserva_id: uuid.UUID,
    nueva: NuevaResena,
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> ResenaPublica:
    """Una reseña **por cita completada**, dentro de la ventana del negocio y una sola vez.

    Las tres condiciones se comprueban en `servicios.resenas`, no aquí: son reglas de negocio y
    tienen que valer igual si algún día la reseña entra por otro camino.
    """
    reserva = await sesion.get(Booking, reserva_id)
    if reserva is None or reserva.client_user_id != identidad.usuario_id:
        raise NoExiste("Esa cita no es tuya o ya no existe.")

    # A partir de aquí se escribe en la casa del salón: la reseña es suya, cuelga de su negocio
    # y su política de tenant exige que el negocio esté declarado.
    await sesion.execute(
        text("SELECT set_config('app.current_business_id', :negocio, true)"),
        {"negocio": str(reserva.business_id)},
    )

    resena = await servicio_resenas.crear(
        sesion,
        reserva,
        autor_user_id=identidad.usuario_id,
        nota=nueva.rating,
        texto=nueva.texto,
        nota_al_profesional=nueva.nota_al_profesional,
        profesional_id=nueva.profesional_id,
        fotos=nueva.fotos,
    )
    autor = await sesion.get(User, identidad.usuario_id)
    return ResenaPublica(
        id=resena.id,
        nota=resena.rating,
        texto=resena.body,
        fecha=resena.created_at or datetime.now(UTC),
        autor=_nombre_corto(autor.full_name if autor else None),
        nota_al_profesional=resena.staff_rating,
        fotos=[],
        respuesta=None,
    )


@router.post("/mi/reviews/{resena_id}/reportar", status_code=201, summary="Reportar (REV-4)")
async def reportar_como_cliente(
    resena_id: uuid.UUID,
    reporte: NuevoReporte,
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> dict[str, str]:
    """Manda la reseña a la cola de moderación. **Exige sesión** y queda registrado quién.

    Reportar de forma anónima sería regalar una herramienta de acoso: la reseña se oculta
    mientras se revisa, así que sin autor identificable bastaría con un guion para tumbar a la
    competencia una tarde.
    """
    return await _reportar(
        sesion, resena_id, reporte, quien="cliente", user_id=identidad.usuario_id
    )


# ── Cualquiera ────────────────────────────────────────────────────────────────────────────


@router.get("/publico/negocios/{slug}/reviews", summary="Reseñas del perfil (REV-1, REV-5)")
async def resenas_del_negocio(
    slug: str,
    sesion: SesionPublica,
    pagina: Annotated[int, Query(ge=1)] = 1,
) -> ResenasDelPerfil:
    """Las reseñas publicadas de un salón, con su respuesta y el agregado bayesiano.

    Sale por la sesión pública, que **no tiene permiso** sobre reservas ni sobre fichas de
    cliente: aunque este código quisiera cruzar la reseña con la cita para enseñar qué se hizo,
    la base no se lo permitiría.
    """
    negocio = (
        await sesion.execute(select(Business).where(Business.slug == slug))
    ).scalar_one_or_none()
    if negocio is None:
        raise NoExiste("Ese negocio no está publicado.")

    filas = (
        (
            await sesion.execute(
                select(Review)
                .where(Review.business_id == negocio.id, Review.status == "publicada")
                .order_by(Review.created_at.desc())
                .offset((pagina - 1) * POR_PAGINA)
                .limit(POR_PAGINA)
            )
        )
        .scalars()
        .all()
    )

    return ResenasDelPerfil(
        resumen=await _resumen(sesion, negocio.id),
        resenas=await _pintar_publicas(sesion, list(filas)),
    )


# ── El negocio ────────────────────────────────────────────────────────────────────────────


@router.get("/negocio/reviews", summary="Mis reseñas y cuáles faltan por responder (REV-3)")
async def resenas_del_panel(
    sesion_negocio: SesionNegocio,
    sin_responder: Annotated[
        bool, Query(description="Solo las que aún no tienen respuesta")
    ] = False,
    pagina: Annotated[int, Query(ge=1)] = 1,
) -> list[ResenaDelPanel]:
    sesion, identidad = sesion_negocio

    consulta = (
        select(Review)
        .where(Review.business_id == identidad.negocio_id)
        .order_by(Review.created_at.desc())
        .offset((pagina - 1) * POR_PAGINA)
        .limit(POR_PAGINA)
    )
    if sin_responder:
        consulta = consulta.where(
            ~select(ReviewReply.id).where(ReviewReply.review_id == Review.id).exists()
        )

    filas = list((await sesion.execute(consulta)).scalars().all())
    publicas = await _pintar_publicas(sesion, filas, con_rol_de_negocio=True)

    reportes: dict[uuid.UUID, int] = {}
    if filas:
        for review_id, total in (
            await sesion.execute(
                select(ReviewReport.review_id, func.count())
                .where(
                    ReviewReport.review_id.in_([f.id for f in filas]),
                    ReviewReport.status.in_(("abierto", "en_revision")),
                )
                .group_by(ReviewReport.review_id)
            )
        ).all():
            reportes[review_id] = total

    por_id = {f.id: f for f in filas}
    return [
        ResenaDelPanel(
            **publica.model_dump(),
            reportes_abiertos=reportes.get(publica.id, 0),
            estado=por_id[publica.id].status,
        )
        for publica in publicas
    ]


@router.post(
    "/negocio/reviews/{resena_id}/responder", status_code=201, summary="Responder una vez (REV-3)"
)
async def responder(
    resena_id: uuid.UUID, respuesta: NuevaRespuesta, sesion_negocio: SesionNegocio
) -> RespuestaDelNegocio:
    """**Una respuesta por reseña**, y lo garantiza el único de la base, no la pantalla.

    Es una decisión de producto que el brief fija en REV-3: la respuesta del negocio no puede
    convertirse en un hilo. Quien quiera seguir hablando tiene el WhatsApp del salón, que es
    donde esa conversación se arregla de verdad.
    """
    sesion, identidad = sesion_negocio

    resena = (
        await sesion.execute(
            select(Review).where(Review.id == resena_id, Review.business_id == identidad.negocio_id)
        )
    ).scalar_one_or_none()
    if resena is None:
        raise NoExiste("Esa reseña no existe en este negocio.")

    ya = (
        await sesion.execute(select(ReviewReply).where(ReviewReply.review_id == resena.id))
    ).scalar_one_or_none()
    if ya is not None:
        raise YaExiste("Ya respondiste a esa reseña.")

    fila = ReviewReply(
        business_id=identidad.negocio_id,
        review_id=resena.id,
        author_user_id=identidad.usuario_id,
        body=respuesta.texto.strip(),
    )
    sesion.add(fila)
    await sesion.flush()
    return RespuestaDelNegocio(texto=fila.body, fecha=fila.created_at or datetime.now(UTC))


@router.post(
    "/negocio/reviews/{resena_id}/reportar", status_code=201, summary="Reportar una reseña (REV-4)"
)
async def reportar_como_negocio(
    resena_id: uuid.UUID, reporte: NuevoReporte, sesion_negocio: SesionNegocio
) -> dict[str, str]:
    """El salón que recibe una reseña falsa la manda a moderación. **No la puede ocultar él.**

    Ocultarla es decisión de M2G desde la consola: si el negocio pudiera esconder lo que no le
    gusta, el rating dejaría de significar nada y el marketplace entero con él.
    """
    sesion, identidad = sesion_negocio
    return await _reportar(
        sesion,
        resena_id,
        reporte,
        quien="negocio",
        user_id=identidad.usuario_id,
        negocio_id=identidad.negocio_id,
    )


# ── Piezas internas ───────────────────────────────────────────────────────────────────────


async def _reportar(
    sesion: AsyncSession,
    resena_id: uuid.UUID,
    reporte: NuevoReporte,
    *,
    quien: str,
    user_id: uuid.UUID,
    negocio_id: uuid.UUID | None = None,
) -> dict[str, str]:
    resena = await sesion.get(Review, resena_id)
    if resena is None or (negocio_id is not None and resena.business_id != negocio_id):
        raise NoExiste("Esa reseña no existe.")

    if negocio_id is None:
        # La clienta no está «dentro» de ningún salón, así que hay que declarar el negocio de
        # la reseña antes de escribir: `review_reports` es una tabla del negocio.
        await sesion.execute(
            text("SELECT set_config('app.current_business_id', :negocio, true)"),
            {"negocio": str(resena.business_id)},
        )

    sesion.add(
        ReviewReport(
            business_id=resena.business_id,
            review_id=resena.id,
            reporter_user_id=user_id,
            reporter_kind=quien,
            reason=(f"{reporte.motivo}: {reporte.detalle}" if reporte.detalle else reporte.motivo),
            status="abierto",
        )
    )
    await sesion.flush()
    return {"estado": "recibido"}


def _nombre_corto(nombre: str | None) -> str:
    """«Yaritza Beitía» → «Yaritza B.». Sin nombre, «Cliente».

    No es cosmética: el nombre completo junto a la dirección del salón al que alguien va cada
    mes, en una página que indexa Google, es más información de la que esa persona quiso dar
    cuando escribió que le gustó el corte.
    """
    partes = (nombre or "").strip().split()
    if not partes:
        return "Cliente"
    if len(partes) == 1:
        return partes[0]
    return f"{partes[0]} {partes[1][0].upper()}."


async def _resumen(sesion: AsyncSession, negocio_id: uuid.UUID) -> ResumenDeResenas:
    """El agregado precalculado más el reparto por nota, que es lo que da confianza.

    Se lee de `business_rating_stats` y **no se recalcula al vuelo**: recorrer las reseñas de
    un salón en cada carga del perfil es la consulta que hace lento lo que más se visita.
    """
    stats = await sesion.get(BusinessRatingStats, negocio_id)
    reparto = dict(
        (
            await sesion.execute(
                select(Review.rating, func.count())
                .where(Review.business_id == negocio_id, Review.status == "publicada")
                .group_by(Review.rating)
            )
        ).all()
    )
    return ResumenDeResenas(
        total=stats.reviews_count if stats else 0,
        media=float(stats.rating_avg) if stats and stats.rating_avg is not None else None,
        puntuacion=(
            float(stats.rating_bayesian) if stats and stats.rating_bayesian is not None else None
        ),
        reparto={nota: reparto.get(nota, 0) for nota in range(1, 6)},
    )


async def _pintar_publicas(
    sesion: AsyncSession, filas: list[Review], *, con_rol_de_negocio: bool = False
) -> list[ResenaPublica]:
    """Serializador público. Tres consultas para la página entera, no tres por reseña."""
    if not filas:
        return []
    ids = [f.id for f in filas]

    respuestas = {
        fila.review_id: fila
        for fila in (
            (await sesion.execute(select(ReviewReply).where(ReviewReply.review_id.in_(ids))))
            .scalars()
            .all()
        )
    }
    fotos: dict[uuid.UUID, list[ReviewMedia]] = {}
    for foto in (
        (
            await sesion.execute(
                select(ReviewMedia).where(
                    ReviewMedia.review_id.in_(ids),
                    ReviewMedia.moderation_status == "aprobada",
                )
            )
        )
        .scalars()
        .all()
    ):
        fotos.setdefault(foto.review_id, []).append(foto)

    nombres = await _nombres_de_autores(sesion, filas, con_rol_de_negocio=con_rol_de_negocio)

    return [
        ResenaPublica(
            id=f.id,
            nota=f.rating,
            texto=f.body,
            fecha=f.created_at,
            autor=nombres.get(f.author_user_id, "Cliente"),
            nota_al_profesional=f.staff_rating,
            fotos=[
                FotoDeResena(id=m.id, url=url_de_media(m.storage_key) or "")
                for m in fotos.get(f.id, [])
            ],
            respuesta=(
                RespuestaDelNegocio(texto=respuestas[f.id].body, fecha=respuestas[f.id].created_at)
                if f.id in respuestas
                else None
            ),
        )
        for f in filas
    ]


async def _nombres_de_autores(
    sesion: AsyncSession, filas: list[Review], *, con_rol_de_negocio: bool
) -> dict[uuid.UUID, str]:
    """Los nombres, acortados. **El rol público no tiene permiso sobre `users`**, y está bien.

    Para el perfil público hay que abrir una segunda sesión con el rol de la aplicación y leer
    solo el identificador y el nombre. Es más incómodo que conceder un `SELECT` al rol del
    marketplace, y es a propósito: abrirle `users` al rol que sirve las páginas públicas
    dejaría los teléfonos de todo el mundo a un `SELECT` mal escrito de distancia.
    """
    autores = [f.author_user_id for f in filas if f.author_user_id is not None]
    if not autores:
        return {}

    consulta = select(User.id, User.full_name).where(User.id.in_(autores))
    if con_rol_de_negocio:
        filas_usuarios = (await sesion.execute(consulta)).all()
    else:
        async with sesion_sin_tenant() as otra:
            filas_usuarios = (await otra.execute(consulta)).all()

    return {usuario_id: _nombre_corto(nombre) for usuario_id, nombre in filas_usuarios}
