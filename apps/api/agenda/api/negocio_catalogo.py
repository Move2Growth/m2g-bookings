"""El catálogo del salón: servicios y variantes (SRV-1 a SRV-4).

Hasta ahora un servicio solo se podía **crear**. Un salón real cambia de precio en temporada,
deja de hacer un tratamiento y reordena la carta cada pocas semanas; sin listar, editar ni
desactivar, el panel obliga a llamar a alguien de M2G, que es exactamente lo que ONB-2 promete
que no hará falta.

Dos reglas que se ven en las firmas y no son de estilo:

* **Desactivar no es borrar.** Un servicio con citas pasadas detrás no se puede destruir sin
  destruir la contabilidad del salón, así que `DELETE` marca `deleted_at` y `active = false`.
  La cita de la semana pasada sigue diciendo qué se hizo y cuánto costó, porque el precio y la
  duración están copiados en `booking_items`.
* **Cambiar el buffer no reescribe lo ya reservado.** Es consecuencia declarada de ADR-0004 y
  aquí no se toca: la ocupación se queda con la copia que tenía.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.api.comunes import url_de_media
from agenda.api.dependencias import SesionNegocio, SesionPublica, exigir_dueno
from agenda.errores import DatoInvalido, NoExiste
from agenda.modelos.catalogo import Service, ServiceCategory, ServiceVariant
from agenda.modelos.equipo import StaffService

router = APIRouter(prefix="/api/v1", tags=["catálogo del negocio"])


class CategoriaGlobal(BaseModel):
    """Una categoría del catálogo de M2G (SRV-4). **La administra M2G, no el negocio.**"""

    id: uuid.UUID
    slug: str
    nombre: str
    padre_slug: str | None = None


class VarianteDeServicio(BaseModel):
    id: uuid.UUID
    nombre: str
    duracion_minutos: int
    precio_centavos: int | None
    tipo_de_precio: str
    activa: bool


class ServicioDelPanel(BaseModel):
    """Un servicio visto **desde dentro**: lleva lo que el dueño edita, incluidos los buffers."""

    id: uuid.UUID
    nombre: str
    descripcion: str | None
    categoria_slug: str
    categoria_nombre: str
    duracion_minutos: int
    precio_centavos: int | None
    tipo_de_precio: str = Field(description="fijo | desde | consultar")
    moneda: str
    buffer_antes_min: int
    buffer_despues_min: int
    foto: str | None
    activo: bool
    orden: int
    #: Cuántos profesionales lo prestan. Un servicio que no presta nadie **no se puede
    #: reservar** (STF-1), y sin este número el dueño no tiene forma de enterarse hasta que
    #: alguien se queja de que su servicio estrella no aparece.
    profesionales: int
    variantes: list[VarianteDeServicio]


class CambioDeServicio(BaseModel):
    """Todo opcional: se manda lo que cambia. Lo que no viene, no se toca.

    Es un `PATCH` de verdad y no un `PUT` disfrazado: el panel se usa en un teléfono entre
    cliente y cliente, y obligar a reenviar el objeto entero para subir un precio es la forma
    de que un campo se pierda por el camino.
    """

    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    descripcion: str | None = None
    categoria: str | None = None
    duracion_minutos: int | None = Field(default=None, gt=0, le=8 * 60)
    precio_centavos: int | None = Field(default=None, ge=0)
    tipo_de_precio: str | None = Field(default=None, pattern="^(fijo|desde|consultar)$")
    buffer_antes_min: int | None = Field(default=None, ge=0, le=120)
    buffer_despues_min: int | None = Field(default=None, ge=0, le=120)
    foto: str | None = None
    activo: bool | None = None
    orden: int | None = Field(default=None, ge=0, le=999)


class AltaDeVariante(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    duracion_minutos: int = Field(gt=0, le=8 * 60)
    precio_centavos: int | None = Field(default=None, ge=0)
    tipo_de_precio: str = Field(default="fijo", pattern="^(fijo|desde|consultar)$")


@router.get("/catalogo/categorias", summary="Categorías globales de M2G (SRV-4)")
async def categorias(sesion: SesionPublica) -> list[CategoriaGlobal]:
    """Público y cacheable: lo usan el alta del negocio y los filtros del marketplace.

    Sale por la sesión pública a propósito. Es un catálogo global sin nada de nadie dentro, y
    servirlo con el rol del negocio obligaría a tener sesión para pintar el buscador.
    """
    filas = (
        (
            await sesion.execute(
                select(ServiceCategory)
                .where(ServiceCategory.active.is_(True))
                .order_by(ServiceCategory.position, ServiceCategory.name)
            )
        )
        .scalars()
        .all()
    )
    por_id = {fila.id: fila for fila in filas}
    return [
        CategoriaGlobal(
            id=fila.id,
            slug=fila.slug,
            nombre=fila.name,
            padre_slug=por_id[fila.parent_id].slug if fila.parent_id in por_id else None,
        )
        for fila in filas
    ]


@router.get("/negocio/servicios", summary="La carta del salón (SRV-1)")
async def listar_servicios(
    sesion_negocio: SesionNegocio,
    incluir_inactivos: Annotated[bool, Query(description="Los desactivados también")] = True,
) -> list[ServicioDelPanel]:
    """Los servicios del negocio activo, en el orden en que el dueño los colocó.

    Los inactivos vienen por defecto: el panel los pinta apagados para poder reactivarlos, y
    esconderlos haría creer que se borraron.
    """
    sesion, identidad = sesion_negocio

    consulta = (
        select(Service)
        .where(Service.business_id == identidad.negocio_id, Service.deleted_at.is_(None))
        .order_by(Service.position, Service.name)
    )
    if not incluir_inactivos:
        consulta = consulta.where(Service.active.is_(True))

    servicios = (await sesion.execute(consulta)).scalars().all()
    return await _pintar_servicios(sesion, identidad.negocio_id, servicios)


@router.patch("/negocio/servicios/{servicio_id}", summary="Editar un servicio (SRV-1)")
async def editar_servicio(
    servicio_id: uuid.UUID, cambio: CambioDeServicio, sesion_negocio: SesionNegocio
) -> ServicioDelPanel:
    """Cambia lo que venga. **No reescribe las citas ya creadas** (ADR-0004).

    El catálogo es del dueño (STF-3). La política restrictiva de la migración 0006 ya lo
    impediría, pero se comprueba además aquí para poder decirlo con una frase: sin esto, el
    profesional recibiría un error de escritura sin efecto en vez de un «no te toca».
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    servicio = await _servicio_del_negocio(sesion, identidad.negocio_id, servicio_id)

    if cambio.categoria is not None:
        servicio.service_category_id = await _categoria_por_slug(sesion, cambio.categoria)

    for campo, columna in (
        ("nombre", "name"),
        ("descripcion", "description"),
        ("duracion_minutos", "duration_min"),
        ("tipo_de_precio", "price_kind"),
        ("buffer_antes_min", "buffer_before_min"),
        ("buffer_despues_min", "buffer_after_min"),
        ("foto", "photo_key"),
        ("activo", "active"),
        ("orden", "position"),
    ):
        valor = getattr(cambio, campo)
        if valor is not None:
            setattr(servicio, columna, valor)

    # El precio se trata aparte porque `None` significa dos cosas distintas: «no lo cambies»
    # (no vino en el cuerpo) y «no tiene precio» (a consultar). Se distingue mirando si el
    # campo estaba presente, no si vale `None`.
    enviados = cambio.model_dump(exclude_unset=True)
    if "precio_centavos" in enviados:
        servicio.price_minor = enviados["precio_centavos"]

    # La misma regla que la restricción de la base, comprobada antes para poder explicarla:
    # «desde $120» tiene precio mínimo; «a consultar» no tiene ninguno. Dejarlo a la base daría
    # un error de integridad ilegible en vez de una frase.
    if servicio.price_kind != "consultar" and servicio.price_minor is None:
        raise DatoInvalido(
            "Un servicio con precio fijo o «desde» necesita un importe. "
            "Si todavía no lo sabes, ponlo «a consultar»."
        )
    if servicio.price_kind == "consultar":
        servicio.price_minor = None

    await sesion.flush()
    return (await _pintar_servicios(sesion, identidad.negocio_id, [servicio]))[0]


