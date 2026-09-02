"""La búsqueda del marketplace: encontrar, filtrar y ordenar (MKT-1, MKT-2, MKT-3).

El reparto de trabajo entre la base y el código es deliberado y tiene tres pisos, del más
barato al más caro:

1. **PostgreSQL filtra y calcula la distancia.** Es lo que sabe hacer con índices sobre 5.000
   negocios y un presupuesto de 500 ms: texto, categoría, zona, radio, precio y rating.
2. **El ranking se combina en Python** a partir de señales precalculadas más la distancia, que
   es lo único que depende de quién busca. Escribir la fórmula en SQL la volvería intocable, y
   el objetivo es que los pesos se cambien desde la consola sin desplegar (ADR-0009).
3. **La disponibilidad real se calcula con el motor de reservas**, no con una copia. Es el
   filtro más caro del producto —una consulta de agenda por negocio— y por eso se aplica **al
   final y solo a los candidatos que ya pasaron todo lo demás**, recorriendo la lista ordenada
   hasta llenar la página. Un filtro que promete horas libres y las calcula con otra fórmula
   que la de reservar es peor que no tenerlo: manda a la gente a un hueco que no existe.

Y una regla que se ve en el orden de las funciones: **los patrocinados se resuelven aparte y se
intercalan al final**. Nunca compiten en la fórmula, nunca desplazan a un orgánico fuera de la
página, y no tocan el rating.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from geoalchemy2.functions import ST_DWithin, ST_SetSRID
from sqlalchemy import Float, cast, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.bd import sesion_de_negocio
from agenda.dominio.ranking import Puntuacion, SenalesNegocio, puntuar
from agenda.modelos.catalogo import Service, ServiceCategory
from agenda.modelos.marketplace import BusinessRankingSignals, Zone
from agenda.modelos.negocio import Business, BusinessCategory, Location
from agenda.modelos.reviews import BusinessRatingStats
from agenda.servicios import disponibilidad as servicio_disponibilidad
from agenda.servicios import tarjetas as servicio_tarjetas
from agenda.servicios.pesos import pesos_vigentes

#: Cuántos resultados se sirven por página. Con tarjetas de 132 px, cuatro entran en el primer
#: pantallazo de un teléfono; diez es lo que se recorre con un par de gestos.
POR_PAGINA = 10

#: Qué significa «ahora» al filtrar por disponibilidad: las próximas tres horas. No es la
#: antelación mínima —esa la pone cada negocio y el motor la respeta— sino hasta dónde mira la
#: pregunta «¿me pueden atender ya?».
VENTANA_AHORA = timedelta(hours=3)

#: Techo de negocios a los que se les calcula la agenda en una petición. La disponibilidad real
#: cuesta varias consultas por negocio, y sin techo una búsqueda amplia con el filtro puesto
#: recorrería el catálogo entero. Se recorre la lista **ya ordenada**, así que el techo recorta
#: por la cola: lo que se pierde son resultados que nadie iba a ver.
MAXIMO_AGENDAS_POR_PETICION = 40

Orden = Literal["relevancia", "distancia", "precio", "rating", "nuevos"]
Disponibilidad = Literal["ahora", "hoy", "fecha"]


@dataclass
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
    numero_reviews: int = 0
    foto_portada: str | None = None
    categorias: list[str] | None = None
    abierto_ahora: bool | None = None
    #: Instante ISO de la primera hora libre de hoy. Solo se calcula cuando se pide, porque
    #: cuesta una consulta de agenda por negocio (ver `con_proxima_hora`).
    proxima_hora: datetime | None = None
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
    precio_min: int | None = None,
    precio_max: int | None = None,
    rating_min: float | None = None,
    disponibilidad: Disponibilidad | None = None,
    dia: date | None = None,
    abierto_ahora: bool = False,
    orden: Orden = "relevancia",
    pagina: int = 1,
    con_proxima_hora: bool = False,
    ahora: datetime | None = None,
) -> list[Resultado]:
    """Busca negocios publicados, los filtra y los ordena.

    Se puede buscar **por punto o por zona**, y no son lo mismo: «cerca de mí» es un radio, y
    «El Cangrejo» es un sitio con nombre que la gente escribe en Google. Las dos entradas
    conviven porque el producto necesita las dos (ADR-0005).
    """
    ahora = ahora or datetime.now(UTC)

    consulta = (
        select(
            Business.id,
            Business.slug,
            Business.display_name,
            Business.published_at,
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
                    BusinessCategory.service_category_id.in_(
                        select(ServiceCategory.id).where(ServiceCategory.slug == categoria)
                    )
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

    if precio_min is not None or precio_max is not None:
        consulta = consulta.where(
            Business.id.in_(_negocios_en_rango_de_precio(precio_min, precio_max))
        )

    if rating_min is not None:
        # Se filtra por el **bayesiano**, que es el que se enseña (REV-5). Filtrar por la media
        # simple dejaría pasar salones con una sola reseña de cinco estrellas, que es justo lo
        # que la ponderación existe para evitar.
        consulta = consulta.where(
            Business.id.in_(
                select(BusinessRatingStats.business_id).where(
                    BusinessRatingStats.rating_bayesian >= rating_min
                )
            )
        )

    filas = (await sesion.execute(consulta)).all()
    if not filas:
        return []

    # Adornar **antes** de ordenar, y este orden importa: el precio desde y el rating fresco
    # los pone `_adornar`. Ordenando primero, «más baratos» comparaba `None` contra `None` y
    # devolvía el orden del ranking con otro nombre, y «mejor valorados» ordenaba por la señal
    # vieja en vez de por la nota que ve la gente.
    resultados = await _puntuar(sesion, filas, ahora=ahora)
    resultados = await _adornar(sesion, resultados, ahora=ahora)
    resultados = _ordenar(resultados, orden)

    if abierto_ahora:
        # `None` —negocio sin horario cargado— **no pasa el filtro**: quien pide «abierto
        # ahora» pregunta por algo afirmativo, y un «no lo sé» que se cuela es una puerta
        # cerrada al llegar.
        resultados = [r for r in resultados if r.abierto_ahora is True]

    if disponibilidad is not None:
        resultados = await _filtrar_por_agenda(
            sesion, resultados, modo=disponibilidad, dia=dia, ahora=ahora, pagina=pagina
        )
    elif con_proxima_hora:
        await _rellenar_proxima_hora(
            sesion, resultados[: pagina * POR_PAGINA][-POR_PAGINA:], ahora=ahora
        )

    primero = (pagina - 1) * POR_PAGINA
    return resultados[primero : primero + POR_PAGINA]


def _punto(longitud: float, latitud: float):
    return ST_SetSRID(func.ST_MakePoint(longitud, latitud), 4326)


def _distancia(longitud: float | None, latitud: float | None):
    """Metros hasta el punto de búsqueda, o `NULL` si nadie dijo desde dónde busca."""
    if longitud is None or latitud is None:
        return literal(None)
    return cast(func.ST_Distance(Location.geo, _punto(longitud, latitud)), Float)


def _negocios_en_rango_de_precio(minimo: int | None, maximo: int | None):
    """Negocios con **algún** servicio dentro del rango, en centavos.

    «Algún» y no «todos»: quien filtra hasta 25 dólares quiere salones donde pueda pagar 25,
    no salones donde todo cueste menos de 25. Un salón que hace el corte a 18 y el balayage a
    150 tiene que salir en la búsqueda de quien busca un corte barato.

    Los servicios «a consultar» no tienen precio y por tanto **no entran** en ningún rango: no
    se les puede prometer a nadie que caben en su presupuesto.
    """
    consulta = select(Service.business_id).where(
        Service.active.is_(True),
        Service.deleted_at.is_(None),
        Service.price_minor.is_not(None),
    )
    if minimo is not None:
        consulta = consulta.where(Service.price_minor >= minimo)
    if maximo is not None:
        consulta = consulta.where(Service.price_minor <= maximo)
    return consulta


async def _puntuar(sesion: AsyncSession, filas, *, ahora: datetime) -> list[Resultado]:
    """Combina las señales precalculadas con la distancia y calcula la puntuación del ranking.

    **No ordena**: ordenar es lo último que pasa, después de adornar, porque dos de los órdenes
    que se pueden pedir —precio y rating— dependen de datos que pone `_adornar`.
    """
    pesos = await pesos_vigentes(sesion)
    ids = [fila.id for fila in filas]
    senales = await _senales(sesion, ids)
    ratings = await _ratings(sesion, ids)

    resultados: list[Resultado] = []
    for fila in filas:
        precalculadas = senales.get(fila.id)
        total_reviews, suma_notas, bayesiano = ratings.get(fila.id, (0, 0, None))
        dias_publicado = (ahora - fila.published_at).days if fila.published_at is not None else 999
        puntuacion = puntuar(
            SenalesNegocio(
                distancia_metros=float(fila.distancia) if fila.distancia is not None else None,
                suma_notas=suma_notas,
                numero_reviews=total_reviews,
                reservas_recientes=precalculadas.bookings_recent if precalculadas else 0,
                completadas=0,
                no_asistidas=0,
                canceladas_por_negocio=0,
                completitud_perfil=float(precalculadas.completeness or 0) if precalculadas else 0.0,
                dias_desde_ultima_actividad=0,
                dias_desde_publicacion=dias_publicado,
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
                rating=bayesiano,
                numero_reviews=total_reviews,
                desde_centavos=None,  # lo rellena `_adornar`, que corre antes de ordenar
                puntuacion=puntuacion,
            )
        )

    return resultados


def _ordenar(resultados: list[Resultado], orden: Orden) -> list[Resultado]:
    """El orden que pidió quien busca. Por defecto, la fórmula del ranking.

    Los criterios explícitos —distancia, precio, rating, nuevos— **no son el ranking**: son
    ordenaciones que la persona pide a mano y que dejan la fórmula fuera. Es lo correcto:
    quien pulsa «más baratos» quiere los más baratos, no los más baratos ponderados por
    completitud del perfil.
    """
    match orden:
        case "distancia":
            # Sin distancia, al final: no se puede fingir que un negocio sin punto está cerca.
            return sorted(
                resultados,
                key=lambda r: (r.distancia_metros is None, r.distancia_metros or 0),
            )
        case "precio":
            return sorted(
                resultados, key=lambda r: (r.desde_centavos is None, r.desde_centavos or 0)
            )
        case "rating":
            return sorted(resultados, key=lambda r: (r.rating or 0), reverse=True)
        case "nuevos":
            # Los identificadores son UUID v7: llevan la hora dentro, así que ordenar por
            # identificador descendente es ordenar por antigüedad sin columna adicional.
            return sorted(resultados, key=lambda r: r.negocio_id, reverse=True)
        case _:
            return sorted(
                resultados, key=lambda r: r.puntuacion.total if r.puntuacion else 0, reverse=True
            )


async def _adornar(
    sesion: AsyncSession, resultados: list[Resultado], *, ahora: datetime
) -> list[Resultado]:
    """Añade a cada resultado la foto, el precio desde, las categorías y si está abierto.

    Se compone con el mismo módulo que los favoritos (`servicios.tarjetas`) para que las dos
    listas enseñen exactamente lo mismo. Si esto se duplicara, la portada acabaría con foto y
    los favoritos sin ella.
    """
    if not resultados:
        return resultados

    tarjetas = await servicio_tarjetas.componer(
        sesion, [r.negocio_id for r in resultados], ahora=ahora
    )
    for resultado in resultados:
        tarjeta = tarjetas.get(resultado.negocio_id)
        if tarjeta is None:
            continue
        resultado.foto_portada = tarjeta.foto_portada
        resultado.desde_centavos = tarjeta.desde_centavos
        resultado.categorias = tarjeta.categorias
        resultado.abierto_ahora = tarjeta.abierto_ahora
        # El rating de la tarjeta manda si `business_ranking_signals` aún no se ha recalculado:
        # `business_rating_stats` se actualiza en el acto al dejar una reseña y las señales del
        # ranking las refresca un trabajo periódico.
        if tarjeta.rating is not None:
            resultado.rating = tarjeta.rating
            resultado.numero_reviews = tarjeta.numero_reviews
    return resultados


def _ventana_de_agenda(
    modo: Disponibilidad, dia: date | None, zona: str, ahora: datetime
) -> tuple[datetime, datetime]:
    """De «ahora», «hoy» o una fecha a un par de instantes, **en la zona del negocio**.

    Es la única aritmética de husos fuera del motor y está acotada a propósito: convertir «hoy»
    a instantes necesita saber de quién es ese «hoy», y el día de un salón de Panamá empieza a
    las 05:00 UTC. Calcularlo en UTC daría medianoches equivocadas para media búsqueda.
    """
    tz = ZoneInfo(zona)
    local = ahora.astimezone(tz)

    match modo:
        case "ahora":
            return ahora, ahora + VENTANA_AHORA
        case "hoy":
            fin = datetime.combine(local.date() + timedelta(days=1), time(0, 0), tzinfo=tz)
            return ahora, fin.astimezone(UTC)
        case _:
            objetivo = dia or local.date()
            inicio = datetime.combine(objetivo, time(0, 0), tzinfo=tz)
            return inicio.astimezone(UTC), (inicio + timedelta(days=1)).astimezone(UTC)


async def _filtrar_por_agenda(
    sesion: AsyncSession,
    resultados: list[Resultado],
    *,
    modo: Disponibilidad,
    dia: date | None,
    ahora: datetime,
    pagina: int,
) -> list[Resultado]:
    """Deja solo los que **de verdad** tienen hueco, usando el motor de reservas.

    Se recorre la lista ya ordenada y se para al llenar la página pedida: comprobar la agenda
    de los 300 resultados de «peluquería en Panamá» para enseñar diez es trabajo tirado. Los
    que no se llegan a comprobar simplemente no salen, que es lo mismo que les pasaría estando
    en la página doce.
    """
    necesarios = pagina * POR_PAGINA
    servicios = await _servicio_mas_corto(sesion, [r.negocio_id for r in resultados])
    zonas = await _zonas_horarias(sesion, [r.negocio_id for r in resultados])

    con_hueco: list[Resultado] = []
    comprobados = 0
    for resultado in resultados:
        if len(con_hueco) >= necesarios or comprobados >= MAXIMO_AGENDAS_POR_PETICION:
            break
        servicio_id = servicios.get(resultado.negocio_id)
        if servicio_id is None:
            # Sin servicio activo no hay nada que reservar. No es un fallo: es un negocio a
            # medio configurar, y por eso no aparece cuando se pregunta por horas libres.
            continue

        comprobados += 1
        zona = zonas.get(resultado.negocio_id, "America/Panama")
        desde, hasta = _ventana_de_agenda(modo, dia, zona, ahora)
        primera = await _primera_hora_libre(
            resultado.negocio_id, servicio_id, desde=desde, hasta=hasta, ahora=ahora
        )
        if primera is not None:
            resultado.proxima_hora = primera
            con_hueco.append(resultado)

    return con_hueco


async def _rellenar_proxima_hora(
    sesion: AsyncSession, resultados: list[Resultado], *, ahora: datetime
) -> None:
    """Calcula «la próxima hora libre» solo para los resultados de la página que se sirve.

    Es el mismo cálculo que el filtro y por eso se hace aparte y bajo petición: son varias
    consultas por negocio, y ponerlo siempre convertiría la portada en la pantalla más cara del
    producto para un dato que no todas las pantallas usan.
    """
    if not resultados:
        return
    servicios = await _servicio_mas_corto(sesion, [r.negocio_id for r in resultados])
    zonas = await _zonas_horarias(sesion, [r.negocio_id for r in resultados])

    for resultado in resultados:
        servicio_id = servicios.get(resultado.negocio_id)
        if servicio_id is None:
            continue
        zona = zonas.get(resultado.negocio_id, "America/Panama")
        desde, hasta = _ventana_de_agenda("hoy", None, zona, ahora)
        resultado.proxima_hora = await _primera_hora_libre(
            resultado.negocio_id, servicio_id, desde=desde, hasta=hasta, ahora=ahora
        )


async def _primera_hora_libre(
    negocio_id: uuid.UUID,
    servicio_id: uuid.UUID,
    *,
    desde: datetime,
    hasta: datetime,
    ahora: datetime,
) -> datetime | None:
    """El primer hueco del negocio, calculado con **el motor de reservas**.

    Se abre una sesión fijada a ese negocio concreto porque el cálculo necesita horarios,
    asignaciones y ocupación, y **nada de eso es público**: el rol del marketplace no los ve, y
    está bien que no los vea. Desde esa sesión no existe ningún otro negocio, aunque este
    código quisiera.
    """
    async with sesion_de_negocio(str(negocio_id)) as sesion_negocio:
        resultado = await servicio_disponibilidad.calcular(
            sesion_negocio,
            negocio_id=negocio_id,
            servicios_ids=[servicio_id],
            desde=desde,
            hasta=hasta,
            ahora=ahora,
        )
    return resultado.slots[0].inicio if resultado.slots else None


async def _servicio_mas_corto(
    sesion: AsyncSession, negocios: list[uuid.UUID]
) -> dict[uuid.UUID, uuid.UUID]:
    """El servicio activo más corto de cada negocio, como sonda de disponibilidad.

    Es la definición honesta de «tiene hueco»: si el más corto no cabe, no cabe ninguno. Usar
    el más largo diría que no hay hueco en salones donde sí lo hay para un corte.

    Se resuelve con `DISTINCT ON`, que es lo que PostgreSQL tiene para «una fila por grupo,
    la primera según este orden». La versión obvia —agrupar y quedarse con `min(id)`— **no
    compila**: los identificadores son UUID y `min()` no existe para ese tipo. El desempate por
    identificador dentro del `ORDER BY` mantiene el resultado estable entre llamadas, que es lo
    que hace que dos búsquedas seguidas devuelvan lo mismo.
    """
    if not negocios:
        return {}

    filas = (
        await sesion.execute(
            select(Service.business_id, Service.id)
            .where(
                Service.business_id.in_(negocios),
                Service.active.is_(True),
                Service.deleted_at.is_(None),
            )
            .order_by(Service.business_id, Service.duration_min, Service.id)
            .distinct(Service.business_id)
        )
    ).all()
    return dict(filas)


async def _zonas_horarias(sesion: AsyncSession, negocios: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not negocios:
        return {}
    filas = (
        await sesion.execute(
            select(Business.id, Business.timezone).where(Business.id.in_(negocios))
        )
    ).all()
    return dict(filas)


async def _senales(
    sesion: AsyncSession, negocios: list[uuid.UUID]
) -> dict[uuid.UUID, BusinessRankingSignals]:
    """Las señales caras, ya calculadas por el trabajo periódico.

    Recorrer las reservas de 5.000 negocios en cada búsqueda no cabe en 500 ms; por eso esto es
    una lectura y no un cálculo. El precio es un desfase de minutos entre la realidad y el
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


async def _ratings(
    sesion: AsyncSession, negocios: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[int, int, float | None]]:
    """Conteo, suma de notas y bayesiano ya calculado, por negocio.

    La suma hace falta porque la fórmula del ranking vuelve a ponderar con los pesos vigentes:
    si solo se pasara la media ya calculada, cambiar `bayes_c` en la consola no cambiaría el
    orden hasta que alguien dejara una reseña nueva.
    """
    filas = (
        (
            await sesion.execute(
                select(BusinessRatingStats).where(BusinessRatingStats.business_id.in_(negocios))
            )
        )
        .scalars()
        .all()
    )
    return {
        fila.business_id: (
            fila.reviews_count,
            fila.rating_sum,
            float(fila.rating_bayesian) if fila.rating_bayesian is not None else None,
        )
        for fila in filas
    }
