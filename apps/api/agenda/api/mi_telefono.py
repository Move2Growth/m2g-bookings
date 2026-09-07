"""Verificar el teléfono de la cuenta que ya está dentro (D9).

**Esto no es entrar.** Va en su propio módulo justamente para que no se confunda con
`/auth/otp/verificar`, que sí es entrar: aquel busca la cuenta de ese número y, si no existe,
crea una nueva. Llamarlo desde una sesión ya abierta —que es lo que hacía la pantalla de
reservar— dejaba a la persona dentro de **otra cuenta**, vacía y sin sus citas, sin un solo
error por ninguna parte.

El teléfono hace falta antes de la primera reserva y no antes: el salón tiene que poder llamar
si se retrasa o si hay que mover la cita. Pedirlo en el alta devolvería el trámite que se quitó
al pasar a correo y contraseña.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from agenda.ajustes import obtener_ajustes
from agenda.api.dependencias import Identidad, SesionPlataforma, identidad_actual
from agenda.servicios import identidad as servicio_identidad

router = APIRouter(prefix="/api/v1/mi/telefono", tags=["mi cuenta"])
ajustes = obtener_ajustes()


class PeticionDeCodigo(BaseModel):
    telefono: str = Field(description="En formato E.164, por ejemplo +50761234567")


class RespuestaDeCodigo(BaseModel):
    enviado: bool
    canal: str
    codigo_de_desarrollo: str | None = Field(
        default=None,
        description=(
            "Solo en local, y solo porque todavía no hay canal real: en cualquier otro "
            "entorno viaja por WhatsApp y esta respuesta no lo lleva"
        ),
    )


class PeticionDeVerificacion(BaseModel):
    telefono: str
    codigo: str


@router.post("/solicitar", summary="Pide el código para verificar tu teléfono (D9)")
async def solicitar(
    peticion: PeticionDeCodigo,
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> RespuestaDeCodigo:
    """Exige sesión: verificar un teléfono siempre es verificar el de **alguien**."""
    codigo = await servicio_identidad.solicitar_otp(
        sesion, telefono=peticion.telefono, proposito="verificacion_telefono"
    )
    return RespuestaDeCodigo(
        enviado=True,
        canal="whatsapp" if not ajustes.usa_proveedores_de_desarrollo else "desarrollo",
        codigo_de_desarrollo=codigo if ajustes.usa_proveedores_de_desarrollo else None,
    )


@router.post("/verificar", status_code=204, summary="Ata el teléfono a tu cuenta (D9)")
async def verificar(
    peticion: PeticionDeVerificacion,
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> None:
    """No devuelve credenciales **a propósito**: la sesión que había sigue siendo la buena."""
    await servicio_identidad.verificar_telefono_de(
        sesion,
        usuario_id=identidad.usuario_id,
        telefono=peticion.telefono,
        codigo=peticion.codigo,
    )