@router.delete("/negocio/servicios/{servicio_id}", summary="Retirar un servicio (SRV-1)")
async def retirar_servicio(
    servicio_id: uuid.UUID, sesion_negocio: SesionNegocio
) -> ServicioDelPanel:
    """Lo retira de la carta **sin destruir el historial**.

    Es borrado lógico y no físico, y no es prudencia: las citas pasadas apuntan a este servicio
    con `RESTRICT`, así que un `DELETE` de verdad fallaría en cuanto el salón llevara un día
    trabajando. El servicio deja de ofrecerse y de poder reservarse; lo que ya pasó sigue
    contado.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    servicio = await _servicio_del_negocio(sesion, identidad.negocio_id, servicio_id)

    servicio.active = False
    servicio.deleted_at = datetime.now(UTC)
    await sesion.flush()
    return (await _pintar_servicios(sesion, identidad.negocio_id, [servicio]))[0]


@router.post(
    "/negocio/servicios/{servicio_id}/variantes",
    status_code=201,
    summary="Añadir una variante (SRV-2)",
)
async def crear_variante(
    servicio_id: uuid.UUID, alta: AltaDeVariante, sesion_negocio: SesionNegocio
) -> VarianteDeServicio:
    """«Cabello largo», «con mechas»: misma silla, otra duración y otro precio."""
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    servicio = await _servicio_del_negocio(sesion, identidad.negocio_id, servicio_id)

    if alta.tipo_de_precio != "consultar" and alta.precio_centavos is None:
        raise DatoInvalido("Una variante con precio fijo o «desde» necesita un importe.")

    variante = ServiceVariant(
        business_id=identidad.negocio_id,
        service_id=servicio.id,
        name=alta.nombre,
        duration_min=alta.duracion_minutos,
        price_kind=alta.tipo_de_precio,
        price_minor=None if alta.tipo_de_precio == "consultar" else alta.precio_centavos,
    )
    sesion.add(variante)
    await sesion.flush()
    return _pintar_variante(variante)


@router.delete(
    "/negocio/servicios/{servicio_id}/variantes/{variante_id}",
    status_code=204,
    summary="Quitar una variante (SRV-2)",
)
async def borrar_variante(
    servicio_id: uuid.UUID, variante_id: uuid.UUID, sesion_negocio: SesionNegocio
) -> None:
    """Aquí sí se borra de verdad: las citas guardan su propia copia del nombre y del precio.

    `booking_items` apunta a la variante con `RESTRICT`, así que si alguna cita la usó, la base
    lo impide y se traduce a desactivarla.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    variante = (
        await sesion.execute(
            select(ServiceVariant).where(
                ServiceVariant.id == variante_id,
                ServiceVariant.service_id == servicio_id,
                ServiceVariant.business_id == identidad.negocio_id,
            )
        )
    ).scalar_one_or_none()
    if variante is None:
        raise NoExiste("Esa variante no existe en este servicio.")

    variante.active = False
    await sesion.flush()


