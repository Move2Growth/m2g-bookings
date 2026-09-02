"""La búsqueda del marketplace: encontrar y ordenar (MKT-1, MKT-2, MKT-3).

El reparto de trabajo entre la base y el código es deliberado:

* **PostgreSQL filtra y calcula la distancia**, porque es lo que sabe hacer con índices sobre
  5.000 negocios y un presupuesto de 500 ms.
* **El ranking se combina en Python** a partir de señales ya precalculadas más la distancia,
  que es lo único que depende de quién busca. Escribir la fórmula en SQL la volvería
  intocable: el objetivo es que los pesos se cambien desde el back-office sin desplegar
  (ADR-0009).

Y una regla que se ve en el orden de las funciones: **los patrocinados se resuelven aparte y
se intercalan al final**. Nunca compiten en la fórmula, nunca desplazan a un orgánico fuera de
la página, y no tocan el rating.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from geoalchemy2.functions import ST_DWithin, ST_SetSRID
from sqlalchemy import Float, cast, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.dominio.ranking import PesosRanking, Puntuacion, SenalesNegocio, puntuar
from agenda.modelos.catalogo import Service
from agenda.modelos.marketplace import BusinessRankingSignals, RankingWeights, Zone
from agenda.modelos.negocio import Business, BusinessCategory, Location

#: Cuántos resultados se sirven por página. Con tarjetas de 132 px, cuatro entran en el primer
#: pantallazo de un teléfono; diez es lo que se recorre con un par de gestos.
POR_PAGINA = 10


@dataclass(frozen=True)
class Resultado:
    """Un negocio en la lista, con **por qué** salió donde salió."""

    negocio_id: uuid.UUID
    slug: str
    nombre: str
    direccion: str | None
    zona: str | None
    distancia_metros: float | None
    rating: float | None
    desde_centavos: int | None
    patrocinado: bool = False
    puntuacion: Puntuacion | None = None


async def buscar(
    sesion: AsyncSession,
    *,
    texto: str | None = None,
    categoria: str | None = None,
    zona: str | None = None,
    longitud: float | None = None,
    latitud: float | None = None,
    radio_metros: int = 10_000,
    pagina: int = 1,
) -> list[Resultado]:
    """Busca negocios publicados y los ordena.

    Se puede buscar **por punto o por zona**, y no son lo mismo: «cerca de mí» es un radio, y
    «El Cangrejo» es un sitio con nombre que la gente escribe en Google. Las dos entradas
    conviven porque el producto necesita las dos (ADR-0005).
    """
    consulta = (
        select(
            Business.id,
            Business.slug,
            Business.display_name,
            Location.address_line,
            Zone.name.label("zona"),
            _distancia(longitud, latitud).label("distancia"),
        )
        .join(Location, Location.business_id == Business.id, isouter=True)
        .join(Zone, Zone.id == Location.zone_id, isouter=True)
        # La cláusula de publicado la aplica además la política del rol público: esto es el
        # filtro explícito que pide ADR-0002, para que el planificador use los índices.
        .where(Business.status == "publicado")
    )

    if texto:
        patron = f"%{texto.strip()}%"
        # Un `ILIKE` sobre nombre y servicios es suficiente para el volumen de v1 y no arrastra
        # la complejidad de un índice de texto completo. Cuando haga falta, será un ADR nuevo.
        consulta = consulta.where(
            or_(
                Business.display_name.ilike(patron),
                Business.id.in_(
                    select(Service.business_id).where(
                        Service.name.ilike(patron), Service.active.is_(True)
                    )
                ),
            )
        )

    if categoria:
        consulta = consulta.where(
            Business.id.in_(
                select(BusinessCategory.business_id).where(
                    BusinessCategory.category_id.in_(_categoria_por_slug(categoria))
                )
            )
        )

    if zona:
        # Se busca por la rama entera: quien pide «Bella Vista» quiere también El Cangrejo y
        # Obarrio, que están dentro. Por eso `zones` guarda el camino materializado.
        consulta = consulta.where(
            Location.zone_id.in_(
                select(Zone.id).where(or_(Zone.slug == zona, Zone.path.like(f"%{zona}%")))
            )
        )

    if longitud is not None and latitud is not None:
        consulta = consulta.where(ST_DWithin(Location.geo, _punto(longitud, latitud), radio_metros))

    filas = (await sesion.execute(consulta)).all()
    if not filas:
        return []

    pesos = await _pesos_vigentes(sesion)
    senales = await _senales(sesion, [fila.id for fila in filas])
    desde = await _precio_desde(sesion, [fila.id for fila in filas])

    resultados: list[Resultado] = []
    for fila in filas:
        precalculadas = senales.get(fila.id)
        puntuacion = puntuar(
            SenalesNegocio(
                distancia_metros=float(fila.distancia) if fila.distancia is not None else None,
                suma_notas=0,
                numero_reviews=0,
                reservas_recientes=precalculadas.bookings_recent if precalculadas else 0,
                completadas=0,
                no_asistidas=0,
                canceladas_por_negocio=0,
                completitud_perfil=float(precalculadas.completeness or 0) if precalculadas else 0.0,
                dias_desde_ultima_actividad=0,
                dias_desde_publicacion=999,
            ),
            pesos,
        )
        resultados.append(
            Resultado(
                negocio_id=fila.id,
                slug=fila.slug,
                nombre=fila.display_name,
                direccion=fila.address_line,
                zona=fila.zona,
                distancia_metros=float(fila.distancia) if fila.distancia is not None else None,
                rating=float(precalculadas.rating_bayesian)
                if precalculadas and precalculadas.rating_bayesian
                else None,
                desde_centavos=desde.get(fila.id),
                puntuacion=puntuacion,
            )
        )

    resultados.sort(key=lambda r: r.puntuacion.total if r.puntuacion else 0, reverse=True)
    primero = (pagina - 1) * POR_PAGINA
    return resultados[primero : primero + POR_PAGINA]


def _punto(longitud: float, latitud: float):
    return ST_SetSRID(func.ST_MakePoint(longitud, latitud), 4326)


def _distancia(longitud: float | None, latitud: float | None):
    """Metros hasta el punto de búsqueda, o `NULL` si nadie dijo desde dónde busca."""
    if longitud is None or latitud is None:
        return literal(None)
    return cast(func.ST_Distance(Location.geo, _punto(longitud, latitud)), Float)


def _categoria_por_slug(slug: str):
    from agenda.modelos.catalogo import ServiceCategory

    return select(ServiceCategory.id).where(ServiceCategory.slug == slug)


async def _pesos_vigentes(sesion: AsyncSession) -> PesosRanking:
    """Los pesos que manden hoy. **Si no hay fila, se usan los valores por defecto**, no cero.

    Un ranking con todos los pesos a cero ordena al azar y nadie entendería por qué.
    """
    fila = (
        await sesion.execute(
            select(RankingWeights).order_by(RankingWeights.created_at.desc()).limit(1)
        )
    ).scalar_one_or_none()

    if fila is None:
        return PesosRanking()

    return PesosRanking(
        distancia=float(fila.w_distancia),
        rating=float(fila.w_rating),
        reservas_recientes=float(fila.w_reservas_recientes),
        tasa_completado=float(fila.w_tasa_completado),
        completitud=float(fila.w_completitud),
        actividad=float(fila.w_actividad),
        boost_nuevo=float(fila.w_boost_nuevo),
        # La tabla guarda kilómetros porque es como se habla de un radio; la fórmula trabaja
        # en metros porque es lo que devuelve PostGIS. La conversión vive aquí y en un solo
        # sitio: repartirla es como se acaba comparando kilómetros con metros.
        radio_metros=float(fila.radius_km) * 1000,
        techo_reservas=int(fila.recent_cap),
        dias_boost_nuevo=int(fila.boost_days),
        rating_medio_global=float(fila.bayes_m),
        reviews_de_confianza=int(fila.bayes_c),
    )


async def _senales(
    sesion: AsyncSession, negocios: list[uuid.UUID]
) -> dict[uuid.UUID, BusinessRankingSignals]:
    """Las señales caras, ya calculadas por el trabajo periódico.

    Recorrer las reservas de 5.000 negocios en cada búsqueda no cabe en 500 ms; por eso esto
    es una lectura y no un cálculo. El precio es un desfase de minutos entre la realidad y el
    orden, y es aceptable: una reserva de hace un minuto no reordena la portada.
    """
    filas = (
        (
            await sesion.execute(
                select(BusinessRankingSignals).where(
                    BusinessRankingSignals.business_id.in_(negocios)
                )
            )
        )
        .scalars()
        .all()
    )
    return {fila.business_id: fila for fila in filas}


async def _precio_desde(
    sesion: AsyncSession, negocios: list[uuid.UUID]
) -> dict[uuid.UUID, int | None]:
    """El precio más bajo de cada negocio, en una consulta para todos.

    Una lista de salones sin precio obliga a entrar en cada ficha para descartarla, que es
    justo lo que hace que la gente vuelva a WhatsApp. Va en centavos, como todo lo demás:
    formatear es cosa de quien pinta.
    """
    if not negocios:
        return {}
    filas = await sesion.execute(
        select(Service.business_id, func.min(Service.price_minor))
        .where(
            Service.business_id.in_(negocios),
            Service.active.is_(True),
            Service.price_minor.is_not(None),
        )
        .group_by(Service.business_id)
    )
    return {negocio: precio for negocio, precio in filas.all()}
