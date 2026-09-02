"""Dar de alta un negocio y dejarlo operativo: servicios, equipo, horario y publicación.

El objetivo de ONB-2 es exigente y conviene tenerlo delante: **operativo en menos de diez
minutos desde el móvil, sin intervención de M2G y sin tarjeta**. Eso manda sobre el diseño de
estos endpoints — cada uno hace una cosa y ninguno pide nada que no sea imprescindible para el
paso en el que estás.

La suscripción se crea con el negocio aunque el plan cueste 0 (ADR-0010). No es papeleo: es lo
que permite que el día que el precio pase a un dólar el camino ya esté recorrido.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from datetime import UTC, datetime, time
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from agenda.api.dependencias import (
    Identidad,
    SesionNegocio,
    SesionPlataforma,
    exigir_dueno,
    identidad_actual,
)
from agenda.errores import FaltaMinimoParaPublicar, NoAutorizado
from agenda.modelos.base import nuevo_id
from agenda.modelos.catalogo import Service, ServiceCategory
from agenda.modelos.equipo import StaffHours, StaffProfile, StaffService
from agenda.modelos.identidad import Membership
from agenda.modelos.negocio import (
    Business,
    BusinessHours,
    BusinessMedia,
    BusinessSettings,
    Location,
)

router = APIRouter(prefix="/api/v1", tags=["alta de negocio"])

#: Palabras que **no** puede quedarse un salón, porque son rutas del producto. El perfil vive en
#: la raíz (`bukeo.com/barberia-el-cangrejo`) para que quepa en una bio de Instagram, y ese
#: acierto tiene un filo: un negocio llamado «Entrar» se llevaría la página de acceso.
SLUGS_RESERVADOS = frozenset(
    {
        "buscar",
        "entrar",
        "salir",
        "registro",
        "reservar",
        "panel",
        "mis-reservas",
        "mis-citas",
        "para-negocios",
        "precios",
        "ayuda",
        "legal",
        "privacidad",
        "terminos",
        "cookies",
        "contacto",
        "blog",
        "api",
        "admin",
        "app",
        "cuenta",
        "ajustes",
        "negocio",
        "negocios",
        "zonas",
        "categorias",
        "acerca",
        "prensa",
        "estilo",
        "sitemap",
        "robots",
        "favicon",
        "bukeo",
        "www",
    }
)


def _slug(nombre: str) -> str:
    """URL amigable a partir del nombre (NEG-4). Se puede cambiar después.

    Las tildes y la eñe **se transliteran**, no se tiran: «Barbería La Cresta» tiene que dar
    `barberia-la-cresta` y no `barber-a-la-cresta`. Es una URL pública que se comparte por
    WhatsApp y se pone en la bio de Instagram; que salga rota es una primera impresión mala y
    permanente.
    """
    sin_tildes = (
        unicodedata.normalize("NFKD", nombre.replace("ñ", "n").replace("Ñ", "N"))
        .encode("ascii", "ignore")
        .decode()
    )
    limpio = re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower().strip())
    return re.sub(r"-+", "-", limpio).strip("-") or "negocio"


class AltaDeNegocio(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    categoria: str = Field(description="Slug de una categoría global, por ejemplo «barberia»")
    direccion: str
    longitud: float
    latitud: float
    zona_horaria: str = "America/Panama"


class NegocioCreado(BaseModel):
    id: uuid.UUID
    slug: str
    estado: str


class HorarioDelDia(BaseModel):
    dia: int = Field(ge=0, le=6, description="0 = lunes … 6 = domingo")
    abre: time
    cierra: time


class AltaDeServicio(BaseModel):
    nombre: str
    categoria: str
    duracion_minutos: int = Field(gt=0, le=8 * 60)
    precio_centavos: int | None = None
    tipo_de_precio: str = Field(default="fijo", pattern="^(fijo|desde|consultar)$")
    buffer_antes_min: int = Field(default=0, ge=0, le=120)
    buffer_despues_min: int = Field(default=0, ge=0, le=120)


class AltaDeProfesional(BaseModel):
    nombre: str
    #: El profesional «sin cuenta» es el caso normal al empezar (ONB-4): el dueño apunta a su
    #: barbero y ya puede agendarle citas; la invitación llega después, si llega.
    telefono: str | None = None
    horario: list[HorarioDelDia] = Field(default_factory=list)
    servicios: list[uuid.UUID] = Field(default_factory=list)


class EstadoDelChecklist(BaseModel):
    """Qué falta para publicar (ONB-7). El mínimo lo fija D11 y no se negocia."""

    tiene_servicio_activo: bool
    tiene_horario: bool
    tiene_ubicacion: bool
    tiene_foto: bool
    listo_para_publicar: bool
    completitud: float = Field(description="0 a 1, lo que alimenta el ranking")


@router.post("/negocios", status_code=201, summary="Alta self-service de un negocio (ONB-2)")
async def crear_negocio(
    alta: AltaDeNegocio,
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> NegocioCreado:
    """Crea el negocio, la membresía de dueño y sus ajustes. **Sin tarjeta y sin esperar a nadie.**

    Nace en `borrador`: solo se publica cuando cumple el mínimo (D11), y publicar es un paso
    aparte y explícito. Un negocio a medias en el marketplace es peor que uno que no está.
    """
    categoria = (
        await sesion.execute(select(ServiceCategory).where(ServiceCategory.slug == alta.categoria))
    ).scalar_one_or_none()
    if categoria is None:
        raise NoAutorizado("Esa categoría no existe.")

    # El slug es una URL pública y si choca hay que desempatarlo, pero **no se puede comprobar
    # antes preguntando**: el aislamiento por fila esconde los negocios ajenos, así que la
    # consulta diría siempre «está libre» y la inserción fallaría contra el índice único.
    # Se hace al revés: se intenta, y si la base dice que está cogido, se reintenta con sufijo.
    # De paso queda a prueba de dos altas simultáneas con el mismo nombre, que una comprobación
    # previa tampoco resolvería.
    base = _slug(alta.nombre)
    # Si el nombre del salón choca con una ruta del producto, se le añade un sufijo en vez de
    # rechazar el alta: quien se llama «Ayuda Beauty Salon» no tiene por qué enterarse de la
    # arquitectura de URL de nadie.
    if base in SLUGS_RESERVADOS:
        base = f"{base}-salon"
    slug = base

    # Otra vez el huevo y la gallina del aislamiento: la política de `businesses` exige que la
    # fila que insertas sea la del negocio activo, y todavía no hay negocio activo porque lo
    # estás creando. Se resuelve **generando el identificador aquí** y declarándolo como tenant
    # antes de insertar: así solo puedes crear la fila cuyo identificador acabas de declarar.
    # Declarar un tenant no da acceso a nada por sí solo; lo que autoriza sigue siendo la
    # membresía, que se crea justo después.
    negocio_id = nuevo_id()
    await sesion.execute(
        text("SELECT set_config('app.current_business_id', :negocio, true)"),
        {"negocio": str(negocio_id)},
    )

    # Se inserta con `ON CONFLICT DO NOTHING` y se mira si entró: si el slug estaba cogido, no
    # se lanza excepción, no se ensucia la sesión y se vuelve a intentar con un sufijo. Dejar
    # que salte la excepción dentro de una sesión con más trabajo pendiente obliga a deshacerlo
    # todo, y aquí lo que queremos deshacer es una línea, no el alta entera.
    for intento in range(5):
        insertado = (
            await sesion.execute(
                pg_insert(Business.__table__)
                .values(
                    id=negocio_id,
                    slug=slug,
                    display_name=alta.nombre,
                    owner_user_id=identidad.usuario_id,
                    timezone=alta.zona_horaria,
                    status="borrador",
                )
                .on_conflict_do_nothing(index_elements=["slug"])
                .returning(Business.__table__.c.id)
            )
        ).scalar_one_or_none()

        if insertado is not None:
            break
        slug = f"{base}-{uuid.uuid4().hex[:4]}"
        if intento == 4:
            raise NoAutorizado("No pudimos crear la dirección web del negocio. Prueba otro nombre.")

    negocio = await sesion.get(Business, negocio_id)

    sesion.add(
        Membership(
            business_id=negocio.id,
            user_id=identidad.usuario_id,
            role="dueno",
            status="activa",
            accepted_at=datetime.now(UTC),
        )
    )
    sesion.add(BusinessSettings(business_id=negocio.id))
    sesion.add(
        Location(
            business_id=negocio.id,
            address_line=alta.direccion,
            geo=f"SRID=4326;POINT({alta.longitud} {alta.latitud})",
        )
    )
    await sesion.flush()

    return NegocioCreado(id=negocio.id, slug=negocio.slug, estado=negocio.status)


@router.put("/negocio/horario", summary="Horario semanal del negocio (ONB-2)")
async def poner_horario(
    horario: list[HorarioDelDia], sesion_negocio: SesionNegocio
) -> list[HorarioDelDia]:
    """Reemplaza el horario entero.

    **No borra ni cancela las citas que queden fuera** del horario nuevo (caso 4 del motor):
    el negocio decide qué hacer con ellas. Que un cambio de horario cancelara citas en silencio
    sería la peor sorpresa posible un lunes por la mañana.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)

    anteriores = (
        (
            await sesion.execute(
                select(BusinessHours).where(BusinessHours.business_id == identidad.negocio_id)
            )
        )
        .scalars()
        .all()
    )
    for fila in anteriores:
        await sesion.delete(fila)

    for tramo in horario:
        sesion.add(
            BusinessHours(
                business_id=identidad.negocio_id,
                weekday=tramo.dia,
                opens_at=tramo.abre,
                closes_at=tramo.cierra,
            )
        )
    await sesion.flush()
    return horario


