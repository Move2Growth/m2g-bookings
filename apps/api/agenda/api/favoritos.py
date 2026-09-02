"""Favoritos, perfil de la persona y «reservar de nuevo» (MKT-5).

Las tres cosas comparten superficie —`/mi/…`— porque las tres son de la persona y no de ningún
salón. Y comparten un detalle de implementación que conviene entender antes de tocar nada:

**la lista de favoritos se lee con el rol de la aplicación, pero las tarjetas se componen con
el rol público.** No es un rodeo: `favorites` es una tabla de la plataforma que la API filtra
por identidad, mientras que el nombre, la foto y el rating de un salón son datos publicables
que ya tienen su política en el rol del marketplace. Componerlos con el rol del negocio
obligaría a fijar un tenant por cada favorito —y a tener permiso sobre tablas que no hacen
falta para pintar una tarjeta.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from agenda.api.dependencias import Identidad, SesionPlataforma, identidad_actual
from agenda.bd import sesion_de_marketplace
from agenda.errores import NoExiste
from agenda.modelos.catalogo import Service
from agenda.modelos.clientes import Favorite
from agenda.modelos.equipo import StaffProfile, StaffService
from agenda.modelos.identidad import User
from agenda.modelos.negocio import Business
from agenda.modelos.reservas import Booking, BookingItem
from agenda.servicios import tarjetas as servicio_tarjetas

router = APIRouter(prefix="/api/v1/mi", tags=["cliente"])


class NegocioFavorito(BaseModel):
    """Un salón guardado. Misma forma que un resultado de búsqueda, para pintarlo igual."""

    negocio_id: uuid.UUID
    slug: str
    nombre: str
    direccion: str | None
    zona: str | None
    foto_portada: str | None
    rating: float | None
    numero_reviews: int
    servicios_desde_centavos: int | None
    categorias: list[str]
    abierto_ahora: bool | None


class NuevoFavorito(BaseModel):
    negocio_id: uuid.UUID


class MiPerfil(BaseModel):
    """Lo que la persona ve de sí misma. El teléfono sí, porque es suyo."""

    id: uuid.UUID
    nombre: str
    telefono: str
    telefono_verificado: bool
    correo: str | None
    idioma: str


class CambioDePerfil(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    correo: str | None = Field(default=None, max_length=200)


class ServicioParaRepetir(BaseModel):
    id: uuid.UUID
    nombre: str
    duracion_minutos: int
    precio_centavos: int | None
    #: Si el salón lo sigue ofreciendo. Un servicio retirado **no se puede volver a reservar**,
    #: y decirlo aquí evita mandar a la persona a un calendario que nunca tendrá huecos.
    sigue_disponible: bool


class ReservaDeNuevo(BaseModel):
    """Todo lo que hace falta para volver a entrar en el flujo de reserva (MKT-5).

    Es deliberadamente lo mismo que pide `POST /mi/reservas`: la pantalla de «reservar de
    nuevo» no es un atajo mágico, es el mismo formulario relleno. Si el servicio o el
    profesional ya no están, se dice **antes** de elegir hora, no después de intentarlo.
    """

    negocio_slug: str
    negocio_nombre: str
    servicios: list[ServicioParaRepetir]
    profesional_id: uuid.UUID | None
    profesional: str | None
    profesional_disponible: bool
    se_puede_repetir: bool = Field(
        description="Cierto solo si siguen activos todos los servicios y el profesional"
    )


@router.get("/perfil", summary="Mis datos")
async def leer_perfil(
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> MiPerfil:
    usuario = await sesion.get(User, identidad.usuario_id)
    if usuario is None:
        raise NoExiste("Esa cuenta ya no existe.")
    return _pintar_perfil(usuario)


@router.patch("/perfil", summary="Cambiar mi nombre o mi correo")
async def editar_perfil(
    cambio: CambioDePerfil,
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> MiPerfil:
    """El **teléfono no se cambia por aquí**: es la identidad de la cuenta.

    Cambiarlo es verificar el nuevo con un OTP, porque si bastara con un `PATCH`, quien
    entrara una vez en una sesión ajena se llevaría la cuenta entera cambiando el número.
    """
    usuario = await sesion.get(User, identidad.usuario_id)
    if usuario is None:
        raise NoExiste("Esa cuenta ya no existe.")

    if cambio.nombre is not None:
        usuario.full_name = cambio.nombre.strip()[:120]
    if cambio.correo is not None:
        # El correo entra **sin verificar**: sirve para mandar la factura, no para entrar. Las
        # identidades de Google y Apple solo se enlazan con correo verificado (ADR-0006), y
        # aceptar aquí uno cualquiera como verificado sería el atajo para secuestrar cuentas.
        usuario.email = cambio.correo.strip().lower() or None
        usuario.email_verified_at = None

    await sesion.flush()
    return _pintar_perfil(usuario)


@router.get("/favoritos", summary="Mis salones guardados (MKT-5)")
async def listar_favoritos(
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> list[NegocioFavorito]:
    """Los guardados, en orden de guardado descendente: el último arriba."""
    ids = list(
        (
            await sesion.execute(
                select(Favorite.business_id)
                .where(Favorite.user_id == identidad.usuario_id)
                .order_by(Favorite.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    if not ids:
        return []

    # El rol público compone la tarjeta. Si alguno de los guardados dejó de estar publicado,
    # sencillamente no vuelve: la política del marketplace lo esconde, y enseñar un salón
    # despublicado en los favoritos sería mandar a alguien a una página que ya no existe.
    async with sesion_de_marketplace() as publica:
        compuestas = await servicio_tarjetas.componer(publica, ids)

    return [
        NegocioFavorito(
            negocio_id=t.negocio_id,
            slug=t.slug,
            nombre=t.nombre,
            direccion=t.direccion,
            zona=t.zona,
            foto_portada=t.foto_portada,
            rating=t.rating,
            numero_reviews=t.numero_reviews,
            servicios_desde_centavos=t.desde_centavos,
            categorias=t.categorias,
            abierto_ahora=t.abierto_ahora,
        )
        # Se recorre `ids` y no el diccionario para conservar el orden de guardado.
        for negocio_id in ids
        if (t := compuestas.get(negocio_id)) is not None
    ]


@router.post("/favoritos", status_code=201, summary="Guardar un salón (MKT-5)")
async def guardar_favorito(
    nuevo: NuevoFavorito,
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> dict[str, bool]:
    """Guardar dos veces el mismo salón **no es un error**: es la misma respuesta.

    El botón de favorito se pulsa con el dedo en un teléfono con 3G, y un doble toque que
    devuelve `409` es una pantalla en rojo por hacer bien lo que se quería hacer. Se resuelve
    con `ON CONFLICT DO NOTHING`, que además es a prueba de dos peticiones a la vez.
    """
    negocio = (
        await sesion.execute(
            select(Business.id).where(
                Business.id == nuevo.negocio_id, Business.status == "publicado"
            )
        )
    ).scalar_one_or_none()
    if negocio is None:
        raise NoExiste("Ese negocio no existe o no está publicado.")

    await sesion.execute(
        pg_insert(Favorite.__table__)
        .values(user_id=identidad.usuario_id, business_id=negocio)
        .on_conflict_do_nothing(index_elements=["user_id", "business_id"])
    )
    return {"guardado": True}


@router.delete("/favoritos/{negocio_id}", status_code=204, summary="Quitar de favoritos (MKT-5)")
async def quitar_favorito(
    negocio_id: uuid.UUID,
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> None:
    """Quitar algo que no estaba tampoco es un error: el resultado que se pedía ya se cumple."""
    await sesion.execute(
        delete(Favorite).where(
            Favorite.user_id == identidad.usuario_id,
            Favorite.business_id == negocio_id,
        )
    )


@router.get("/reservas/{reserva_id}/repetir", summary="Reservar de nuevo (MKT-5)")
async def repetir_reserva(
    reserva_id: uuid.UUID,
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> ReservaDeNuevo:
    """Devuelve el mismo servicio y el mismo profesional, listos para el flujo de reserva.

    **No crea nada.** «Reservar de nuevo» es rellenar el formulario, no saltárselo: la hora
    sigue eligiéndose, porque el hueco de hace un mes no significa nada hoy y porque una cita
    creada sin que nadie confirme la hora es una sorpresa el día que toca.
    """
    reserva = await sesion.get(Booking, reserva_id)
    if reserva is None or reserva.client_user_id != identidad.usuario_id:
        raise NoExiste("Esa cita no es tuya o ya no existe.")

    negocio = await sesion.get(Business, reserva.business_id)
    if negocio is None or negocio.status != "publicado":
        raise NoExiste("Ese salón ya no está en el marketplace.")

    # A partir de aquí hace falta el negocio declarado: los servicios y el equipo son suyos.
    await sesion.execute(
        text("SELECT set_config('app.current_business_id', :negocio, true)"),
        {"negocio": str(reserva.business_id)},
    )

    items = (
        (
            await sesion.execute(
                select(BookingItem)
                .where(BookingItem.booking_id == reserva.id)
                .order_by(BookingItem.position)
            )
        )
        .scalars()
        .all()
    )
    vivos = {
        fila.id: fila
        for fila in (
            (
                await sesion.execute(
                    select(Service).where(
                        Service.id.in_([i.service_id for i in items]),
                        Service.active.is_(True),
                        Service.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
    }

    profesional = await sesion.get(StaffProfile, reserva.staff_id)
    profesional_ok = bool(profesional and profesional.active and profesional.deleted_at is None)
    if profesional_ok:
        # Que siga en plantilla no basta: tiene que seguir prestando **todos** los servicios de
        # aquella cita, o la reserva encadenada se quedaría a medias.
        presta = set(
            (
                await sesion.execute(
                    select(StaffService.service_id).where(
                        StaffService.staff_id == reserva.staff_id,
                        StaffService.service_id.in_(list(vivos)),
                    )
                )
            )
            .scalars()
            .all()
        )
        profesional_ok = set(vivos) <= presta

    servicios = [
        ServicioParaRepetir(
            id=item.service_id,
            # El nombre y el precio de **hoy** si el servicio sigue vivo; el congelado de la
            # cita si ya no está. Enseñar el precio de hace un año como si fuera el actual es
            # la clase de detalle que acaba en una discusión en el mostrador.
            nombre=vivos[item.service_id].name if item.service_id in vivos else item.name_snapshot,
            duracion_minutos=(
                vivos[item.service_id].duration_min
                if item.service_id in vivos
                else item.duration_min_snapshot
            ),
            precio_centavos=(
                vivos[item.service_id].price_minor
                if item.service_id in vivos
                else item.price_minor_snapshot
            ),
            sigue_disponible=item.service_id in vivos,
        )
        for item in items
    ]

    return ReservaDeNuevo(
        negocio_slug=negocio.slug,
        negocio_nombre=negocio.display_name,
        servicios=servicios,
        profesional_id=reserva.staff_id if profesional_ok else None,
        profesional=profesional.display_name if profesional else None,
        profesional_disponible=profesional_ok,
        se_puede_repetir=bool(servicios)
        and all(s.sigue_disponible for s in servicios)
        and profesional_ok,
    )


def _pintar_perfil(usuario: User) -> MiPerfil:
    return MiPerfil(
        id=usuario.id,
        nombre=usuario.full_name,
        telefono=usuario.phone_e164,
        telefono_verificado=usuario.phone_verified_at is not None,
        correo=usuario.email,
        idioma=usuario.locale,
    )
