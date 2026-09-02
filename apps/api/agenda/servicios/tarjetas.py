"""La «tarjeta» de un negocio: lo que se pinta de él en cualquier lista.

Existe porque tres pantallas distintas necesitan exactamente lo mismo —resultados de búsqueda,
favoritos y «reservar de nuevo»— y componerlo tres veces garantizaría que la portada enseñe el
rating y los favoritos no.

**Se sirve con el rol público**, no con el del negocio, y eso es lo que la hace segura por
construcción: `agenda_publico` no tiene permiso sobre reservas, ni sobre fichas de cliente, ni
sobre `users`. Aunque este módulo quisiera colar un teléfono en la tarjeta, la base no se lo
permitiría.

Una consulta por concepto y ninguna dentro de un bucle. Diez tarjetas se componen con cinco
consultas, no con cincuenta: es la diferencia entre una portada que carga en 3G y una que no.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.modelos.catalogo import Service, ServiceCategory
from agenda.modelos.marketplace import Zone
from agenda.modelos.negocio import (
    Business,
    BusinessCategory,
    BusinessHours,
    BusinessMedia,
    Location,
)
from agenda.modelos.reviews import BusinessRatingStats


@dataclass
class Tarjeta:
    """Lo publicable de un negocio. **Ni un campo de contacto.**"""

    negocio_id: uuid.UUID
    slug: str
    nombre: str
    direccion: str | None = None
    zona: str | None = None
    foto_portada: str | None = None
    rating: float | None = None
    numero_reviews: int = 0
    desde_centavos: int | None = None
    categorias: list[str] = field(default_factory=list)
    #: `None` cuando el negocio **no tiene horario cargado**, que no es lo mismo que estar
    #: cerrado. Un negocio a medio configurar tiene que poder distinguirse de uno que hoy
    #: libra, o el filtro «abierto ahora» convierte lo primero en lo segundo.
    abierto_ahora: bool | None = None


async def componer(
    sesion: AsyncSession, negocios: list[uuid.UUID], *, ahora: datetime | None = None
) -> dict[uuid.UUID, Tarjeta]:
    """Compone las tarjetas de una lista de negocios en un puñado de consultas."""
    if not negocios:
        return {}

    filas = (
        await sesion.execute(
            select(
                Business.id,
                Business.slug,
                Business.display_name,
                Business.timezone,
                Location.address_line,
                Zone.name,
            )
            .join(Location, Location.business_id == Business.id, isouter=True)
            .join(Zone, Zone.id == Location.zone_id, isouter=True)
            .where(Business.id.in_(negocios))
        )
    ).all()

    portadas = await _portadas(sesion, negocios)
    ratings = await _ratings(sesion, negocios)
    precios = await _precio_desde(sesion, negocios)
    categorias = await _categorias(sesion, negocios)
    horarios = await _horarios(sesion, negocios)

    tarjetas: dict[uuid.UUID, Tarjeta] = {}
    for negocio_id, slug, nombre, zona_horaria, direccion, zona in filas:
        total, puntuacion = ratings.get(negocio_id, (0, None))
        tarjetas[negocio_id] = Tarjeta(
            negocio_id=negocio_id,
            slug=slug,
            nombre=nombre,
            direccion=direccion,
            zona=zona,
            foto_portada=portadas.get(negocio_id),
            rating=puntuacion,
            numero_reviews=total,
            desde_centavos=precios.get(negocio_id),
            categorias=categorias.get(negocio_id, []),
            abierto_ahora=esta_abierto(horarios.get(negocio_id, []), zona_horaria, ahora=ahora),
        )
    return tarjetas


def esta_abierto(
    tramos: list[tuple[int, time, time]], zona_horaria: str, *, ahora: datetime | None = None
) -> bool | None:
    """Si el negocio está abierto **en su hora local** ahora mismo (MKT-2).

    Sin tramos devuelve `None` y no `False`: «no lo sé» y «está cerrado» son respuestas
    distintas y la pantalla las pinta distinto.

    El tramo que cruza la medianoche —el spa que cierra a las 00:30— se comprueba en dos
    trozos: desde la apertura hasta el final del día, y desde el principio del día siguiente
    hasta el cierre. Es la misma convención de ADR-0003 que usa el motor: `cierra <= abre`
    significa que el tramo se pasa de las doce.
    """
    if not tramos:
        return None

    momento = (ahora or datetime.now(ZoneInfo(zona_horaria))).astimezone(ZoneInfo(zona_horaria))
    hoy = momento.weekday()
    ayer = (hoy - 1) % 7
    hora = momento.time()

    for dia, abre, cierra in tramos:
        cruza = cierra <= abre
        if dia == hoy and (hora >= abre if cruza else abre <= hora < cierra):
            return True
        # El tramo de ayer que se pasó de medianoche sigue abierto esta madrugada.
        if cruza and dia == ayer and hora < cierra:
            return True
    return False


async def _portadas(sesion: AsyncSession, negocios: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    from agenda.api.comunes import url_de_media

    filas = (
        (
            await sesion.execute(
                select(BusinessMedia).where(
                    BusinessMedia.business_id.in_(negocios),
                    BusinessMedia.kind == "portada",
                )
            )
        )
        .scalars()
        .all()
    )
    return {
        fila.business_id: url
        for fila in filas
        if (url := url_de_media(fila.storage_key)) is not None
    }


async def _ratings(
    sesion: AsyncSession, negocios: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[int, float | None]]:
    """El agregado ya calculado. **El que sale es el bayesiano** (REV-5, ADR-0009)."""
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
            float(fila.rating_bayesian) if fila.rating_bayesian is not None else None,
        )
        for fila in filas
    }


async def _precio_desde(
    sesion: AsyncSession, negocios: list[uuid.UUID]
) -> dict[uuid.UUID, int | None]:
    """El servicio más barato de cada negocio, en una consulta para todos.

    Una lista de salones sin precio obliga a entrar en cada ficha para descartarla, que es
    justo lo que hace que la gente vuelva al WhatsApp.
    """
    filas = await sesion.execute(
        select(Service.business_id, func.min(Service.price_minor))
        .where(
            Service.business_id.in_(negocios),
            Service.active.is_(True),
            Service.price_minor.is_not(None),
        )
        .group_by(Service.business_id)
    )
    return dict(filas.all())


async def _categorias(
    sesion: AsyncSession, negocios: list[uuid.UUID]
) -> dict[uuid.UUID, list[str]]:
    """Los **nombres** de las categorías, no los slugs: es lo que se pinta en la tarjeta."""
    filas = (
        await sesion.execute(
            select(BusinessCategory.business_id, ServiceCategory.name)
            .join(ServiceCategory, ServiceCategory.id == BusinessCategory.service_category_id)
            .where(BusinessCategory.business_id.in_(negocios))
            .order_by(BusinessCategory.is_primary.desc(), ServiceCategory.name)
        )
    ).all()

    salida: dict[uuid.UUID, list[str]] = {}
    for negocio_id, nombre in filas:
        salida.setdefault(negocio_id, []).append(nombre)
    return salida


async def _horarios(
    sesion: AsyncSession, negocios: list[uuid.UUID]
) -> dict[uuid.UUID, list[tuple[int, time, time]]]:
    filas = (
        (await sesion.execute(select(BusinessHours).where(BusinessHours.business_id.in_(negocios))))
        .scalars()
        .all()
    )
    salida: dict[uuid.UUID, list[tuple[int, time, time]]] = {}
    for fila in filas:
        salida.setdefault(fila.business_id, []).append(
            (fila.weekday, fila.opens_at, fila.closes_at)
        )
    return salida


#: Cuánto se mira hacia delante al calcular «la próxima hora libre». Un día: si un salón no
#: tiene hueco hoy, lo que la tarjeta tiene que decir es «hoy no», no rebuscar hasta el jueves.
HORIZONTE_PROXIMA_HORA = timedelta(days=1)
