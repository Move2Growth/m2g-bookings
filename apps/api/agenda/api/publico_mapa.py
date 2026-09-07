"""La vista de mapa de la clienta (punto 5 del encargo).

Va en su propio archivo y con su propio router aunque comparta el prefijo `/publico`: es una
pieza cerrada —una consulta, un serializador— y separarla evita que el módulo público, que ya
es el más grande, siga creciendo por acumulación.

**Aquí no viaja ningún teléfono**, y no porque el serializador se acuerde: lo sirve el rol
`agenda_publico`, que no tiene permiso sobre reservas ni sobre fichas de cliente, y lo que se
devuelve es lo mismo que ya enseña una tarjeta de resultado más el punto en el mapa.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from agenda.api.dependencias import SesionPublica
from agenda.servicios import mapa as servicio_mapa

router = APIRouter(prefix="/api/v1/publico", tags=["público"])


class SalonEnElMapa(BaseModel):
    """Un pin. Lo justo para dibujarlo y decidir si se toca."""

    negocio_id: uuid.UUID
    slug: str
    nombre: str
    longitud: float
    latitud: float
    rating: float | None = Field(
        default=None, description="El bayesiano (REV-5). Nulo = todavía sin reseñas"
    )
    numero_reviews: int = 0


class VistaDelMapa(BaseModel):
    salones: list[SalonEnElMapa]
    truncado: bool = Field(
        description=(
            "Cierto cuando había más salones de los que caben en el tope. La pantalla debería "
            "pedir que se acerque el mapa en vez de enseñar una muestra sin decirlo"
        )
    )


@router.get("/mapa", summary="Salones dentro del rectángulo visible (MKT-1, punto 5)")
async def mapa(
    sesion: SesionPublica,
    oeste: Annotated[float, Query(ge=-180, le=180, description="Longitud del borde izquierdo")],
    sur: Annotated[float, Query(ge=-90, le=90, description="Latitud del borde inferior")],
    este: Annotated[float, Query(ge=-180, le=180, description="Longitud del borde derecho")],
    norte: Annotated[float, Query(ge=-90, le=90, description="Latitud del borde superior")],
    limite: Annotated[
        int, Query(ge=1, le=servicio_mapa.TOPE_MAXIMO, description="Tope de pines devueltos")
    ] = servicio_mapa.TOPE_POR_DEFECTO,
) -> VistaDelMapa:
    """Lo que hay dentro de las cuatro esquinas que se ven en la pantalla.

    Es la otra pregunta del marketplace, distinta de la que ya resolvía la búsqueda: «cerca de
    mí» es un radio y esto es un rectángulo. La pantalla de un móvil es alta y estrecha, así que
    el círculo que la cubre entera se lleva medio barrio que no se ve.

    **Con tope, y diciéndolo.** Un mapa alejado sobre el país entero serían varios megabytes de
    datos móviles para pintar puntos que no caben; cuando el tope recorta, `truncado` viene en
    cierto y se conservan los del centro del rectángulo, que es donde está mirando quien mueve
    el mapa.
    """
    vista = await servicio_mapa.en_el_rectangulo(
        sesion, oeste=oeste, sur=sur, este=este, norte=norte, limite=limite
    )
    return VistaDelMapa(
        truncado=vista.truncado,
        salones=[
            SalonEnElMapa(
                negocio_id=s.negocio_id,
                slug=s.slug,
                nombre=s.nombre,
                longitud=s.longitud,
                latitud=s.latitud,
                rating=s.rating,
                numero_reviews=s.numero_reviews,
            )
            for s in vista.salones
        ],
    )
