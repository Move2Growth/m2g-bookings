"""Entrar, refrescar y salir.

El código del OTP **no se devuelve en la respuesta** salvo en local. Es la diferencia entre un
segundo factor y un adorno: si la API lo enseña, cualquiera que llegue al endpoint entra.
En local se devuelve porque no hay canal —las credenciales de Meta aún no existen— y el flujo
tiene que poder probarse entero sin ellas (ADR-0007).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from agenda.ajustes import obtener_ajustes
from agenda.api.dependencias import Identidad, SesionPlataforma, identidad_actual
from agenda.servicios import identidad as servicio_identidad

router = APIRouter(prefix="/api/v1/auth", tags=["acceso"])
ajustes = obtener_ajustes()


class PeticionOtp(BaseModel):
    telefono: str = Field(description="En formato E.164, por ejemplo +50761234567")


class RespuestaOtp(BaseModel):
    enviado: bool
    canal: str
    codigo_de_desarrollo: str | None = Field(
        default=None,
        description=(
            "Solo en local, y solo porque todavía no hay canal real: en cualquier otro "
            "entorno viaja por WhatsApp y esta respuesta no lo lleva"
        ),
    )


class PeticionVerificacion(BaseModel):
    telefono: str
    codigo: str
    superficie: str = "web"


class RespuestaCredenciales(BaseModel):
    acceso: str
    refresco: str
    expira_en_segundos: int
    usuario_id: uuid.UUID
    negocio_activo: uuid.UUID | None = None


class PeticionRefresco(BaseModel):
    refresco: str


class PeticionModoNegocio(BaseModel):
    negocio_id: uuid.UUID
    superficie: str = "web"


@router.post("/otp/solicitar", summary="Pide un código por WhatsApp (ONB-1)")
async def solicitar(peticion: PeticionOtp, sesion: SesionPlataforma) -> RespuestaOtp:
    """Limitado por teléfono: es seguridad y es control de gasto.

    Cada mensaje de WhatsApp se paga y el SMS de respaldo es el vector clásico de fraude por
    tarificación. Pedir códigos en bucle no puede salir gratis.
    """
    codigo = await servicio_identidad.solicitar_otp(sesion, telefono=peticion.telefono)

    return RespuestaOtp(
        enviado=True,
        canal="whatsapp" if not ajustes.usa_proveedores_de_desarrollo else "desarrollo",
        codigo_de_desarrollo=codigo if ajustes.usa_proveedores_de_desarrollo else None,
    )


@router.post("/otp/verificar", summary="Canjea el código por una sesión (ONB-1)")
async def verificar(
    peticion: PeticionVerificacion, sesion: SesionPlataforma
) -> RespuestaCredenciales:
    credenciales = await servicio_identidad.verificar_otp(
        sesion,
        telefono=peticion.telefono,
        codigo=peticion.codigo,
        superficie=peticion.superficie,
    )
    return RespuestaCredenciales(**credenciales.__dict__)


@router.post("/refrescar", summary="Rota el refresco (ADR-0006)")
async def refrescar(peticion: PeticionRefresco, sesion: SesionPlataforma) -> RespuestaCredenciales:
    """Presentar un refresco ya usado cierra la familia entera: es la firma de un token robado."""
    credenciales = await servicio_identidad.refrescar(sesion, refresco=peticion.refresco)
    return RespuestaCredenciales(**credenciales.__dict__)


@router.post("/cerrar-sesion", status_code=204, summary="Revoca este dispositivo")
async def cerrar(peticion: PeticionRefresco, sesion: SesionPlataforma) -> None:
    await servicio_identidad.cerrar_sesion(sesion, refresco=peticion.refresco)


@router.post("/modo-negocio", summary="Cambia el contexto a un negocio (ONB-3)")
async def modo_negocio(
    peticion: PeticionModoNegocio,
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> RespuestaCredenciales:
    """Cambiar de negocio es **cambiar de token**, no mandar un parámetro distinto."""
    credenciales = await servicio_identidad.cambiar_a_negocio(
        sesion,
        usuario_id=identidad.usuario_id,
        negocio_id=peticion.negocio_id,
        superficie=peticion.superficie,
    )
    return RespuestaCredenciales(**credenciales.__dict__)
