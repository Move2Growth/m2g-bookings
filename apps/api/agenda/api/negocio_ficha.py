"""La ficha del salón tal como la ve el mundo, editada desde dentro (NEG-1, NEG-2, MKT-6).

Es la pantalla que decide si alguien entra o pasa de largo, y hasta ahora no se podía tocar:
el nombre y la dirección se ponían en el alta y ahí se quedaban para siempre.

**El teléfono es la única excepción a «se edita y se devuelve».** Se puede guardar, y la ficha
dice *si lo hay*, pero el número **no sale nunca** hacia el público: el click-to-chat se
resuelve en servidor, con un salto que registra el clic y redirige (garantía nº 3). Si el
número viajara en el perfil, alguien se lleva la base entera de negocios en una tarde, y eso
está anotado como riesgo en el propio brief.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from geoalchemy2 import Geometry
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.api.comunes import url_de_media
from agenda.api.dependencias import SesionNegocio, exigir_dueno
from agenda.errores import DatoInvalido, NoExiste
from agenda.modelos.catalogo import ServiceCategory
from agenda.modelos.marketplace import Zone
from agenda.modelos.negocio import (
    Attribute,
    AttributeValue,
    Business,
    BusinessAttribute,
    BusinessCategory,
    BusinessMedia,
    Location,
)

router = APIRouter(prefix="/api/v1/negocio", tags=["ficha del negocio"])


class FotoDelNegocio(BaseModel):
    id: uuid.UUID
    url: str
    clase: str = Field(description="portada | galeria")
    texto_alternativo: str | None
    orden: int
    moderacion: str


class FichaDelNegocio(BaseModel):
    """Lo que el dueño edita de su perfil público."""

    id: uuid.UUID
    slug: str
    nombre: str
    descripcion: str | None
    estado: str = Field(description="borrador | publicado | suspendido")
    zona_horaria: str
    moneda: str
    direccion: str | None
    detalle_direccion: str | None
    longitud: float | None
    latitud: float | None
    zona_id: uuid.UUID | None
    zona_nombre: str | None
    categorias: list[str] = Field(description="Slugs de categorías globales de M2G")
    atributos: list[str] = Field(description="Slugs de valores de atributo (NEG-2)")
    instagram: str | None
    web: str | None
    #: **Nunca el número.** Solo si lo hay, para que el panel sepa si pintar «configurar
    #: WhatsApp» o «ya está puesto».
    tiene_whatsapp: bool
    fotos: list[FotoDelNegocio]


class CambioDeFicha(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    descripcion: str | None = Field(default=None, max_length=2000)
    direccion: str | None = Field(default=None, min_length=4, max_length=300)
    detalle_direccion: str | None = Field(default=None, max_length=300)
    longitud: float | None = Field(default=None, ge=-180, le=180)
    latitud: float | None = Field(default=None, ge=-90, le=90)
    #: La zona la **elige el dueño**: en Panamá los límites de corregimiento no coinciden con
    #: lo que la gente llama su barrio, y él sabe mejor dónde está su salón (MKT-6, ADR-0005).
    zona_id: uuid.UUID | None = None
    categorias: list[str] | None = None
    atributos: list[str] | None = None
    instagram: str | None = Field(default=None, max_length=60)
    web: str | None = Field(default=None, max_length=300)
    whatsapp: str | None = Field(
        default=None, description="En E.164. Se guarda y no se devuelve nunca (garantía nº 3)"
    )


class AltaDeFoto(BaseModel):
    #: La **clave** en el almacén, no una URL firmada: las URL caducan y guardarlas obligaría a
    #: reescribir filas. Admite también una ruta servible (`/fotos/spa.webp`) o una URL
    #: absoluta, y el serializador se encarga de componer la que se pinta.
    clave: str = Field(min_length=1, max_length=500)
    clase: str = Field(default="galeria", pattern="^(portada|galeria)$")
    texto_alternativo: str | None = Field(default=None, max_length=200)
    orden: int = Field(default=0, ge=0, le=99)


class GrupoDeAtributos(BaseModel):
    """Un grupo filtrable del catálogo global (NEG-2, ADM-4): «tipo de cabello», «pagos»."""

    slug: str
    nombre: str
    grupo: str
    seleccion: str = Field(description="unico | multiple | booleano")
    valores: list[dict[str, str]]


@router.get("/ficha", summary="El perfil público, para editarlo (NEG-1)")
async def leer_ficha(sesion_negocio: SesionNegocio) -> FichaDelNegocio:
    sesion, identidad = sesion_negocio
    return await _pintar_ficha(sesion, identidad.negocio_id)


@router.patch("/ficha", summary="Editar el perfil público (NEG-1, NEG-2, MKT-6)")
async def editar_ficha(cambio: CambioDeFicha, sesion_negocio: SesionNegocio) -> FichaDelNegocio:
    """Cambia lo que venga. **El slug no se toca desde aquí.**

    Cambiar el slug es cambiar una URL que ya circula por WhatsApp y está en la bio de
    Instagram; se hace con su redirección en `slug_redirects` y no como efecto colateral de
    corregir una tilde del nombre.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    negocio = await sesion.get(Business, identidad.negocio_id)
    if negocio is None:
        raise NoExiste("Ese negocio no existe.")

    for campo, columna in (
        ("nombre", "display_name"),
        ("descripcion", "description"),
        ("instagram", "instagram_handle"),
        ("web", "website_url"),
        ("whatsapp", "whatsapp_phone_e164"),
    ):
        valor = getattr(cambio, campo)
        if valor is not None:
            setattr(negocio, columna, valor)

    await _actualizar_ubicacion(sesion, identidad.negocio_id, cambio)

    if cambio.categorias is not None:
        await _reemplazar_categorias(sesion, identidad.negocio_id, cambio.categorias)
    if cambio.atributos is not None:
        await _reemplazar_atributos(sesion, identidad.negocio_id, cambio.atributos)

    await sesion.flush()
    return await _pintar_ficha(sesion, identidad.negocio_id)


