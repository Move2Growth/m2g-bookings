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
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from agenda.api.dependencias import SesionPublica
from agenda.bd import sesion_de_negocio
from agenda.errores import NegocioNoPublicado
from agenda.modelos.negocio import Business
from agenda.servicios import disponibilidad as servicio_disponibilidad

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
