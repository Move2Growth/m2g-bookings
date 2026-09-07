"""Los salones que caben en el rectángulo que se ve en la pantalla (punto 5 del encargo).

Esto **no es geo nuevo**. La búsqueda del marketplace ya es PostGIS con radio y distancia en
metros (ADR-0005, `servicios/busqueda.py`); lo que faltaba es la otra pregunta, la que hace un
mapa: «dime lo que hay dentro de estas cuatro esquinas». Un radio no sirve para eso — la
pantalla de un móvil es un rectángulo alto y estrecho, y el círculo que lo cubre entero se
lleva medio barrio que no se ve.

Dos decisiones que no son evidentes:

* **Hay tope de resultados, y se dice cuándo se aplicó.** Un mapa alejado sobre Panamá entera
  devolvería el catálogo completo, y eso son varios megabytes en datos móviles para pintar
  puntos que no caben en la pantalla. Cuando el tope recorta, la respuesta lo dice —
  `truncado`— para que la pantalla pueda pedir «acerca el mapa» en vez de mentir enseñando
  quince salones donde hay cuatrocientos.

* **Al recortar se conservan los del centro.** Se ordena por distancia al centro del
  rectángulo, que es donde mira quien mueve el mapa. Recortar por identificador o por nombre
  dejaría huecos arbitrarios y el mapa parecería roto justo en el sitio que se está mirando.

Y lo de siempre: esto lo sirve el **rol público**, que no tiene permiso sobre reservas ni sobre
fichas de cliente. Aquí no viaja ningún teléfono, y no porque el serializador se acuerde.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from geoalchemy2 import Geography, Geometry
from sqlalchemy import Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.errores import DatoInvalido
from agenda.modelos.negocio import Business, Location
from agenda.modelos.reviews import BusinessRatingStats

#: Cuántos puntos se devuelven como mucho si nadie dice otra cosa. Con cien pines la pantalla
#: de un móvil ya está llena; el resto solo pesa.
TOPE_POR_DEFECTO = 100

#: El techo duro. Ni pidiéndolo se pasa de aquí: el parámetro es del cliente y un cliente
#: puede pedir un millón.
TOPE_MAXIMO = 300

#: Lo más grande que se admite como «lo que se ve en la pantalla», en grados. 12° de lado son
#: unas 1.300 km: cabe Panamá entera con margen. Más que eso no es un mapa, es una descarga del
#: catálogo con otro nombre.
LADO_MAXIMO_GRADOS = 12.0


@dataclass(frozen=True)
class SalonEnElMapa:
    """Un pin. Lo justo para dibujarlo y decidir si se toca."""

    negocio_id: uuid.UUID
    slug: str
    nombre: str
    longitud: float
    latitud: float
    #: El bayesiano (REV-5), que es el que se enseña en todas partes. `None` = todavía sin
    #: reseñas, que **no es lo mismo** que un cero y no se pinta igual.
    rating: float | None
    numero_reviews: int


@dataclass(frozen=True)
class Vista:
    """Lo que hay dentro del rectángulo, y si hubo que recortar."""

    salones: list[SalonEnElMapa]
    truncado: bool


async def en_el_rectangulo(
    sesion: AsyncSession,
    *,
    oeste: float,
    sur: float,
    este: float,
    norte: float,
    limite: int = TOPE_POR_DEFECTO,
) -> Vista:
    """Los salones publicados cuyo punto cae dentro del rectángulo.

    Los cuatro números son los del mapa: las longitudes de los bordes izquierdo y derecho y las
    latitudes de los bordes inferior y superior. Se validan aquí y no se «arreglan» solos: un
    rectángulo al revés casi siempre significa que quien llama cambió el orden de los
    parámetros, y devolverle cero resultados en silencio le costaría media tarde.
    """
    limite = max(1, min(limite, TOPE_MAXIMO))

    if este <= oeste or norte <= sur:
        raise DatoInvalido(
            "El rectángulo del mapa está al revés: «este» tiene que ser mayor que «oeste» y "
            "«norte» mayor que «sur»."
        )
    if (este - oeste) > LADO_MAXIMO_GRADOS or (norte - sur) > LADO_MAXIMO_GRADOS:
        raise DatoInvalido(
            "Ese trozo de mapa es demasiado grande. Acerca el mapa y vuelve a pedirlo."
        )

    # `geography` y no `geometry`, igual que en la búsqueda: la columna es `geography` y
    # compararla con una `geometry` obligaría a convertir **fila a fila**, que tira al suelo el
    # índice GiST (ADR-0005). Por eso el rectángulo se convierte una vez, aquí.
    ventana = cast(func.ST_MakeEnvelope(oeste, sur, este, norte, 4326), Geography(srid=4326))
    # El centro se calcula en Python y no con `ST_Centroid`: de un rectángulo es la media de
    # sus esquinas, y pedírselo a la base sería una función más en el plan para lo mismo.
    centro = cast(
        func.ST_SetSRID(func.ST_MakePoint((oeste + este) / 2, (sur + norte) / 2), 4326),
        Geography(srid=4326),
    )
    distancia_al_centro = func.ST_Distance(Location.geo, centro)
    # `ST_X` y `ST_Y` solo existen para `geometry`; la conversión es de **una** fila por
    # resultado ya filtrado, así que no toca ningún índice.
    punto = cast(Location.geo, Geometry(geometry_type="POINT", srid=4326))

    consulta = (
        select(
            Business.id,
            Business.slug,
            Business.display_name,
            cast(func.ST_X(punto), Float).label("longitud"),
            cast(func.ST_Y(punto), Float).label("latitud"),
            BusinessRatingStats.rating_bayesian,
            BusinessRatingStats.reviews_count,
        )
        .join(Location, Location.business_id == Business.id)
        .join(
            BusinessRatingStats,
            BusinessRatingStats.business_id == Business.id,
            isouter=True,
        )
        # El filtro de publicado lo aplica además la política del rol público. Se escribe
        # igualmente (ADR-0002): sin él, el planificador no usa el índice parcial.
        .where(Business.status == "publicado", func.ST_Intersects(Location.geo, ventana))
        .order_by(distancia_al_centro)
        # Uno más que el tope: es cómo se sabe que había más sin contar la tabla entera.
        .limit(limite + 1)
    )

    filas = (await sesion.execute(consulta)).all()
    truncado = len(filas) > limite

    return Vista(
        truncado=truncado,
        salones=[
            SalonEnElMapa(
                negocio_id=fila.id,
                slug=fila.slug,
                nombre=fila.display_name,
                longitud=float(fila.longitud),
                latitud=float(fila.latitud),
                rating=float(fila.rating_bayesian) if fila.rating_bayesian is not None else None,
                numero_reviews=fila.reviews_count or 0,
            )
            for fila in filas[:limite]
        ],
    )