@router.get("/atributos", summary="Catálogo de atributos filtrables (NEG-2, ADM-4)")
async def catalogo_de_atributos(sesion_negocio: SesionNegocio) -> list[GrupoDeAtributos]:
    """Los grupos y valores que M2G administra. **Son datos, no código**: añadir «atiende
    cabello afro» como filtro es una fila, no un despliegue."""
    sesion, _ = sesion_negocio

    grupos = (
        (
            await sesion.execute(
                select(Attribute)
                .where(Attribute.active.is_(True))
                .order_by(Attribute.position, Attribute.name)
            )
        )
        .scalars()
        .all()
    )
    valores: dict[uuid.UUID, list[AttributeValue]] = {}
    for valor in (
        (
            await sesion.execute(
                select(AttributeValue)
                .where(AttributeValue.active.is_(True))
                .order_by(AttributeValue.position, AttributeValue.name)
            )
        )
        .scalars()
        .all()
    ):
        valores.setdefault(valor.attribute_id, []).append(valor)

    return [
        GrupoDeAtributos(
            slug=grupo.slug,
            nombre=grupo.name,
            grupo=grupo.group_key,
            seleccion=grupo.input_kind,
            valores=[{"slug": v.slug, "nombre": v.name} for v in valores.get(grupo.id, [])],
        )
        for grupo in grupos
    ]


@router.get("/fotos", summary="Portada y galería (NEG-1, D11)")
async def listar_fotos(sesion_negocio: SesionNegocio) -> list[FotoDelNegocio]:
    sesion, identidad = sesion_negocio
    return await _fotos_de(sesion, identidad.negocio_id)


