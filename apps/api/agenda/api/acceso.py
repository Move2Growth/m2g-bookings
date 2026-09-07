"""Entrar, refrescar y salir.

**La puerta principal es correo y contraseña** (`/registrar` y `/entrar`). El código de un solo
uso se queda para lo que siempre debió ser: verificar el teléfono antes de la primera reserva,
porque el salón tiene que poder llamar. Entrar con un código que caduca a los cinco minutos era
un peaje en cada pantalla mientras se desarrolla, y no aportaba seguridad que la contraseña no
dé —al contrario: un WhatsApp interceptado es una sesión, y aquí ni siquiera hay canal todavía—.

Lo que viene después y por eso está el sitio hecho: **segundo factor opcional** y entrada con
Google o Apple. `password_hash` admite nulo justamente para eso.

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
from agenda.servicios.identidad import LARGO_MAXIMO_CONTRASENA, LARGO_MINIMO_CONTRASENA

router = APIRouter(prefix="/api/v1/auth", tags=["acceso"])
ajustes = obtener_ajustes()


class PeticionAlta(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    correo: str = Field(max_length=254)
    contrasena: str = Field(
        min_length=LARGO_MINIMO_CONTRASENA,
        max_length=LARGO_MAXIMO_CONTRASENA,
        description=(
            "Al menos diez caracteres. No se piden mayúsculas ni símbolos: esa regla produce "
            "la misma contraseña en todas las cuentas del país"
        ),
    )
    telefono: str | None = Field(
        default=None,
        description=(
            "Opcional en el alta. Se pide y se verifica antes de la primera reserva, que es "
            "donde hace falta: el salón tiene que poder llamar"
        ),
    )
    superficie: str = "web"


class PeticionEntrada(BaseModel):
    correo: str = Field(max_length=254)
    contrasena: str = Field(max_length=LARGO_MAXIMO_CONTRASENA)
    superficie: str = "web"


class PeticionCambioDeContrasena(BaseModel):
    actual: str | None = Field(
        default=None,
        description="Solo puede faltar si la cuenta todavía no tiene contraseña",
        max_length=LARGO_MAXIMO_CONTRASENA,
    )
    nueva: str = Field(min_length=LARGO_MINIMO_CONTRASENA, max_length=LARGO_MAXIMO_CONTRASENA)


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


@router.post("/registrar", summary="Crea una cuenta con correo y contraseña (ONB-1)")
async def registrar(peticion: PeticionAlta, sesion: SesionPlataforma) -> RespuestaCredenciales:
    """Da de alta y deja dentro en el mismo paso.

    Registrarse y luego tener que entrar es un formulario de más para nada: quien acaba de
    escribir su contraseña ya demostró quién es.
    """
    credenciales = await servicio_identidad.registrar(
        sesion,
        nombre=peticion.nombre,
        correo=peticion.correo,
        contrasena=peticion.contrasena,
        telefono=peticion.telefono,
        superficie=peticion.superficie,
    )
    return RespuestaCredenciales(**credenciales.__dict__)


@router.post("/entrar", summary="Entra con correo y contraseña (ONB-1)")
async def entrar(peticion: PeticionEntrada, sesion: SesionPlataforma) -> RespuestaCredenciales:
    """Correo incorrecto y contraseña incorrecta dan **el mismo error**, a propósito: separarlos
    le confirma a quien prueba combinaciones qué cuentas existen."""
    credenciales = await servicio_identidad.entrar(
        sesion,
        correo=peticion.correo,
        contrasena=peticion.contrasena,
        superficie=peticion.superficie,
    )
    return RespuestaCredenciales(**credenciales.__dict__)


@router.post("/contrasena", status_code=204, summary="Cambia la contraseña")
async def cambiar_contrasena(
    peticion: PeticionCambioDeContrasena,
    sesion: SesionPlataforma,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> None:
    """Cambiarla **cierra las demás sesiones**: es lo que hace quien cree que alguien entró en
    su cuenta, y dejar al intruso dentro vaciaría el gesto de sentido."""
    await servicio_identidad.cambiar_contrasena(
        sesion, usuario_id=identidad.usuario_id, actual=peticion.actual, nueva=peticion.nueva
    )


@router.post("/otp/solicitar", summary="Pide un código para verificar el teléfono (D9)")
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
