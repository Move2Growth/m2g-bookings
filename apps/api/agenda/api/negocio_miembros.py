"""Asignar personas al local, con su papel (punto 4 del encargo, ONB-3, ONB-4, STF-3).

El alta del local son tres pasos —crear, asignar personas, dar de alta los servicios— y el del
medio es el que faltaba: los servicios y el negocio ya se podían crear, pero **meter a alguien
que ya tiene cuenta, con su papel, no**. Esto lo cierra.

Todo lo de aquí es del dueño. No porque lo diga este archivo: el equipo y la configuración son
suyos por STF-3, y debajo están las políticas restrictivas de la migración 0006 impidiendo que
un profesional escriba en `memberships` aunque un endpoint se olvide del `exigir_dueno`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from agenda.api.dependencias import SesionNegocio, exigir_dueno
from agenda.servicios import miembros as servicio_miembros

router = APIRouter(prefix="/api/v1/negocio", tags=["personas del local"])


class MiembroDelLocal(BaseModel):
    """Una persona asignada al salón. **Sin teléfono**: aquí no hace falta y no viaja."""

    id: uuid.UUID
    usuario_id: uuid.UUID
    nombre: str
    correo: str | None
    rol: str = Field(description="dueno | profesional")
    estado: str = Field(description="invitada | activa | revocada")
    invitacion_caduca: datetime | None
    aceptada_en: datetime | None
    profesional_id: uuid.UUID | None = Field(
        description="Su ficha de equipo en este salón, si la tiene"
    )
    ultimo_dueno: bool = Field(
        description="Si es el único dueño activo: quitarle el papel dejaría el salón sin nadie"
    )


class Invitacion(BaseModel):
    correo: str = Field(max_length=254)
    rol: str = Field(pattern="^(dueno|profesional)$")
    nombre: str | None = Field(
        default=None,
        max_length=120,
        description="Para la ficha de equipo cuando la persona todavía no tiene cuenta",
    )
    profesional_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Ficha de equipo ya creada «sin cuenta» a la que enlazar a esta persona (ONB-4). "
            "Sin ella se crea una nueva"
        ),
    )


class InvitacionCreada(BaseModel):
    miembro: MiembroDelLocal
    token_de_desarrollo: str | None = Field(
        default=None,
        description=(
            "Solo en local, y solo porque todavía no hay canal de correo real: en cualquier "
            "otro entorno el token viaja al correo y esta respuesta no lo lleva"
        ),
    )
    enlace_de_desarrollo: str | None = None


class CambioDePapel(BaseModel):
    rol: str = Field(pattern="^(dueno|profesional)$")


@router.get("/miembros", summary="Quién trabaja en el local y con qué papel (ONB-3)")
async def listar_miembros(sesion_negocio: SesionNegocio) -> list[MiembroDelLocal]:
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    return [
        _pintar(m) for m in await servicio_miembros.listar(sesion, negocio_id=identidad.negocio_id)
    ]


@router.post("/miembros/invitaciones", status_code=201, summary="Invitar a alguien por correo")
async def invitar(peticion: Invitacion, sesion_negocio: SesionNegocio) -> InvitacionCreada:
    """Invita por correo con su papel, **tenga cuenta o no**.

    Si el correo no tiene cuenta se le crea una **sin contraseña**, que no se puede usar para
    entrar por ninguna vía: se activa presentando el token que llega a ese correo. Es lo que
    permite que el dueño reparta los papeles del salón un domingo sin que nadie tenga que
    registrarse antes.

    Volver a invitar a la misma persona **emite un token nuevo** y reutiliza su fila: quien se
    fue y vuelve es un caso normal, no un error.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)

    enviada = await servicio_miembros.invitar(
        sesion,
        negocio_id=identidad.negocio_id,
        invitado_por=identidad.usuario_id,
        correo=peticion.correo,
        rol=peticion.rol,
        nombre=peticion.nombre,
        profesional_id=peticion.profesional_id,
    )
    return InvitacionCreada(
        miembro=_pintar(enviada.miembro),
        token_de_desarrollo=enviada.token or None,
        enlace_de_desarrollo=enviada.enlace or None,
    )


@router.patch("/miembros/{membresia_id}", summary="Cambiarle el papel a alguien (STF-3)")
async def cambiar_papel(
    membresia_id: uuid.UUID, cambio: CambioDePapel, sesion_negocio: SesionNegocio
) -> MiembroDelLocal:
    """Sube o baja de papel. **Bajar al último dueño no se puede.**

    Un salón sin ningún dueño no lo arregla nadie desde dentro: no queda nadie con permiso para
    invitar. Por eso es un error con su propio código —`NEGOCIO_SIN_DUENO`— y no una casilla que
    se marca y ya se verá.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    return _pintar(
        await servicio_miembros.cambiar_papel(
            sesion,
            negocio_id=identidad.negocio_id,
            membresia_id=membresia_id,
            rol=cambio.rol,
        )
    )


@router.delete("/miembros/{membresia_id}", summary="Quitar a alguien del local (ONB-3)")
async def revocar(membresia_id: uuid.UUID, sesion_negocio: SesionNegocio) -> MiembroDelLocal:
    """Surte efecto **en la siguiente llamada**, no cuando caduque su token (ADR-0006).

    No borra la fila ni su ficha de equipo: sus citas siguen ahí y el rastro de quién trabajó
    aquí es lo que permite entender una agenda de hace tres meses. Y tampoco deja al salón sin
    dueño: quitar al último es el mismo error que bajarle el papel.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    return _pintar(
        await servicio_miembros.revocar(
            sesion, negocio_id=identidad.negocio_id, membresia_id=membresia_id
        )
    )


def _pintar(miembro: servicio_miembros.Miembro) -> MiembroDelLocal:
    return MiembroDelLocal(
        id=miembro.id,
        usuario_id=miembro.usuario_id,
        nombre=miembro.nombre,
        correo=miembro.correo,
        rol=miembro.rol,
        estado=miembro.estado,
        invitacion_caduca=miembro.invitacion_caduca,
        aceptada_en=miembro.aceptada_en,
        profesional_id=miembro.profesional_id,
        ultimo_dueno=miembro.ultimo_dueno,
    )