@router.post("/fotos", status_code=201, summary="Añadir una foto (NEG-1, D11)")
async def anadir_foto(alta: AltaDeFoto, sesion_negocio: SesionNegocio) -> FotoDelNegocio:
    """Registra la foto. **Una portada y solo una**: si ya había, la anterior pasa a galería.

    El único parcial de la base lo impediría de todos modos, pero con un error de integridad
    que no explica nada. Aquí se resuelve como espera quien lo hace: eliges otra portada y la
    de antes se queda en la galería, no desaparece.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)

    if alta.clase == "portada":
        anterior = (
            await sesion.execute(
                select(BusinessMedia).where(
                    BusinessMedia.business_id == identidad.negocio_id,
                    BusinessMedia.kind == "portada",
                )
            )
        ).scalar_one_or_none()
        if anterior is not None:
            anterior.kind = "galeria"
            await sesion.flush()

    foto = BusinessMedia(
        business_id=identidad.negocio_id,
        kind=alta.clase,
        storage_key=alta.clave,
        alt_text=alta.texto_alternativo,
        position=alta.orden,
    )
    sesion.add(foto)
    await sesion.flush()
    return _pintar_foto(foto)


@router.delete("/fotos/{foto_id}", status_code=204, summary="Quitar una foto (NEG-1)")
async def quitar_foto(foto_id: uuid.UUID, sesion_negocio: SesionNegocio) -> None:
    """Se borra de verdad: de una foto no cuelga nada y guardarla apagada solo ocupa sitio.

    Ojo con el efecto: quitar la última portada deja al negocio **por debajo del mínimo para
    publicar** (D11). El checklist lo dirá en la siguiente llamada; no se despublica solo,
    porque despublicar a alguien por borrar una foto sería una sorpresa muy cara.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    foto = (
        await sesion.execute(
            select(BusinessMedia).where(
                BusinessMedia.id == foto_id,
                BusinessMedia.business_id == identidad.negocio_id,
            )
        )
    ).scalar_one_or_none()
    if foto is None:
        raise NoExiste("Esa foto no existe en este negocio.")
    await sesion.delete(foto)
    await sesion.flush()


async def _actualizar_ubicacion(
    sesion: AsyncSession, negocio_id: uuid.UUID, cambio: CambioDeFicha
) -> None:
    """Dirección, pin y zona. El punto solo se mueve si vienen **las dos** coordenadas."""
    campos_de_ubicacion = (
        cambio.direccion,
        cambio.detalle_direccion,
        cambio.longitud,
        cambio.latitud,
        cambio.zona_id,
    )
    if all(valor is None for valor in campos_de_ubicacion):
        return

    ubicacion = (
        (await sesion.execute(select(Location).where(Location.business_id == negocio_id)))
        .scalars()
        .first()
    )
    if ubicacion is None:
        raise DatoInvalido("Este negocio todavía no tiene ubicación; créala en el alta.")

    if cambio.direccion is not None:
        ubicacion.address_line = cambio.direccion
    if cambio.detalle_direccion is not None:
        ubicacion.address_details = cambio.detalle_direccion
    if cambio.longitud is not None and cambio.latitud is not None:
        ubicacion.geo = f"SRID=4326;POINT({cambio.longitud} {cambio.latitud})"
    elif (cambio.longitud is None) != (cambio.latitud is None):
        raise DatoInvalido("Para mover el pin hacen falta longitud y latitud, no una sola.")

    if cambio.zona_id is not None:
        zona = await sesion.get(Zone, cambio.zona_id)
        if zona is None:
            raise DatoInvalido("Esa zona no existe en el catálogo.")
        ubicacion.zone_id = zona.id
        # Se marca como manual para que el trabajo que recalcula zonas **no pise la corrección
        # del dueño** la próxima vez que pase.
        ubicacion.zone_source = "manual"


async def _reemplazar_categorias(
    sesion: AsyncSession, negocio_id: uuid.UUID, slugs: list[str]
) -> None:
    """Se manda la lista entera, como las casillas de la pantalla."""
    if not slugs:
        raise DatoInvalido("Un negocio necesita al menos una categoría para aparecer en la lista.")

    encontradas = {
        slug: id_
        for id_, slug in (
            await sesion.execute(
                select(ServiceCategory.id, ServiceCategory.slug).where(
                    ServiceCategory.slug.in_(slugs)
                )
            )
        ).all()
    }
    faltan = [s for s in slugs if s not in encontradas]
    if faltan:
        raise DatoInvalido("Alguna categoría no existe en el catálogo.", categorias=faltan)

    await sesion.execute(delete(BusinessCategory).where(BusinessCategory.business_id == negocio_id))
    for posicion, slug in enumerate(dict.fromkeys(slugs)):
        sesion.add(
            BusinessCategory(
                business_id=negocio_id,
                service_category_id=encontradas[slug],
                # La primera es la principal: es la que manda en la página categoría × zona.
                is_primary=posicion == 0,
            )
        )


