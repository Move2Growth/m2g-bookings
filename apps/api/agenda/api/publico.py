"""Rutas públicas: lo que puede ver cualquiera, incluido el rastreador de Google.

**Nada de lo que sale por aquí lleva teléfonos, correos ni datos de clientes.** No es una
recomendación: los listados públicos son lo que alguien raspa en una tarde para montarse una
base de negocios, y el brief lo recoge como riesgo. Por eso los serializadores de este módulo
son propios y no se comparten con los de negocio (ADR-0012).

Y por eso también estas rutas **nacen con límite de peticiones**: la disponibilidad es una
consulta cara y pública. Dejarla sin límite «hasta el sprint de endurecimiento» es abrir la
puerta y apuntar en una lista que hay que cerrarla.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from agenda.api.comunes import url_de_media
from agenda.api.dependencias import SesionPublica
from agenda.bd import sesion_de_negocio
from agenda.errores import DatoInvalido, NegocioNoPublicado, NoExiste
from agenda.modelos.catalogo import Service
from agenda.modelos.equipo import StaffProfile
from agenda.modelos.marketplace import ListingClickDaily
from agenda.modelos.negocio import (
    AttributeValue,
    Business,
    BusinessAttribute,
    BusinessHours,
    BusinessMedia,
    Location,
)
from agenda.modelos.reviews import BusinessRatingStats
from agenda.servicios import busqueda as servicio_busqueda
from agenda.servicios import disponibilidad as servicio_disponibilidad
from agenda.servicios import tarjetas as servicio_tarjetas

router = APIRouter(prefix="/api/v1/publico", tags=["público"])

#: Cuánto se puede pedir de una vez. Un mes de agenda de un salón entero es mucha aritmética
#: para una consulta pública, y quien de verdad quiere ver más avanza de semana en semana.
VENTANA_MAXIMA = timedelta(days=31)


class SlotPublico(BaseModel):
    """Un hueco ofrecible. **No reserva nada**: mirar no aparta."""

    inicio: datetime
    fin: datetime
    profesional_id: uuid.UUID | None = None


class RespuestaDisponibilidad(BaseModel):
    zona: str = Field(description="Zona horaria IANA del negocio, para pintar la hora local")
    duracion_minutos: int
    slots: list[SlotPublico]


class ServicioPublico(BaseModel):
    id: uuid.UUID
    nombre: str
    duracion_minutos: int
    #: En centavos, como se guarda. Formatear es cosa de quien pinta, no de la API.
    precio_centavos: int | None
    tipo_de_precio: str = Field(description="fijo | desde | consultar")


class ProfesionalPublico(BaseModel):
    id: uuid.UUID
    nombre: str


class NegocioEnLista(BaseModel):
    """Lo que se enseña en un listado. **Sin teléfono**: el número no viaja en claro."""

    slug: str
    nombre: str
    zona: str | None = None
    direccion: str | None = None
    servicios_desde_centavos: int | None = None


class TramoPublico(BaseModel):
    """Un tramo de apertura, en hora local del negocio. Para pintar «hoy abre de 9 a 19»."""

    dia: int = Field(ge=0, le=6, description="0 = lunes … 6 = domingo")
    abre: time
    cierra: time


class PerfilPublico(NegocioEnLista):
    id: uuid.UUID
    zona_horaria: str
    descripcion: str | None = None
    #: Todas las fotos aprobadas, **la portada primero**.
    fotos: list[str] = Field(default_factory=list)
    foto_portada: str | None = None
    rating: float | None = Field(
        default=None, description="El bayesiano (REV-5), que es el que se enseña"
    )
    numero_reviews: int = 0
    #: Nombres de los atributos filtrables que declaró el negocio (NEG-2): «atiende cabello
    #: afro», «estacionamiento», «acepta Yappy».
    atributos: list[str] = Field(default_factory=list)
    horario: list[TramoPublico] = Field(default_factory=list)
    abierto_ahora: bool | None = None
    #: **Nunca el número.** Solo si hay canal, para pintar el botón que salta al servidor.
    tiene_whatsapp: bool = False
    servicios: list[ServicioPublico]
    equipo: list[ProfesionalPublico]


class ResultadoDeBusqueda(BaseModel):
    #: Hace falta además del slug: los favoritos se guardan por identificador, y el slug puede
    #: cambiar (por eso existe `slug_redirects`). Guardar por slug sería guardar una URL.
    negocio_id: uuid.UUID
    slug: str
    nombre: str
    direccion: str | None
    zona: str | None
    distancia_metros: int | None
    rating: float | None
    #: El más barato de sus servicios activos. Sin esto hay que entrar en cada ficha para
    #: descartarla, y eso es exactamente lo que devuelve a la gente al WhatsApp.
    servicios_desde_centavos: int | None = None
    foto_portada: str | None = None
    numero_reviews: int = 0
    categorias: list[str] = Field(default_factory=list)
    #: `null` cuando el negocio **no tiene horario cargado**, que no es lo mismo que cerrado.
    abierto_ahora: bool | None = None
    #: Primera hora libre de hoy. Solo viene cuando se filtra por disponibilidad o se pide con
    #: `con_proxima_hora`: cuesta una consulta de agenda por negocio.
    proxima_hora: datetime | None = None
    patrocinado: bool = Field(
        default=False,
        description="Si es un resultado pagado. Va etiquetado en pantalla, sin excepción",
    )


@router.get("/buscar", summary="Búsqueda del marketplace (MKT-1, MKT-2, MKT-3, MKT-4)")
async def buscar(
    sesion: SesionPublica,
    texto: Annotated[str | None, Query(description="Nombre del negocio o del servicio")] = None,
    categoria: Annotated[str | None, Query()] = None,
    zona: Annotated[
        str | None, Query(description="Slug de zona, por ejemplo «el-cangrejo»")
    ] = None,
    longitud: Annotated[float | None, Query()] = None,
    latitud: Annotated[float | None, Query()] = None,
    radio_metros: Annotated[int, Query(ge=200, le=50_000)] = 10_000,
    precio_min: Annotated[
        int | None, Query(ge=0, description="En centavos. Filtra por ALGÚN servicio en rango")
    ] = None,
    precio_max: Annotated[int | None, Query(ge=0, description="En centavos")] = None,
    rating_min: Annotated[
        float | None, Query(ge=0, le=5, description="Sobre el rating bayesiano, no la media")
    ] = None,
    disponibilidad: Annotated[
        str | None,
        Query(
            pattern="^(ahora|hoy|fecha)$",
            description="Disponibilidad real, calculada con el motor de reservas",
        ),
    ] = None,
    dia: Annotated[date | None, Query(description="Obligatorio con disponibilidad=fecha")] = None,
    abierto_ahora: Annotated[bool, Query()] = False,
    orden: Annotated[
        str, Query(pattern="^(relevancia|distancia|precio|rating|nuevos)$")
    ] = "relevancia",
    con_proxima_hora: Annotated[
        bool,
        Query(
            description=(
                "Calcula la primera hora libre de hoy de cada resultado. Cuesta una consulta "
                "de agenda por negocio: se pide cuando la pantalla lo va a pintar"
            )
        ),
    ] = False,
    pagina: Annotated[int, Query(ge=1)] = 1,
) -> list[ResultadoDeBusqueda]:
    """Busca por texto, categoría, zona o cercanía, filtra y ordena.

    Buscar «por zona» no es lo mismo que buscar «cerca de mí»: la zona es un sitio con nombre
    que la gente escribe en Google, y el radio es el gesto de quien tiene el GPS encendido. Se
    puede combinar, y quien pide «Bella Vista» ve también El Cangrejo y Obarrio, que están
    dentro.

    **El filtro de disponibilidad usa el mismo motor que la reserva**, no una copia (MKT-2):
    prometer horas libres con una fórmula distinta a la de reservar es mandar a la gente a un
    hueco que no existe. Es también el filtro más caro, así que se aplica al final y solo sobre
    los candidatos que ya pasaron todo lo demás.

    Los patrocinados se intercalan aquí cuando existan (Fase 4): **se insertan entre los
    orgánicos, nunca en su lugar**, y siempre etiquetados.
    """
    if disponibilidad == "fecha" and dia is None:
        # `DATO_INVALIDO` y no «no existe»: lo que falta es un parámetro de la petición, no un
        # recurso. El código del error lo consume el cliente y tiene que decir la verdad.
        raise DatoInvalido("Para filtrar por una fecha concreta hay que decir cuál, en «dia».")

    resultados = await servicio_busqueda.buscar(
        sesion,
        texto=texto,
        categoria=categoria,
        zona=zona,
        longitud=longitud,
        latitud=latitud,
        radio_metros=radio_metros,
        precio_min=precio_min,
        precio_max=precio_max,
        rating_min=rating_min,
        disponibilidad=disponibilidad,
        dia=dia,
        abierto_ahora=abierto_ahora,
        orden=orden,
        con_proxima_hora=con_proxima_hora,
        pagina=pagina,
    )

    return [
        ResultadoDeBusqueda(
            negocio_id=r.negocio_id,
            slug=r.slug,
            nombre=r.nombre,
            direccion=r.direccion,
            zona=r.zona,
            distancia_metros=int(r.distancia_metros) if r.distancia_metros is not None else None,
            rating=r.rating,
            servicios_desde_centavos=r.desde_centavos,
            foto_portada=r.foto_portada,
            numero_reviews=r.numero_reviews,
            categorias=r.categorias or [],
            abierto_ahora=r.abierto_ahora,
            proxima_hora=r.proxima_hora,
            patrocinado=r.patrocinado,
        )
        for r in resultados
    ]


@router.get("/negocios", summary="Negocios publicados (MKT-1)")
async def listar_negocios(sesion: SesionPublica) -> list[NegocioEnLista]:
    """El listado del marketplace.

    Solo salen los **publicados**, y eso no lo decide esta función: lo decide la política de
    seguridad por fila del rol público. Un despiste aquí no puede sacar a la luz un negocio en
    borrador, porque desde este rol los borradores no existen.
    """
    negocios = (
        (await sesion.execute(select(Business).order_by(Business.display_name))).scalars().all()
    )

    salida: list[NegocioEnLista] = []
    for negocio in negocios:
        ubicacion = (
            (await sesion.execute(select(Location).where(Location.business_id == negocio.id)))
            .scalars()
            .first()
        )
        precio = (
            await sesion.execute(
                select(func.min(Service.price_minor)).where(
                    Service.business_id == negocio.id,
                    Service.active.is_(True),
                    Service.price_minor.is_not(None),
                )
            )
        ).scalar_one_or_none()

        salida.append(
            NegocioEnLista(
                slug=negocio.slug,
                nombre=negocio.display_name,
                direccion=ubicacion.address_line if ubicacion else None,
                servicios_desde_centavos=precio,
            )
        )
    return salida


@router.get("/negocios/{slug}", summary="Perfil público del negocio (NEG-1, NEG-3)")
async def perfil(slug: str, sesion: SesionPublica) -> PerfilPublico:
    """El perfil que indexa Google y desde el que se reserva.

    Lleva servicios con precio y duración, equipo visible, fotos, horario, atributos y el
    rating agregado. **No lleva el teléfono**: el click-to-chat se resuelve en servidor, porque
    si el número viajara aquí, alguien se lleva la base entera de negocios en una tarde.

    Todo sale con el rol del marketplace, que **no tiene permiso** sobre reservas ni sobre
    fichas de cliente: aunque este código quisiera, no podría filtrar un dato de una persona.
    """
    negocio = (
        await sesion.execute(select(Business).where(Business.slug == slug))
    ).scalar_one_or_none()
    if negocio is None:
        raise NegocioNoPublicado()

    ubicacion = (
        (await sesion.execute(select(Location).where(Location.business_id == negocio.id)))
        .scalars()
        .first()
    )
    servicios = (
        (
            await sesion.execute(
                select(Service)
                .where(Service.business_id == negocio.id, Service.active.is_(True))
                .order_by(Service.position)
            )
        )
        .scalars()
        .all()
    )
    equipo = (
        (
            await sesion.execute(
                select(StaffProfile)
                .where(StaffProfile.business_id == negocio.id, StaffProfile.active.is_(True))
                .order_by(StaffProfile.position)
            )
        )
        .scalars()
        .all()
    )
    fotos = (
        (
            await sesion.execute(
                select(BusinessMedia)
                .where(
                    BusinessMedia.business_id == negocio.id,
                    BusinessMedia.moderation_status == "aprobada",
                )
                # La portada primero: `kind` ordena al revés alfabéticamente, de ahí el `desc`.
                .order_by(BusinessMedia.kind.desc(), BusinessMedia.position, BusinessMedia.id)
            )
        )
        .scalars()
        .all()
    )
    tramos = (
        (
            await sesion.execute(
                select(BusinessHours)
                .where(BusinessHours.business_id == negocio.id)
                .order_by(BusinessHours.weekday, BusinessHours.opens_at)
            )
        )
        .scalars()
        .all()
    )
    atributos = list(
        (
            await sesion.execute(
                select(AttributeValue.name)
                .join(
                    BusinessAttribute,
                    BusinessAttribute.attribute_value_id == AttributeValue.id,
                )
                .where(BusinessAttribute.business_id == negocio.id)
                .order_by(AttributeValue.position, AttributeValue.name)
            )
        )
        .scalars()
        .all()
    )
    stats = await sesion.get(BusinessRatingStats, negocio.id)

    urls = [u for f in fotos if (u := url_de_media(f.storage_key)) is not None]

    return PerfilPublico(
        id=negocio.id,
        slug=negocio.slug,
        nombre=negocio.display_name,
        descripcion=negocio.description,
        zona_horaria=negocio.timezone,
        direccion=ubicacion.address_line if ubicacion else None,
        fotos=urls,
        foto_portada=urls[0] if urls else None,
        rating=(
            float(stats.rating_bayesian) if stats and stats.rating_bayesian is not None else None
        ),
        numero_reviews=stats.reviews_count if stats else 0,
        atributos=atributos,
        horario=[TramoPublico(dia=t.weekday, abre=t.opens_at, cierra=t.closes_at) for t in tramos],
        abierto_ahora=servicio_tarjetas.esta_abierto(
            [(t.weekday, t.opens_at, t.closes_at) for t in tramos], negocio.timezone
        ),
        # Solo **si lo hay**. El número no viaja ni aquí ni en ningún otro sitio público.
        tiene_whatsapp=bool(negocio.whatsapp_phone_e164),
        servicios_desde_centavos=min(
            (s.price_minor for s in servicios if s.price_minor is not None), default=None
        ),
        servicios=[
            ServicioPublico(
                id=s.id,
                nombre=s.name,
                duracion_minutos=s.duration_min,
                precio_centavos=s.price_minor,
                tipo_de_precio=s.price_kind,
            )
            for s in servicios
        ],
        equipo=[ProfesionalPublico(id=p.id, nombre=p.display_name) for p in equipo],
    )


@router.get(
    "/negocios/{slug}/chat",
    summary="Salto a WhatsApp resuelto en servidor (NEG-1, MKT-8)",
    response_class=RedirectResponse,
    status_code=307,
)
async def click_to_chat(slug: str, sesion: SesionPublica) -> RedirectResponse:
    """Registra el clic y redirige. **El número nunca llega al navegador.**

    Es la garantía nº 3 del proyecto hecha código: si el teléfono viajara en el perfil, un
    script se lleva la base entera de negocios de Panamá en una tarde. Aquí el cliente pide una
    URL de nuestro dominio, el servidor apunta el clic y responde con la redirección; el número
    solo existe entre la base de datos y esta función.

    El clic se cuenta **agregado por día** (MKT-8): 5.000 negocios generando una fila por
    evento no aporta nada que la serie no cuente mejor.
    """
    negocio = (
        await sesion.execute(select(Business).where(Business.slug == slug))
    ).scalar_one_or_none()
    if negocio is None:
        raise NegocioNoPublicado()
    if not negocio.whatsapp_phone_e164:
        raise NoExiste("Ese negocio no tiene WhatsApp configurado.")

    # El contador vive en una tabla del negocio, así que hay que declararlo. `ON CONFLICT DO
    # UPDATE` suma sin leer antes, que es atómico y aguanta dos clics a la vez.
    async with sesion_de_negocio(str(negocio.id)) as sesion_negocio:
        await sesion_negocio.execute(
            pg_insert(ListingClickDaily.__table__)
            .values(
                business_id=negocio.id,
                day=datetime.now(UTC).date(),
                surface="web",
                kind="whatsapp",
                count=1,
            )
            # El conflicto se declara por **columnas** y no por nombre de restricción: el
            # único es un índice `NULLS NOT DISTINCT` creado a mano en la migración, y
            # PostgreSQL no acepta `ON CONSTRAINT` para un índice único que no es restricción.
            .on_conflict_do_update(
                index_elements=[
                    "business_id",
                    "day",
                    "surface",
                    "kind",
                    "zone_id",
                    "service_category_id",
                ],
                set_={"count": ListingClickDaily.__table__.c.count + 1},
            )
        )

    numero = negocio.whatsapp_phone_e164.lstrip("+")
    return RedirectResponse(url=f"https://wa.me/{numero}", status_code=307)


@router.get(
    "/negocios/{slug}/disponibilidad",
    summary="Huecos libres de un negocio (AGD-1, STF-5)",
    response_model=RespuestaDisponibilidad,
)
async def disponibilidad(
    slug: str,
    sesion: SesionPublica,
    servicios: Annotated[list[uuid.UUID], Query(description="En el orden en que se encadenan")],
    desde: Annotated[datetime, Query()],
    hasta: Annotated[datetime, Query()],
    profesional: Annotated[uuid.UUID | None, Query()] = None,
) -> RespuestaDisponibilidad:
    """Devuelve los huecos de un rango. Una petición por rango, **no una por día**.

    Siete peticiones para pintar una semana es lo que hunde la experiencia en 3G, que es la red
    en la que vive este producto.
    """
    negocio = (
        await sesion.execute(
            select(Business).where(Business.slug == slug, Business.status == "publicado")
        )
    ).scalar_one_or_none()
    if negocio is None:
        raise NegocioNoPublicado()

    if hasta - desde > VENTANA_MAXIMA:
        hasta = desde + VENTANA_MAXIMA

    # El cálculo necesita horarios, asignaciones de servicios y ocupación, y **nada de eso es
    # público**: el rol del marketplace no los ve, y está bien que no los vea. Así que el hueco
    # se calcula con una sesión **fijada a este negocio concreto**, el que la persona está
    # mirando. La seguridad por fila hace el resto: desde esa sesión no existe ningún otro
    # negocio, aunque el código de esta función quisiera.
    #
    # La alternativa —abrirle esas tablas al rol público— dejaría los horarios y la ocupación
    # de los 5.000 negocios accesibles desde cualquier consulta pública mal escrita, y eso sí
    # es una puerta que luego no se cierra.
    async with sesion_de_negocio(str(negocio.id)) as sesion_negocio:
        resultado = await servicio_disponibilidad.calcular(
            sesion_negocio,
            negocio_id=negocio.id,
            servicios_ids=list(servicios),
            desde=desde,
            hasta=hasta,
            ahora=datetime.now(UTC),
            profesional_id=profesional,
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
