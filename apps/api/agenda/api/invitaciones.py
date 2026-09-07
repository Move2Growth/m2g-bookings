"""Aceptar una invitación a un local (punto 4 del encargo).

Es la otra mitad de `POST /negocio/miembros/invitaciones`, y va aparte por una razón que se ve
en las dependencias: **quien acepta todavía no está dentro de ningún negocio**. Estas rutas
usan la sesión de plataforma —el rol de la aplicación sin tenant fijado—, igual que entrar o
refrescar, porque exigir el negocio activo aquí sería exigir lo que la invitación viene a dar.

**El token va en el cuerpo y no en la URL**, y las dos rutas son `POST` aunque una de ellas solo
lea. No es purismo REST al revés: un secreto en la ruta acaba en el registro de accesos del
servidor, en el historial del navegador y en la cabecera `Referer` de la primera imagen que
cargue la página. El token de una invitación abre un salón; no puede ir escrito en un sitio del
que no se pueda borrar.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from agenda.api.acceso import RespuestaCredenciales
from agenda.api.dependencias import IdentidadOpcional, SesionPlataforma
from agenda.servicios import miembros as servicio_miembros
from agenda.servicios.identidad import LARGO_MAXIMO_CONTRASENA, LARGO_MINIMO_CONTRASENA

router = APIRouter(prefix="/api/v1/invitaciones", tags=["invitaciones"])


class PeticionDeInvitacion(BaseModel):
    token: str = Field(min_length=16, max_length=200)


class InvitacionAbierta(BaseModel):
    """Lo que se enseña antes de aceptar: a qué salón te invitan y con qué papel."""

    negocio: str
    rol: str = Field(description="dueno | profesional")
    correo: str
    nombre: str
    caduca: datetime
    cuenta_ya_tiene_dueno: bool = Field(
        description=(
            "Cuando es falso, la cuenta la creó la invitación y no hay otra forma de entrar en "
            "ella: aceptar incluye elegir contraseña. Cuando es cierto, hay que estar dentro "
            "con esa cuenta"
        )
    )


class PeticionDeAceptacion(PeticionDeInvitacion):
    contrasena: str | None = Field(
        default=None,
        min_length=LARGO_MINIMO_CONTRASENA,
        max_length=LARGO_MAXIMO_CONTRASENA,
        description="Obligatoria solo si la cuenta todavía no tiene contraseña",
    )
    superficie: str = "web"


@router.post("/ver", summary="Qué salón y qué papel hay detrás del enlace (ONB-3)")
async def ver(peticion: PeticionDeInvitacion, sesion: SesionPlataforma) -> InvitacionAbierta:
    """No cambia nada: solo dice qué hay al otro lado del enlace.

    Una invitación caducada, ya usada o inventada dan **el mismo error**. Separarlos le diría a
    quien prueba tokens al azar cuándo va por buen camino.
    """
    invitacion = await servicio_miembros.previsualizar(sesion, token=peticion.token)
    return InvitacionAbierta(
        negocio=invitacion.negocio,
        rol=invitacion.rol,
        correo=invitacion.correo,
        nombre=invitacion.nombre,
        caduca=invitacion.caduca,
        cuenta_ya_tiene_dueno=invitacion.cuenta_ya_tiene_dueno,
    )


@router.post("/aceptar", summary="Entrar en el local al que te invitaron (ONB-3, ONB-4)")
async def aceptar(
    peticion: PeticionDeAceptacion,
    sesion: SesionPlataforma,
    identidad: IdentidadOpcional,
) -> RespuestaCredenciales:
    """Acepta y devuelve una sesión **ya en modo negocio**: se entra y se está dentro.

    Dos caminos, y la diferencia importa:

    * **La cuenta la creó la invitación** y no hay otra forma de entrar en ella: la contraseña
      se elige aquí. El token es la prueba de que ese buzón es suyo, así que el correo queda
      verificado — es exactamente lo que demuestra haber recibido el enlace.
    * **La cuenta ya es de alguien** —contraseña, teléfono verificado o Google/Apple—: hace
      falta **estar dentro con ella**. Un token de correo no puede dar acceso a una cuenta que
      ya tiene dueño; quien interceptara el enlace entraría en la cuenta de otra persona y no
      solo en el salón.
    """
    credenciales = await servicio_miembros.aceptar(
        sesion,
        token=peticion.token,
        contrasena=peticion.contrasena,
        usuario_en_sesion=identidad.usuario_id if identidad else None,
        superficie=peticion.superficie,
    )
    return RespuestaCredenciales(**credenciales.__dict__)
