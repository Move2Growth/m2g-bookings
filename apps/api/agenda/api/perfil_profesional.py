"""El panel del profesional: su perfil público y sus fotos.

Dos audiencias, un solo módulo, y a propósito: son las mismas reglas vistas desde dos sitios.

* `/mi/perfil-profesional…` es **la persona editando lo suyo**. No lleva ni un `if` de
  permisos y esa es la parte importante: quién puede escribir qué fila lo decide PostgreSQL
  con la política restrictiva de la migración 0009. Un endpoint nuevo que se olvide de mirar
  el rol **sigue** sin poder tocar la ficha de la compañera.
* `/negocio/profesionales/{id}/fotos…` es **el dueño gestionando el equipo**, que es cosa suya
  (STF-3), y por eso ese lado sí exige dueño explícitamente.

Lo que **no** puede cambiar el profesional de su propia ficha son `activo`, `visible en el
marketplace` y el orden en la lista: eso es del dueño. La base no sabe distinguir columnas
dentro de una fila para un mismo rol, así que ahí protege el código — y por eso el modelo de
entrada de este módulo sencillamente no tiene esos campos, en vez de tenerlos y descartarlos.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.api.comunes import url_de_media
from agenda.api.dependencias import Identidad, SesionNegocio, exigir_dueno
from agenda.dominio.textos import TextoInvalido, url_de_red, usuario_de_red
from agenda.errores import DatoInvalido, NoAutorizado, NoExiste
from agenda.modelos.catalogo import Service
from agenda.modelos.equipo import StaffMedia, StaffProfile
from agenda.servicios import profesionales as servicio_profesionales

router = APIRouter(prefix="/api/v1", tags=["perfil del profesional"])


class MiPerfilProfesional(BaseModel):
    """La ficha pública de una persona, tal y como la ve quien la edita."""

    id: uuid.UUID
    slug: str | None
    nombre: str
    titular: str | None = Field(default=None, description="La descripción de una línea")
    descripcion: str | None = Field(default=None, description="La bio larga")
    foto: str | None
    anos_de_experiencia: int | None
    instagram: str | None
    instagram_url: str | None
    facebook: str | None
    facebook_url: str | None
    x: str | None
    x_url: str | None
    #: Lo que sale en su perfil público y no se puede tocar desde aquí: lo calcula el servidor.
    citas_atendidas: int = 0
    clientes_atendidos: int = 0
    #: Del dueño, no suyas. Se devuelven para que la pantalla pueda explicar por qué no sale.
    activo: bool
    visible_en_marketplace: bool


class CambioDeMiPerfil(BaseModel):
    """Lo que una persona puede cambiar de su propia ficha. **Ni `activo` ni `visible`.**

    Los campos que no se mandan no se tocan; mandar `null` en una red **la borra**, que es la
    forma en que alguien quita un enlace que ya no quiere.
    """

    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    titular: str | None = Field(default=None, max_length=140)
    descripcion: str | None = None
    foto: str | None = None
    anos_de_experiencia: int | None = Field(default=None, ge=0, le=80)
    instagram: str | None = None
    facebook: str | None = None
    x: str | None = None

    #: Qué campos vinieron de verdad en el cuerpo. Sin esto no hay forma de distinguir «no
    #: mando instagram» de «bórrame el instagram», y las dos son peticiones legítimas.
    model_config = {"extra": "forbid"}


class FotoDelPortafolio(BaseModel):
    id: uuid.UUID
    url: str
    descripcion: str | None = None
    servicio_id: uuid.UUID | None = None
    posicion: int = 0
    moderacion: str = Field(description="pendiente | aprobada | rechazada")


class NuevaFoto(BaseModel):
    """Se recibe **una clave**, no un fichero.

    Es la misma limitación que tiene `POST /negocio/fotos` y por el mismo motivo: sin
    almacenamiento de objetos decidido, un endpoint de subida sería prometer algo que no
    funciona. Hoy la clave es una ruta servible o una URL absoluta; el día que haya
    almacenamiento, cambia lo que la rellena y no esta tabla.
    """

    clave: str = Field(min_length=1, max_length=500)
    descripcion: str | None = Field(default=None, max_length=200)
    #: Atarla a un servicio del salón es lo que la convierte en «esto lo hizo esta persona».
    #: Sin servicio, es galería.
    servicio_id: uuid.UUID | None = None
    posicion: int = Field(default=0, ge=0, le=999)


class CambioDeFoto(BaseModel):
    """Reasignar una foto a otro servicio, quitarle el servicio o moverla de sitio."""

    descripcion: str | None = None
    servicio_id: uuid.UUID | None = None
    posicion: int | None = Field(default=None, ge=0, le=999)
    quitar_servicio: bool = Field(
        default=False,
        description="Devuelve la foto a la galería. Va aparte porque `servicio_id: null` "
        "significa «no lo cambies», no «quítalo»",
    )


# ── La persona, sobre lo suyo ─────────────────────────────────────────────────────────────


@router.get("/mi/perfil-profesional", summary="Mi ficha pública (encargo 2026-09-07 §3)")
async def leer_mi_perfil(sesion_negocio: SesionNegocio) -> MiPerfilProfesional:
    sesion, identidad = sesion_negocio
    ficha = await _mi_ficha(sesion, identidad)
    return await _pintar(sesion, identidad.negocio_id, ficha)


@router.patch("/mi/perfil-profesional", summary="Editar mi ficha (encargo 2026-09-07 §3)")
async def editar_mi_perfil(
    cambio: CambioDeMiPerfil, sesion_negocio: SesionNegocio
) -> MiPerfilProfesional:
    """Cada quien edita **su** ficha. La de la compañera la bloquea la base, no este código.

    Si alguien llegara aquí con el identificador de otra persona, el `UPDATE` no encontraría
    la fila y la respuesta sería un `403`, no un cambio silencioso: lo traduce el manejador
    global de `main.py`.
    """
    sesion, identidad = sesion_negocio
    ficha = await _mi_ficha(sesion, identidad)
    await _aplicar_cambio(sesion, identidad.negocio_id, ficha, cambio)
    return await _pintar(sesion, identidad.negocio_id, ficha)


@router.get("/mi/perfil-profesional/fotos", summary="Mis fotos (encargo 2026-09-07 §3)")
async def listar_mis_fotos(sesion_negocio: SesionNegocio) -> list[FotoDelPortafolio]:
    sesion, identidad = sesion_negocio
    ficha = await _mi_ficha(sesion, identidad)
    return await _fotos_de(sesion, identidad.negocio_id, ficha.id)


@router.post(
    "/mi/perfil-profesional/fotos",
    status_code=201,
    summary="Subir una foto mía (encargo 2026-09-07 §3)",
)
async def anadir_mi_foto(alta: NuevaFoto, sesion_negocio: SesionNegocio) -> FotoDelPortafolio:
    sesion, identidad = sesion_negocio
    ficha = await _mi_ficha(sesion, identidad)
    return await _anadir_foto(sesion, identidad.negocio_id, ficha, alta)


@router.patch(
    "/mi/perfil-profesional/fotos/{foto_id}",
    summary="Asignar mi foto a un servicio del salón (encargo 2026-09-07 §3)",
)
async def editar_mi_foto(
    foto_id: uuid.UUID, cambio: CambioDeFoto, sesion_negocio: SesionNegocio
) -> FotoDelPortafolio:
    sesion, identidad = sesion_negocio
    ficha = await _mi_ficha(sesion, identidad)
    return await _editar_foto(sesion, identidad.negocio_id, ficha, foto_id, cambio)


@router.delete(
    "/mi/perfil-profesional/fotos/{foto_id}", status_code=204, summary="Quitar una foto mía"
)
async def quitar_mi_foto(foto_id: uuid.UUID, sesion_negocio: SesionNegocio) -> None:
    sesion, identidad = sesion_negocio
    ficha = await _mi_ficha(sesion, identidad)
    await _quitar_foto(sesion, identidad.negocio_id, ficha, foto_id)


# ── El dueño, sobre el equipo ─────────────────────────────────────────────────────────────


@router.get(
    "/negocio/profesionales/{profesional_id}/fotos",
    summary="Las fotos de alguien del equipo (STF-1)",
)
async def listar_fotos_del_equipo(
    profesional_id: uuid.UUID,
    sesion_negocio: SesionNegocio,
    solo_servicio: Annotated[
        uuid.UUID | None, Query(description="Solo las atadas a este servicio")
    ] = None,
) -> list[FotoDelPortafolio]:
    """Leer sí puede cualquiera del salón: hace falta para pintar la ficha de un servicio."""
    sesion, identidad = sesion_negocio
    ficha = await _del_negocio(sesion, identidad.negocio_id, profesional_id)
    return await _fotos_de(sesion, identidad.negocio_id, ficha.id, servicio_id=solo_servicio)


@router.post(
    "/negocio/profesionales/{profesional_id}/fotos",
    status_code=201,
    summary="Subir una foto de alguien del equipo (STF-1)",
)
async def anadir_foto_del_equipo(
    profesional_id: uuid.UUID, alta: NuevaFoto, sesion_negocio: SesionNegocio
) -> FotoDelPortafolio:
    """El dueño sube el trabajo de su equipo: es lo normal cuando el barbero no usa la app."""
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    ficha = await _del_negocio(sesion, identidad.negocio_id, profesional_id)
    return await _anadir_foto(sesion, identidad.negocio_id, ficha, alta)


@router.patch(
    "/negocio/profesionales/{profesional_id}/fotos/{foto_id}",
    summary="Asignar la foto de alguien a un servicio (STF-1)",
)
async def editar_foto_del_equipo(
    profesional_id: uuid.UUID,
    foto_id: uuid.UUID,
    cambio: CambioDeFoto,
    sesion_negocio: SesionNegocio,
) -> FotoDelPortafolio:
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    ficha = await _del_negocio(sesion, identidad.negocio_id, profesional_id)
    return await _editar_foto(sesion, identidad.negocio_id, ficha, foto_id, cambio)


@router.delete(
    "/negocio/profesionales/{profesional_id}/fotos/{foto_id}",
    status_code=204,
    summary="Quitar la foto de alguien del equipo (STF-1)",
)
async def quitar_foto_del_equipo(
    profesional_id: uuid.UUID, foto_id: uuid.UUID, sesion_negocio: SesionNegocio
) -> None:
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    ficha = await _del_negocio(sesion, identidad.negocio_id, profesional_id)
    await _quitar_foto(sesion, identidad.negocio_id, ficha, foto_id)


# ── Lo compartido ─────────────────────────────────────────────────────────────────────────


async def _mi_ficha(sesion: AsyncSession, identidad: Identidad) -> StaffProfile:
    """La ficha de quien pregunta. Para el dueño, la suya **si la tiene**.

    Un dueño que no trabaja en su propio salón no tiene ficha de profesional, y ahí la
    respuesta correcta es decirlo, no enseñarle la de otro.
    """
    ficha = (
        await sesion.execute(
            select(StaffProfile).where(
                StaffProfile.business_id == identidad.negocio_id,
                StaffProfile.user_id == identidad.usuario_id,
                StaffProfile.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if ficha is None:
        raise NoAutorizado("Tu cuenta no tiene ficha de profesional en este negocio.")
    return ficha


async def _del_negocio(
    sesion: AsyncSession, negocio_id: uuid.UUID, profesional_id: uuid.UUID
) -> StaffProfile:
    ficha = (
        await sesion.execute(
            select(StaffProfile).where(
                StaffProfile.id == profesional_id,
                StaffProfile.business_id == negocio_id,
                StaffProfile.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if ficha is None:
        raise NoExiste("Ese profesional no existe en este negocio.")
    return ficha


async def aplicar_datos_publicos(
    sesion: AsyncSession,
    negocio_id: uuid.UUID,
    ficha: StaffProfile,
    *,
    slug: str | None = None,
    titular: str | None = None,
    anos_de_experiencia: int | None = None,
    instagram: str | None = None,
    facebook: str | None = None,
    x: str | None = None,
    campos_enviados: set[str],
) -> None:
    """Escribe los campos del perfil público. **Lo usan el panel del dueño y el del profesional.**

    Vive aquí y no en cada router para que no haya dos sitios donde normalizar un usuario de
    Instagram: el día que se acepte una red más, se añade en un sitio.
    """
    if "slug" in campos_enviados and slug is not None:
        ficha.slug = await servicio_profesionales.slug_libre(
            sesion, negocio_id, slug, excluir_id=ficha.id
        )
    if "titular" in campos_enviados:
        ficha.headline = titular
    if "anos_de_experiencia" in campos_enviados:
        ficha.years_experience = anos_de_experiencia

    for red, valor in (("instagram", instagram), ("facebook", facebook), ("x", x)):
        if red not in campos_enviados:
            continue
        try:
            setattr(ficha, red, usuario_de_red(red, valor))
        except TextoInvalido as error:
            raise DatoInvalido(str(error), campo=red) from error


async def _aplicar_cambio(
    sesion: AsyncSession,
    negocio_id: uuid.UUID,
    ficha: StaffProfile,
    cambio: CambioDeMiPerfil,
) -> None:
    enviados = set(cambio.model_fields_set)

    if "nombre" in enviados and cambio.nombre is not None:
        ficha.display_name = cambio.nombre
    if "descripcion" in enviados:
        ficha.bio = cambio.descripcion
    if "foto" in enviados:
        ficha.photo_key = cambio.foto

    await aplicar_datos_publicos(
        sesion,
        negocio_id,
        ficha,
        slug=cambio.slug,
        titular=cambio.titular,
        anos_de_experiencia=cambio.anos_de_experiencia,
        instagram=cambio.instagram,
        facebook=cambio.facebook,
        x=cambio.x,
        campos_enviados=enviados,
    )

    # Quien nunca tuvo slug se queda con uno en cuanto toca su perfil por primera vez: es la
    # forma de que una ficha creada desde el mostrador acabe teniendo URL sin que nadie tenga
    # que acordarse de ponérsela.
    if ficha.slug is None:
        ficha.slug = await servicio_profesionales.slug_libre(
            sesion, negocio_id, ficha.display_name, excluir_id=ficha.id
        )

    await sesion.flush()


async def _pintar(
    sesion: AsyncSession, negocio_id: uuid.UUID, ficha: StaffProfile
) -> MiPerfilProfesional:
    atendidos = await servicio_profesionales.atendidos(sesion, negocio_id, [ficha.id])
    contados = atendidos.get(ficha.id, servicio_profesionales.Atendidos())
    return MiPerfilProfesional(
        id=ficha.id,
        slug=ficha.slug,
        nombre=ficha.display_name,
        titular=ficha.headline,
        descripcion=ficha.bio,
        foto=url_de_media(ficha.photo_key),
        anos_de_experiencia=ficha.years_experience,
        instagram=ficha.instagram,
        instagram_url=url_de_red("instagram", ficha.instagram),
        facebook=ficha.facebook,
        facebook_url=url_de_red("facebook", ficha.facebook),
        x=ficha.x,
        x_url=url_de_red("x", ficha.x),
        citas_atendidas=contados.citas,
        clientes_atendidos=contados.clientes,
        activo=ficha.active,
        visible_en_marketplace=ficha.visible_in_marketplace,
    )


async def _fotos_de(
    sesion: AsyncSession,
    negocio_id: uuid.UUID,
    staff_id: uuid.UUID,
    *,
    servicio_id: uuid.UUID | None = None,
) -> list[FotoDelPortafolio]:
    consulta = (
        select(StaffMedia)
        .where(StaffMedia.business_id == negocio_id, StaffMedia.staff_id == staff_id)
        .order_by(StaffMedia.position, StaffMedia.created_at)
    )
    if servicio_id is not None:
        consulta = consulta.where(StaffMedia.service_id == servicio_id)

    return [
        FotoDelPortafolio(
            id=foto.id,
            url=url_de_media(foto.storage_key) or "",
            descripcion=foto.alt_text,
            servicio_id=foto.service_id,
            posicion=foto.position,
            moderacion=foto.moderation_status,
        )
        for foto in (await sesion.execute(consulta)).scalars().all()
    ]


async def _servicio_del_negocio(
    sesion: AsyncSession, negocio_id: uuid.UUID, servicio_id: uuid.UUID
) -> None:
    """Que el servicio exista **en este salón**. Sin esto, «quién hizo qué» apuntaría a nada."""
    existe = (
        await sesion.execute(
            select(Service.id).where(
                Service.id == servicio_id,
                Service.business_id == negocio_id,
                Service.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existe is None:
        raise DatoInvalido("Ese servicio no existe en este negocio.", servicio=str(servicio_id))


async def _anadir_foto(
    sesion: AsyncSession, negocio_id: uuid.UUID, ficha: StaffProfile, alta: NuevaFoto
) -> FotoDelPortafolio:
    if alta.servicio_id is not None:
        await _servicio_del_negocio(sesion, negocio_id, alta.servicio_id)

    foto = StaffMedia(
        business_id=negocio_id,
        staff_id=ficha.id,
        service_id=alta.servicio_id,
        storage_key=alta.clave,
        alt_text=alta.descripcion,
        position=alta.posicion,
    )
    sesion.add(foto)
    await sesion.flush()
    return FotoDelPortafolio(
        id=foto.id,
        url=url_de_media(foto.storage_key) or "",
        descripcion=foto.alt_text,
        servicio_id=foto.service_id,
        posicion=foto.position,
        moderacion=foto.moderation_status,
    )


async def _foto_suya(
    sesion: AsyncSession, negocio_id: uuid.UUID, staff_id: uuid.UUID, foto_id: uuid.UUID
) -> StaffMedia:
    foto = (
        await sesion.execute(
            select(StaffMedia).where(
                StaffMedia.id == foto_id,
                StaffMedia.business_id == negocio_id,
                StaffMedia.staff_id == staff_id,
            )
        )
    ).scalar_one_or_none()
    if foto is None:
        raise NoExiste("Esa foto no existe.")
    return foto


async def _editar_foto(
    sesion: AsyncSession,
    negocio_id: uuid.UUID,
    ficha: StaffProfile,
    foto_id: uuid.UUID,
    cambio: CambioDeFoto,
) -> FotoDelPortafolio:
    foto = await _foto_suya(sesion, negocio_id, ficha.id, foto_id)

    if cambio.quitar_servicio:
        foto.service_id = None
    elif cambio.servicio_id is not None:
        await _servicio_del_negocio(sesion, negocio_id, cambio.servicio_id)
        foto.service_id = cambio.servicio_id

    if "descripcion" in cambio.model_fields_set:
        foto.alt_text = cambio.descripcion
    if cambio.posicion is not None:
        foto.position = cambio.posicion

    await sesion.flush()
    return FotoDelPortafolio(
        id=foto.id,
        url=url_de_media(foto.storage_key) or "",
        descripcion=foto.alt_text,
        servicio_id=foto.service_id,
        posicion=foto.position,
        moderacion=foto.moderation_status,
    )


async def _quitar_foto(
    sesion: AsyncSession, negocio_id: uuid.UUID, ficha: StaffProfile, foto_id: uuid.UUID
) -> None:
    foto = await _foto_suya(sesion, negocio_id, ficha.id, foto_id)
    await sesion.delete(foto)
    await sesion.flush()