async def _servicio_del_negocio(
    sesion: AsyncSession, negocio_id: uuid.UUID, servicio_id: uuid.UUID
) -> Service:
    """El aislamiento por fila ya lo escondería; el filtro explícito lo convierte en un 404."""
    servicio = (
        await sesion.execute(
            select(Service).where(
                Service.id == servicio_id,
                Service.business_id == negocio_id,
                Service.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if servicio is None:
        raise NoExiste("Ese servicio no existe en este negocio.")
    return servicio


async def _categoria_por_slug(sesion: AsyncSession, slug: str) -> uuid.UUID:
    categoria = (
        await sesion.execute(select(ServiceCategory.id).where(ServiceCategory.slug == slug))
    ).scalar_one_or_none()
    if categoria is None:
        raise DatoInvalido(f"La categoría «{slug}» no existe en el catálogo de M2G.")
    return categoria


def _pintar_variante(variante: ServiceVariant) -> VarianteDeServicio:
    return VarianteDeServicio(
        id=variante.id,
        nombre=variante.name,
        duracion_minutos=variante.duration_min,
        precio_centavos=variante.price_minor,
        tipo_de_precio=variante.price_kind,
        activa=variante.active,
    )


async def _pintar_servicios(
    sesion: AsyncSession, negocio_id: uuid.UUID, servicios: list[Service]
) -> list[ServicioDelPanel]:
    """Serializador **de panel**. Tres consultas para toda la lista, no tres por servicio."""
    if not servicios:
        return []
    ids = [s.id for s in servicios]

    categorias = {
        fila.id: fila
        for fila in (
            (
                await sesion.execute(
                    select(ServiceCategory).where(
                        ServiceCategory.id.in_({s.service_category_id for s in servicios})
                    )
                )
            )
            .scalars()
            .all()
        )
    }
    cuantos = dict(
        (
            await sesion.execute(
                select(StaffService.service_id, func.count())
                .where(
                    StaffService.business_id == negocio_id,
                    StaffService.service_id.in_(ids),
                )
                .group_by(StaffService.service_id)
            )
        ).all()
    )
    variantes: dict[uuid.UUID, list[ServiceVariant]] = {}
    for fila in (
        (
            await sesion.execute(
                select(ServiceVariant)
                .where(
                    ServiceVariant.business_id == negocio_id,
                    ServiceVariant.service_id.in_(ids),
                )
                .order_by(ServiceVariant.position, ServiceVariant.name)
            )
        )
        .scalars()
        .all()
    ):
        variantes.setdefault(fila.service_id, []).append(fila)

    return [
        ServicioDelPanel(
            id=s.id,
            nombre=s.name,
            descripcion=s.description,
            categoria_slug=categorias[s.service_category_id].slug,
            categoria_nombre=categorias[s.service_category_id].name,
            duracion_minutos=s.duration_min,
            precio_centavos=s.price_minor,
            tipo_de_precio=s.price_kind,
            moneda=s.currency,
            buffer_antes_min=s.buffer_before_min,
            buffer_despues_min=s.buffer_after_min,
            foto=url_de_media(s.photo_key),
            activo=s.active,
            orden=s.position,
            profesionales=cuantos.get(s.id, 0),
            variantes=[_pintar_variante(v) for v in variantes.get(s.id, [])],
        )
        for s in servicios
    ]