@router.post("/negocio/servicios", status_code=201, summary="Añadir un servicio (SRV-1)")
async def crear_servicio(alta: AltaDeServicio, sesion_negocio: SesionNegocio) -> uuid.UUID:
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)

    categoria = (
        await sesion.execute(select(ServiceCategory).where(ServiceCategory.slug == alta.categoria))
    ).scalar_one_or_none()
    if categoria is None:
        raise NoAutorizado("Esa categoría no existe.")

    servicio = Service(
        business_id=identidad.negocio_id,
        service_category_id=categoria.id,
        name=alta.nombre,
        duration_min=alta.duracion_minutos,
        price_kind=alta.tipo_de_precio,
        price_minor=alta.precio_centavos,
        buffer_before_min=alta.buffer_antes_min,
        buffer_after_min=alta.buffer_despues_min,
    )
    sesion.add(servicio)
    await sesion.flush()
    return servicio.id


@router.post("/negocio/profesionales", status_code=201, summary="Añadir un profesional (STF-1)")
async def crear_profesional(alta: AltaDeProfesional, sesion_negocio: SesionNegocio) -> uuid.UUID:
    """El profesional **sin cuenta** es el caso normal al empezar (ONB-4).

    El dueño apunta a su barbero y ya puede agendarle citas esa misma tarde; la invitación
    llega después. Exigir que cada persona se registre antes de poder agendarle sería pedirle
    al salón que espere a que su equipo tenga tiempo.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)

    profesional = StaffProfile(business_id=identidad.negocio_id, display_name=alta.nombre)
    sesion.add(profesional)
    await sesion.flush()

    for tramo in alta.horario:
        sesion.add(
            StaffHours(
                business_id=identidad.negocio_id,
                staff_id=profesional.id,
                weekday=tramo.dia,
                starts_at=tramo.abre,
                ends_at=tramo.cierra,
                kind="trabajo",
            )
        )
    for servicio_id in alta.servicios:
        sesion.add(
            StaffService(
                business_id=identidad.negocio_id,
                staff_id=profesional.id,
                service_id=servicio_id,
            )
        )
    await sesion.flush()
    return profesional.id


@router.get("/negocio/checklist", summary="Qué falta para publicar (ONB-7, D11)")
async def checklist(sesion_negocio: SesionNegocio) -> EstadoDelChecklist:
    sesion, identidad = sesion_negocio
    return await _estado_del_checklist(sesion, identidad.negocio_id)


@router.post("/negocio/publicar", summary="Publicar en el marketplace (ONB-6, D11)")
async def publicar(sesion_negocio: SesionNegocio) -> NegocioCreado:
    """Publica **solo si cumple el mínimo**: un servicio activo, horario, ubicación y una foto.

    El error dice qué falta, no «no se pudo publicar». Una puerta que no explica por qué está
    cerrada es una puerta que la gente aporrea.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)

    estado = await _estado_del_checklist(sesion, identidad.negocio_id)
    if not estado.listo_para_publicar:
        faltan = [
            nombre
            for nombre, cumplido in (
                ("un servicio activo", estado.tiene_servicio_activo),
                ("el horario", estado.tiene_horario),
                ("la ubicación", estado.tiene_ubicacion),
                ("una foto", estado.tiene_foto),
            )
            if not cumplido
        ]
        raise FaltaMinimoParaPublicar(f"Para publicar falta {', '.join(faltan)}.", faltan=faltan)

    negocio = await sesion.get(Business, identidad.negocio_id)
    negocio.status = "publicado"
    negocio.published_at = datetime.now(UTC)
    await sesion.flush()

    return NegocioCreado(id=negocio.id, slug=negocio.slug, estado=negocio.status)


async def _estado_del_checklist(sesion, negocio_id: uuid.UUID) -> EstadoDelChecklist:
    async def hay(modelo, *condiciones) -> bool:
        total = (
            await sesion.execute(
                select(func.count())
                .select_from(modelo)
                .where(modelo.business_id == negocio_id, *condiciones)
            )
        ).scalar_one()
        return total > 0

    servicio = await hay(Service, Service.active.is_(True), Service.deleted_at.is_(None))
    horario = await hay(BusinessHours)
    ubicacion = await hay(Location)
    foto = await hay(BusinessMedia)

    cumplidos = [servicio, horario, ubicacion, foto]
    return EstadoDelChecklist(
        tiene_servicio_activo=servicio,
        tiene_horario=horario,
        tiene_ubicacion=ubicacion,
        tiene_foto=foto,
        listo_para_publicar=all(cumplidos),
        completitud=sum(1 for c in cumplidos if c) / len(cumplidos),
    )