async def _reemplazar_atributos(
    sesion: AsyncSession, negocio_id: uuid.UUID, slugs: list[str]
) -> None:
    encontrados = {
        slug: id_
        for id_, slug in (
            await sesion.execute(
                select(AttributeValue.id, AttributeValue.slug).where(
                    AttributeValue.slug.in_(slugs), AttributeValue.active.is_(True)
                )
            )
        ).all()
    }
    faltan = [s for s in slugs if s not in encontrados]
    if faltan:
        raise DatoInvalido("Algún atributo no existe en el catálogo.", atributos=faltan)

    await sesion.execute(
        delete(BusinessAttribute).where(BusinessAttribute.business_id == negocio_id)
    )
    for slug in dict.fromkeys(slugs):
        sesion.add(BusinessAttribute(business_id=negocio_id, attribute_value_id=encontrados[slug]))


def _pintar_foto(foto: BusinessMedia) -> FotoDelNegocio:
    return FotoDelNegocio(
        id=foto.id,
        url=url_de_media(foto.storage_key) or "",
        clase=foto.kind,
        texto_alternativo=foto.alt_text,
        orden=foto.position,
        moderacion=foto.moderation_status,
    )


async def _fotos_de(sesion: AsyncSession, negocio_id: uuid.UUID) -> list[FotoDelNegocio]:
    filas = (
        (
            await sesion.execute(
                select(BusinessMedia)
                .where(BusinessMedia.business_id == negocio_id)
                # La portada primero: es la que se pinta grande y la que decide si alguien
                # entra. `kind` ordena al revés alfabéticamente, de ahí el `desc()`.
                .order_by(BusinessMedia.kind.desc(), BusinessMedia.position, BusinessMedia.id)
            )
        )
        .scalars()
        .all()
    )
    return [_pintar_foto(f) for f in filas]


async def _pintar_ficha(sesion: AsyncSession, negocio_id: uuid.UUID) -> FichaDelNegocio:
    negocio = await sesion.get(Business, negocio_id)
    if negocio is None:
        raise NoExiste("Ese negocio no existe.")

    ubicacion = (
        (await sesion.execute(select(Location).where(Location.business_id == negocio_id)))
        .scalars()
        .first()
    )
    zona = await sesion.get(Zone, ubicacion.zone_id) if ubicacion and ubicacion.zone_id else None

    longitud = latitud = None
    if ubicacion is not None:
        # El pin se devuelve para poder pintarlo en el mapa del panel. Se saca con `ST_X`/
        # `ST_Y` de PostGIS y no deserializando el WKB en Python: es una consulta más y una
        # dependencia menos, y la dependencia de menos es la que no se rompe al subir de
        # versión. El `cast` a `geometry` es obligatorio — sobre `geography` esas dos
        # funciones no existen.
        punto = Location.geo.cast(Geometry())
        longitud, latitud = (
            await sesion.execute(
                select(func.ST_X(punto), func.ST_Y(punto)).where(Location.id == ubicacion.id)
            )
        ).one()

    categorias = (
        (
            await sesion.execute(
                select(ServiceCategory.slug)
                .join(
                    BusinessCategory,
                    BusinessCategory.service_category_id == ServiceCategory.id,
                )
                .where(BusinessCategory.business_id == negocio_id)
                .order_by(BusinessCategory.is_primary.desc(), ServiceCategory.name)
            )
        )
        .scalars()
        .all()
    )
    atributos = (
        (
            await sesion.execute(
                select(AttributeValue.slug)
                .join(
                    BusinessAttribute,
                    BusinessAttribute.attribute_value_id == AttributeValue.id,
                )
                .where(BusinessAttribute.business_id == negocio_id)
                .order_by(AttributeValue.slug)
            )
        )
        .scalars()
        .all()
    )

    return FichaDelNegocio(
        id=negocio.id,
        slug=negocio.slug,
        nombre=negocio.display_name,
        descripcion=negocio.description,
        estado=negocio.status,
        zona_horaria=negocio.timezone,
        moneda=negocio.currency,
        direccion=ubicacion.address_line if ubicacion else None,
        detalle_direccion=ubicacion.address_details if ubicacion else None,
        longitud=longitud,
        latitud=latitud,
        zona_id=zona.id if zona else None,
        zona_nombre=zona.name if zona else None,
        categorias=list(categorias),
        atributos=list(atributos),
        instagram=negocio.instagram_handle,
        web=negocio.website_url,
        tiene_whatsapp=bool(negocio.whatsapp_phone_e164),
        fotos=await _fotos_de(sesion, negocio_id),
    )
