"""El profesional visto desde fuera: su perfil, el equipo de un salón y buscar personas.

Aquí está el cambio de fondo del encargo del 7 de septiembre: **la clienta elige primero con
quién se quiere atender**. Hasta ahora el único camino era negocio → servicio → profesional, y
quien busca «Yaris» no tenía por dónde entrar. Estas rutas abren el camino contrario sin
quitar el que había: buscar persona → ver su perfil → elegir uno de **sus** servicios → hora.

**El motor de disponibilidad no cambia ni una línea**: ya sabía calcular los huecos de un
profesional concreto. Lo único que faltaba era poder llegar hasta él sin pasar por la ficha
del salón.

Como todo lo público de este proyecto: **ni un teléfono, ni un correo, ni un nombre completo
de clienta**. Los serializadores de este módulo son propios y no se comparten con los del
panel; es la única forma de que un cambio en el panel no filtre nada aquí por descuido.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from geoalchemy2.functions import ST_DWithin, ST_SetSRID
from pydantic import BaseModel, Field
from sqlalchemy import Float, cast, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.api.comunes import url_de_media
from agenda.api.dependencias import SesionPublica
from agenda.api.publico import RespuestaDisponibilidad, ServicioPublico, SlotPublico
from agenda.api.resenas import ResenaPublica, pintar_publicas
from agenda.bd import sesion_de_negocio
from agenda.dominio.textos import url_de_red
from agenda.errores import NoExiste
from agenda.modelos.catalogo import Service, ServiceCategory
from agenda.modelos.equipo import StaffMedia, StaffProfile, StaffService
from agenda.modelos.marketplace import Zone
from agenda.modelos.negocio import Business, Location
from agenda.modelos.reviews import Review
from agenda.servicios import disponibilidad as servicio_disponibilidad
from agenda.servicios import pesos as servicio_pesos
from agenda.servicios import profesionales as servicio_profesionales

router = APIRouter(prefix="/api/v1/publico", tags=["profesionales"])

#: Igual que en la disponibilidad del negocio: un mes cabe, y quien quiere más avanza semana a
#: semana. Un rango abierto en una ruta pública es una consulta cara regalada.
VENTANA_MAXIMA = timedelta(days=31)

#: Cuántos profesionales devuelve la búsqueda por página. Corto a propósito: esto se pinta en
#: un móvil de gama media con 3G.
POR_PAGINA = 20

#: Cuántas reseñas suyas se pintan en el perfil. El resto están en la ficha del salón.
RESENAS_EN_EL_PERFIL = 10


class RedesDelProfesional(BaseModel):
    """Las tres redes, con **el usuario y la dirección compuesta al servir**.

    La dirección no se guarda: se compone aquí a partir del usuario, así que siempre apunta al
    dominio correcto. Guardar la URL entera sería aceptar un enlace a cualquier sitio metido
    desde un formulario, y un perfil público es exactamente donde eso se aprovecha.
    """

    instagram: str | None = None
    instagram_url: str | None = None
    facebook: str | None = None
    facebook_url: str | None = None
    x: str | None = None
    x_url: str | None = None


class FotoDelProfesional(BaseModel):
    """Una foto suya. Si trae servicio, es un **trabajo**: «esto lo hizo esta persona»."""

    id: uuid.UUID
    url: str
    descripcion: str | None = None
    servicio_id: uuid.UUID | None = None
    servicio: str | None = None


class ProfesionalEnLista(BaseModel):
    """Lo que cabe en una tarjeta de equipo o de resultado de búsqueda.

    Sin teléfono y sin correo, como todo lo público. El nombre que sale es el **de trabajo**
    (`display_name`), que es el que la propia persona puso para que la llamen.
    """

    id: uuid.UUID
    slug: str | None = None
    nombre: str
    titular: str | None = Field(default=None, description="La descripción de una línea")
    foto: str | None = None
    anos_de_experiencia: int | None = None
    #: La bayesiana (REV-5), que es la que se enseña. `null` cuando todavía no tiene reseñas:
    #: enseñar la media global como si fuera suya sería inventarle una reputación.
    nota: float | None = None
    numero_resenas: int = 0
    servicios: list[uuid.UUID] = Field(default_factory=list)
    #: El salón donde trabaja. Hace falta en la búsqueda suelta y no estorba en la del equipo.
    negocio_slug: str | None = None
    negocio: str | None = None
    zona: str | None = None
    distancia_metros: int | None = None


class ProfesionalDelEquipo(ProfesionalEnLista):
    """En la lista del equipo de un salón sí se puede decir cuánto lleva atendido.

    Se calcula con una consulta agrupada sobre las citas **completadas** de ese salón. En la
    búsqueda suelta no viene, y no es un olvido: ahí los resultados son de salones distintos y
    contarlo costaría una consulta por negocio en la ruta más caliente del producto.
    """

    citas_atendidas: int = 0
    clientes_atendidos: int = 0


class PerfilDelProfesional(ProfesionalDelEquipo):
    """La ficha completa: quién es, qué hace, qué ha hecho y qué dicen de ella."""

    descripcion: str | None = Field(default=None, description="La bio larga")
    redes: RedesDelProfesional
    negocio_id: uuid.UUID
    zona_horaria: str
    direccion: str | None = None
    #: Sus servicios, con precio y duración, para poder elegir sin volver a la ficha del salón.
    catalogo: list[ServicioPublico] = Field(default_factory=list)
    #: Fotos sueltas: su galería.
    galeria: list[FotoDelProfesional] = Field(default_factory=list)
    #: Fotos atadas a un servicio: «esto lo hizo esta persona».
    trabajos: list[FotoDelProfesional] = Field(default_factory=list)
    resenas: list[ResenaPublica] = Field(default_factory=list)


# ── El equipo de un salón ─────────────────────────────────────────────────────────────────


@router.get(
    "/negocios/{slug}/profesionales",
    summary="El equipo visible de un salón (STF-2, encargo 2026-09-07 §3)",
)
async def equipo_del_negocio(slug: str, sesion: SesionPublica) -> list[ProfesionalDelEquipo]:
    """Quién trabaja aquí, con su titular, su nota y cuánto lleva atendido.

    Qué fichas salen **no lo decide esta función**: lo decide la política del rol público, que
    exige negocio publicado, ficha activa y visible en el marketplace. Ocultar a alguien del
    marketplace lo saca de aquí sin tocar ni una línea de código.
    """
    negocio = await _negocio_publicado(sesion, slug)
    equipo = await _equipo_visible(sesion, negocio.id)
    return await _pintar_equipo(sesion, negocio, equipo)


# ── El perfil ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/negocios/{slug}/profesionales/{profesional}",
    summary="Perfil público de un profesional (encargo 2026-09-07 §3)",
)
async def perfil_del_profesional(
    slug: str,
    profesional: str,
    sesion: SesionPublica,
) -> PerfilDelProfesional:
    """La ficha de una persona: descripción, fotos, servicios, reseñas, redes y su nota.

    `profesional` admite **el slug o el identificador**. El slug es lo que se comparte y lo que
    indexa Google; el identificador es la salida de emergencia para una ficha que todavía no
    tiene slug, para que un nulo en una columna no deje a nadie sin perfil.

    Cuánta gente ha atendido se cuenta **al leer** y no sale de ningún contador guardado: un
    contador se desincroniza el primer día que alguien toca una cita a mano en la base.
    """
    negocio = await _negocio_publicado(sesion, slug)
    ficha = await _ficha_visible(sesion, negocio.id, profesional)

    catalogo = await _servicios_de(sesion, negocio.id, [ficha.id])
    fotos = await _fotos_de(sesion, [ficha.id], {s.id: s.name for s in catalogo.get(ficha.id, [])})
    resenas = (
        (
            await sesion.execute(
                select(Review)
                .where(
                    Review.business_id == negocio.id,
                    Review.staff_id == ficha.id,
                    Review.status == "publicada",
                )
                .order_by(Review.created_at.desc())
                .limit(RESENAS_EN_EL_PERFIL)
            )
        )
        .scalars()
        .all()
    )

    base = (await _pintar_equipo(sesion, negocio, [ficha]))[0]
    ubicacion = (
        (await sesion.execute(select(Location).where(Location.business_id == negocio.id)))
        .scalars()
        .first()
    )

    servicios = catalogo.get(ficha.id, [])
    todas = fotos.get(ficha.id, [])

    return PerfilDelProfesional(
        **base.model_dump(),
        descripcion=ficha.bio,
        redes=_redes(ficha),
        negocio_id=negocio.id,
        zona_horaria=negocio.timezone,
        direccion=ubicacion.address_line if ubicacion else None,
        catalogo=[
            ServicioPublico(
                id=s.id,
                nombre=s.name,
                duracion_minutos=s.duration_min,
                precio_centavos=s.price_minor,
                tipo_de_precio=s.price_kind,
            )
            for s in servicios
        ],
        galeria=[f for f in todas if f.servicio_id is None],
        trabajos=[f for f in todas if f.servicio_id is not None],
        resenas=await pintar_publicas(sesion, list(resenas)),
    )


# ── Buscar personas, no salones ───────────────────────────────────────────────────────────


@router.get("/profesionales", summary="Buscar profesionales (encargo 2026-09-07 §3)")
async def buscar_profesionales(
    sesion: SesionPublica,
    texto: Annotated[
        str | None, Query(description="Nombre o titular: «Yaris», «colorista»")
    ] = None,
    servicio: Annotated[
        str | None, Query(description="Slug de una categoría global, por ejemplo «barberia»")
    ] = None,
    zona: Annotated[
        str | None, Query(description="Slug de zona, por ejemplo «el-cangrejo»")
    ] = None,
    negocio: Annotated[str | None, Query(description="Slug de un salón concreto")] = None,
    longitud: Annotated[float | None, Query(description="Desde dónde busca quien pregunta")] = None,
    latitud: Annotated[float | None, Query()] = None,
    radio_metros: Annotated[int, Query(ge=100, le=50_000)] = 10_000,
    orden: Annotated[str, Query(pattern="^(relevancia|nota|nombre|distancia)$")] = "relevancia",
    pagina: Annotated[int, Query(ge=1)] = 1,
) -> list[ProfesionalEnLista]:
    """Buscar **personas**, que es por donde entra quien ya sabe con quién quiere ir.

    Es la mitad que faltaba del encargo: quien busca «una barbería cerca» sigue usando
    `/publico/buscar`, y quien busca «Yaris» entra por aquí.

    **No trae cuántas clientas ha atendido**, y es deliberado: cada resultado puede ser de un
    salón distinto y ese número se cuenta sobre `bookings`, que no es público. Contarlo aquí
    costaría abrir una conexión por negocio en la consulta que más se va a repetir. Está en el
    perfil, que es donde alguien lo mira de verdad.
    """
    # La distancia se calcula en la base, como en la búsqueda de salones: es lo único que
    # depende de quién pregunta, y traérsela a Python obligaría a leer la geometría de cada fila.
    hay_punto = longitud is not None and latitud is not None
    punto = ST_SetSRID(func.ST_MakePoint(longitud, latitud), 4326) if hay_punto else None
    distancia = cast(func.ST_Distance(Location.geo, punto), Float) if hay_punto else literal(None)

    consulta = (
        select(StaffProfile, Business, Location, distancia.label("distancia"))
        .join(Business, Business.id == StaffProfile.business_id)
        .join(Location, Location.business_id == Business.id, isouter=True)
    )

    if hay_punto:
        # Se acota al radio, igual que la de salones: sin esto, «ordenar por distancia» devuelve
        # también a quien está en la otra punta del país, solo que al final de la lista.
        consulta = consulta.where(ST_DWithin(Location.geo, punto, radio_metros))

    if texto:
        patron = f"%{texto.strip()}%"
        consulta = consulta.where(
            or_(StaffProfile.display_name.ilike(patron), StaffProfile.headline.ilike(patron))
        )
    if negocio:
        consulta = consulta.where(Business.slug == negocio)
    if zona:
        # Por la rama entera, igual que la búsqueda de salones: quien pide «Bella Vista»
        # quiere también El Cangrejo y Obarrio, que están dentro (ADR-0005).
        consulta = consulta.where(
            Location.zone_id.in_(
                select(Zone.id).where(or_(Zone.slug == zona, Zone.path.like(f"%{zona}%")))
            )
        )
    if servicio:
        # Por la categoría **del servicio que presta**, no por la del salón: alguien puede
        # trabajar en un salón de uñas y hacer solo cejas, y quien busca cejas quiere a esa
        # persona y no a las otras cuatro del local.
        consulta = consulta.where(
            StaffProfile.id.in_(
                select(StaffService.staff_id)
                .join(Service, Service.id == StaffService.service_id)
                .where(
                    Service.active.is_(True),
                    Service.service_category_id.in_(
                        select(ServiceCategory.id).where(ServiceCategory.slug == servicio)
                    ),
                )
            )
        )

    if orden == "nombre":
        consulta = consulta.order_by(StaffProfile.display_name)
    elif orden == "distancia" and hay_punto:
        consulta = consulta.order_by(distancia)
    else:
        # Sin señal de calidad todavía: se ordena por salón y posición, que es el orden que el
        # propio salón puso en su equipo. Ordenar por nota se hace después, con los agregados
        # ya calculados, porque la nota no vive en una columna.
        consulta = consulta.order_by(Business.display_name, StaffProfile.position)

    filas = (
        await sesion.execute(consulta.offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA))
    ).all()
    if not filas:
        return []

    fichas = [fila[0] for fila in filas]
    negocios = {fila[1].id: fila[1] for fila in filas}
    ubicaciones = {fila[2].business_id: fila[2] for fila in filas if fila[2] is not None}
    distancias = {fila[0].id: fila[3] for fila in filas}

    pesos = await servicio_pesos.pesos_vigentes(sesion)
    notas = await servicio_profesionales.notas(sesion, [f.id for f in fichas], pesos)
    servicios = await _servicios_por_profesional(sesion, [f.id for f in fichas])

    salida = [
        ProfesionalEnLista(
            id=f.id,
            slug=f.slug,
            nombre=f.display_name,
            titular=f.headline,
            foto=url_de_media(f.photo_key),
            anos_de_experiencia=f.years_experience,
            nota=notas.get(f.id, servicio_profesionales.Nota()).puntuacion,
            numero_resenas=notas.get(f.id, servicio_profesionales.Nota()).numero,
            servicios=servicios.get(f.id, []),
            negocio_slug=negocios[f.business_id].slug,
            negocio=negocios[f.business_id].display_name,
            zona=(
                ubicaciones[f.business_id].address_line if f.business_id in ubicaciones else None
            ),
            distancia_metros=(
                round(distancias[f.id]) if distancias.get(f.id) is not None else None
            ),
        )
        for f in fichas
    ]

    if orden == "distancia" and not hay_punto:
        # Pedir «por distancia» sin decir desde dónde no puede ordenar por distancia. Se deja el
        # orden que ya traía en vez de fingir uno: una lista ordenada al azar y presentada como
        # ordenada por cercanía manda a la gente al otro lado de la ciudad.
        pass
    elif orden == "nota":
        # Quien no tiene nota va al final, no al principio: un `None` que ordena primero
        # pondría arriba justo a quien menos se sabe de él.
        salida.sort(key=lambda p: (p.nota is None, -(p.nota or 0), p.nombre))
    return salida


# ── Sus huecos, sin pasar por la ficha del salón ──────────────────────────────────────────


@router.get(
    "/profesionales/{profesional_id}/disponibilidad",
    summary="Huecos de un profesional concreto (AGD-1, encargo 2026-09-07 §3)",
)
async def disponibilidad_del_profesional(
    profesional_id: uuid.UUID,
    sesion: SesionPublica,
    servicios: Annotated[list[uuid.UUID], Query(description="En el orden en que se encadenan")],
    desde: Annotated[datetime, Query()],
    hasta: Annotated[datetime, Query()],
) -> RespuestaDisponibilidad:
    """El tercer paso del camino nuevo: profesional → servicio suyo → **hora**.

    Es la misma respuesta que `/publico/negocios/{slug}/disponibilidad?profesional=…` y sale
    del **mismo motor**; lo que cambia es que aquí no hace falta saber en qué salón trabaja,
    porque eso lo resuelve el servidor a partir de la ficha. Quien entra por la persona no
    tiene por qué haber visto nunca el nombre del local.
    """
    ficha = (
        await sesion.execute(select(StaffProfile).where(StaffProfile.id == profesional_id))
    ).scalar_one_or_none()
    if ficha is None:
        raise NoExiste("Ese profesional no está publicado.")

    negocio = await sesion.get(Business, ficha.business_id)
    if negocio is None:
        raise NoExiste("Ese profesional no está publicado.")

    if hasta - desde > VENTANA_MAXIMA:
        hasta = desde + VENTANA_MAXIMA

    # Horarios, asignaciones y ocupación **no son públicos**, y está bien que no lo sean. El
    # cálculo se hace con una sesión fijada a este negocio concreto, igual que la
    # disponibilidad de la ficha del salón: desde ahí no existe ningún otro negocio.
    async with sesion_de_negocio(str(negocio.id)) as sesion_negocio:
        resultado = await servicio_disponibilidad.calcular(
            sesion_negocio,
            negocio_id=negocio.id,
            servicios_ids=list(servicios),
            desde=desde,
            hasta=hasta,
            ahora=datetime.now(UTC),
            profesional_id=ficha.id,
        )

    return RespuestaDisponibilidad(
        zona=resultado.zona,
        duracion_minutos=int(resultado.duracion_total.total_seconds() // 60),
        slots=[
            SlotPublico(
                inicio=slot.inicio,
                fin=slot.fin,
                profesional_id=uuid.UUID(slot.profesional_id) if slot.profesional_id else None,
            )
            for slot in resultado.slots
        ],
    )


# ── Piezas compartidas ────────────────────────────────────────────────────────────────────


async def _negocio_publicado(sesion: AsyncSession, slug: str) -> Business:
    negocio = (
        await sesion.execute(select(Business).where(Business.slug == slug))
    ).scalar_one_or_none()
    if negocio is None:
        raise NoExiste("Ese negocio no está publicado.")
    return negocio


async def _equipo_visible(sesion: AsyncSession, negocio_id: uuid.UUID) -> list[StaffProfile]:
    return list(
        (
            await sesion.execute(
                select(StaffProfile)
                .where(StaffProfile.business_id == negocio_id)
                .order_by(StaffProfile.position, StaffProfile.display_name)
            )
        )
        .scalars()
        .all()
    )


async def _ficha_visible(
    sesion: AsyncSession, negocio_id: uuid.UUID, referencia: str
) -> StaffProfile:
    """Por slug o por identificador. **El mismo 404 en los dos casos** y en el de «no visible».

    Distinguir «no existe» de «existe pero está oculta» convertiría el perfil en un detector
    de fichas ocultas, que es información del salón y no de quien pregunta.
    """
    consulta = select(StaffProfile).where(StaffProfile.business_id == negocio_id)
    try:
        identificador = uuid.UUID(referencia)
    except ValueError:
        consulta = consulta.where(StaffProfile.slug == referencia)
    else:
        consulta = consulta.where(StaffProfile.id == identificador)

    ficha = (await sesion.execute(consulta)).scalar_one_or_none()
    if ficha is None:
        raise NoExiste("Ese profesional no está publicado.")
    return ficha


async def _pintar_equipo(
    sesion: AsyncSession, negocio: Business, equipo: list[StaffProfile]
) -> list[ProfesionalDelEquipo]:
    """Serializador de la lista, con la nota y lo atendido resueltos en dos consultas."""
    if not equipo:
        return []
    ids = [p.id for p in equipo]

    pesos = await servicio_pesos.pesos_vigentes(sesion)
    notas = await servicio_profesionales.notas(sesion, ids, pesos)
    servicios = await _servicios_por_profesional(sesion, ids)

    # `bookings` no la ve el rol público, así que lo atendido se cuenta con una sesión fijada
    # a este negocio — el mismo movimiento que hace la disponibilidad, y por el mismo motivo:
    # abrirle las reservas al rol del marketplace sería una puerta que después no se cierra.
    async with sesion_de_negocio(str(negocio.id)) as sesion_negocio:
        atendidos = await servicio_profesionales.atendidos(sesion_negocio, negocio.id, ids)

    vacio_nota = servicio_profesionales.Nota()
    vacio_atendidos = servicio_profesionales.Atendidos()

    return [
        ProfesionalDelEquipo(
            id=p.id,
            slug=p.slug,
            nombre=p.display_name,
            titular=p.headline,
            foto=url_de_media(p.photo_key),
            anos_de_experiencia=p.years_experience,
            nota=notas.get(p.id, vacio_nota).puntuacion,
            numero_resenas=notas.get(p.id, vacio_nota).numero,
            servicios=servicios.get(p.id, []),
            negocio_slug=negocio.slug,
            negocio=negocio.display_name,
            citas_atendidas=atendidos.get(p.id, vacio_atendidos).citas,
            clientes_atendidos=atendidos.get(p.id, vacio_atendidos).clientes,
        )
        for p in equipo
    ]


def _redes(ficha: StaffProfile) -> RedesDelProfesional:
    return RedesDelProfesional(
        instagram=ficha.instagram,
        instagram_url=url_de_red("instagram", ficha.instagram),
        facebook=ficha.facebook,
        facebook_url=url_de_red("facebook", ficha.facebook),
        x=ficha.x,
        x_url=url_de_red("x", ficha.x),
    )


async def _servicios_por_profesional(
    sesion: AsyncSession, staff_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[uuid.UUID]]:
    if not staff_ids:
        return {}
    salida: dict[uuid.UUID, list[uuid.UUID]] = {}
    for staff_id, servicio_id in (
        await sesion.execute(
            select(StaffService.staff_id, StaffService.service_id).where(
                StaffService.staff_id.in_(staff_ids)
            )
        )
    ).all():
        salida.setdefault(staff_id, []).append(servicio_id)
    return salida


async def _servicios_de(
    sesion: AsyncSession, negocio_id: uuid.UUID, staff_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[Service]]:
    """Los servicios **activos** que presta cada quien, con su ficha entera."""
    if not staff_ids:
        return {}
    salida: dict[uuid.UUID, list[Service]] = {}
    for staff_id, servicio in (
        await sesion.execute(
            select(StaffService.staff_id, Service)
            .join(Service, Service.id == StaffService.service_id)
            .where(
                StaffService.staff_id.in_(staff_ids),
                Service.business_id == negocio_id,
                Service.active.is_(True),
            )
            .order_by(Service.position)
        )
    ).all():
        salida.setdefault(staff_id, []).append(servicio)
    return salida


async def _fotos_de(
    sesion: AsyncSession, staff_ids: list[uuid.UUID], nombres: dict[uuid.UUID, str]
) -> dict[uuid.UUID, list[FotoDelProfesional]]:
    """Galería y trabajos en una sola consulta. Solo las aprobadas — lo exige la política."""
    if not staff_ids:
        return {}
    salida: dict[uuid.UUID, list[FotoDelProfesional]] = {}
    for foto in (
        (
            await sesion.execute(
                select(StaffMedia)
                .where(StaffMedia.staff_id.in_(staff_ids))
                .order_by(StaffMedia.position, StaffMedia.created_at)
            )
        )
        .scalars()
        .all()
    ):
        url = url_de_media(foto.storage_key)
        if url is None:
            continue
        salida.setdefault(foto.staff_id, []).append(
            FotoDelProfesional(
                id=foto.id,
                url=url,
                descripcion=foto.alt_text,
                servicio_id=foto.service_id,
                servicio=nombres.get(foto.service_id) if foto.service_id else None,
            )
        )
    return salida
