"""Asignar personas al local: invitar, aceptar y no dejar el salón sin dueño (punto 4).

Tres cosas que solo se pueden comprobar contra una base real:

1. **La puerta de la invitación es una política**, no un `if`. Quien acepta no está dentro de
   ningún negocio, así que lo único que le deja ver su fila es presentar el token — y lo que se
   compara es su hash. Las pruebas de token equivocado y token caducado van **sin pasar por el
   servicio**, contra el SQL, para que lo que se mida sea la política.
2. **La regla del último dueño**, que se cuenta en la base y en la misma transacción.
3. **La puerta de atrás**: dar de baja del equipo a alguien revoca su membresía, y el dueño que
   además corta el pelo —la norma en un salón de barrio— se llevaba por delante al único dueño
   del salón sin que nada avisara.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agenda.errores import NoAutorizado, SinDueno
from agenda.servicios import miembros as servicio_miembros
from pruebas.bd.escenario_panel import conexion_de_dueno, montar_salon

pytestmark = pytest.mark.bd


@asynccontextmanager
async def _en_el_negocio(motor, negocio_id: uuid.UUID) -> AsyncIterator[AsyncSession]:
    """La sesión del panel: negocio fijado, como `sesion_de_negocio` de la API."""
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    async with crear() as sesion, sesion.begin():
        await sesion.execute(
            text("SELECT set_config('app.current_business_id', :negocio, true)"),
            {"negocio": str(negocio_id)},
        )
        yield sesion


@asynccontextmanager
async def _sin_negocio(motor) -> AsyncIterator[AsyncSession]:
    """La sesión de plataforma: el rol de la aplicación **sin tenant fijado**, como al entrar."""
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    async with crear() as sesion, sesion.begin():
        yield sesion


def _correo() -> str:
    return f"marielys.{uuid.uuid4().hex[:8]}@correo.pa"


async def test_invitar_a_alguien_sin_cuenta_y_que_acepte(motor):
    """El camino entero: el dueño invita un domingo y la persona entra sin registrarse antes."""
    salon = await montar_salon()
    correo = _correo()

    async with _en_el_negocio(motor, salon.negocio_id) as sesion:
        enviada = await servicio_miembros.invitar(
            sesion,
            negocio_id=salon.negocio_id,
            invitado_por=salon.dueno_user_id,
            correo=correo,
            rol="profesional",
            nombre="Yaris Him",
        )
        token = enviada.token
        await sesion.commit()

    assert token, "En local el token tiene que volver: todavía no hay canal de correo."
    assert enviada.miembro.estado == "invitada"

    async with _sin_negocio(motor) as sesion:
        invitacion = await servicio_miembros.previsualizar(sesion, token=token)
    assert invitacion.rol == "profesional"
    assert (
        invitacion.cuenta_con_contrasena is False
    ), "La cuenta la creó la invitación: aceptar tiene que incluir elegir contraseña."

    async with _sin_negocio(motor) as sesion:
        credenciales = await servicio_miembros.aceptar(
            sesion, token=token, contrasena="una frase larga y facil"
        )
        await sesion.commit()

    assert (
        credenciales.negocio_activo == salon.negocio_id
    ), "Aceptar tiene que dejar dentro del salón, no en la pantalla de clienta."

    async with _en_el_negocio(motor, salon.negocio_id) as sesion:
        equipo = await servicio_miembros.listar(sesion, negocio_id=salon.negocio_id)
    invitada = next(m for m in equipo if m.correo == correo)
    assert invitada.estado == "activa"
    assert (
        invitada.profesional_id is not None
    ), "Un profesional sin ficha de equipo entra en un salón donde no tiene agenda."


async def test_el_token_equivocado_no_abre_nada(motor):
    """Y no lo impide el servicio: la política solo deja ver la fila cuyo hash coincide.

    La consulta va **a pelo**, con un token inventado declarado como si fuera bueno. Si esto
    devolviera algo, la puerta estaría abierta para cualquiera que pruebe cadenas al azar.
    """
    salon = await montar_salon()
    async with _en_el_negocio(motor, salon.negocio_id) as sesion:
        await servicio_miembros.invitar(
            sesion,
            negocio_id=salon.negocio_id,
            invitado_por=salon.dueno_user_id,
            correo=_correo(),
            rol="profesional",
        )
        await sesion.commit()

    inventado = hashlib.sha256(b"no es el token de nadie").hexdigest()
    async with _sin_negocio(motor) as sesion:
        await sesion.execute(
            text("SELECT set_config('app.current_invite', :token, true)"), {"token": inventado}
        )
        visibles = (await sesion.execute(text("SELECT count(*) FROM memberships"))).scalar_one()

    assert visibles == 0, "Con un token inventado se han visto membresías."


async def test_una_invitacion_caducada_no_se_puede_aceptar(motor):
    """La caducidad se comprueba **en la política**, no solo en el código.

    Se envejece la fila a mano y después se intenta el `UPDATE` directamente: si la política no
    mirara `invite_expires_at`, el `UPDATE` tocaría una fila y la invitación de hace tres meses
    seguiría abriendo el salón.
    """
    salon = await montar_salon()
    async with _en_el_negocio(motor, salon.negocio_id) as sesion:
        enviada = await servicio_miembros.invitar(
            sesion,
            negocio_id=salon.negocio_id,
            invitado_por=salon.dueno_user_id,
            correo=_correo(),
            rol="profesional",
        )
        token = enviada.token
        await sesion.commit()

    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text(
                "UPDATE memberships SET invite_expires_at = now() - interval '1 day' "
                "WHERE id = :membresia"
            ),
            {"membresia": enviada.miembro.id},
        )

    async with _sin_negocio(motor) as sesion:
        await servicio_miembros.declarar_invitacion(sesion, token)
        tocadas = (
            await sesion.execute(
                text(
                    "UPDATE memberships SET status = 'activa' "
                    "WHERE invite_token_hash IS NOT NULL RETURNING id"
                )
            )
        ).all()
    assert tocadas == [], "Una invitación caducada ha podido aceptarse por SQL directo."

    async with _sin_negocio(motor) as sesion:
        with pytest.raises(NoAutorizado):
            await servicio_miembros.aceptar(
                sesion, token=token, contrasena="una frase larga y facil"
            )


async def test_una_cuenta_que_ya_tiene_contrasena_exige_estar_dentro(motor):
    """Un token de correo no puede dar acceso a una cuenta que ya tiene dueño.

    Quien interceptara el enlace entraría en la cuenta de otra persona, y no solo en el salón.
    """
    salon = await montar_salon()
    correo = _correo()
    async with conexion_de_dueno() as sesion:
        usuario_id = (
            await sesion.execute(
                text(
                    "INSERT INTO users (full_name, email, password_hash) "
                    "VALUES ('Abdiel Him', :correo, 'ya-tiene-una') RETURNING id"
                ),
                {"correo": correo},
            )
        ).scalar_one()

    async with _en_el_negocio(motor, salon.negocio_id) as sesion:
        enviada = await servicio_miembros.invitar(
            sesion,
            negocio_id=salon.negocio_id,
            invitado_por=salon.dueno_user_id,
            correo=correo,
            rol="profesional",
        )
        await sesion.commit()

    async with _sin_negocio(motor) as sesion:
        with pytest.raises(NoAutorizado):
            await servicio_miembros.aceptar(sesion, token=enviada.token)

    async with _sin_negocio(motor) as sesion:
        credenciales = await servicio_miembros.aceptar(
            sesion, token=enviada.token, usuario_en_sesion=usuario_id
        )
        await sesion.commit()
    assert credenciales.negocio_activo == salon.negocio_id


async def test_no_se_le_puede_quitar_el_papel_al_ultimo_dueno(motor):
    """La regla que no se negocia. Un salón sin dueño no lo arregla nadie desde dentro."""
    salon = await montar_salon()

    async with _en_el_negocio(motor, salon.negocio_id) as sesion:
        equipo = await servicio_miembros.listar(sesion, negocio_id=salon.negocio_id)
        dueno = next(m for m in equipo if m.rol == "dueno")
        assert dueno.ultimo_dueno is True

        with pytest.raises(SinDueno):
            await servicio_miembros.cambiar_papel(
                sesion,
                negocio_id=salon.negocio_id,
                membresia_id=dueno.id,
                rol="profesional",
            )
        with pytest.raises(SinDueno):
            await servicio_miembros.revocar(
                sesion, negocio_id=salon.negocio_id, membresia_id=dueno.id
            )


async def test_con_dos_duenos_si_se_le_puede_quitar_a_uno(motor):
    """Para que la prueba anterior signifique «el último» y no «ningún dueño»."""
    salon = await montar_salon()

    async with _en_el_negocio(motor, salon.negocio_id) as sesion:
        equipo = await servicio_miembros.listar(sesion, negocio_id=salon.negocio_id)
        primero = next(m for m in equipo if m.rol == "dueno")
        otro = next(m for m in equipo if m.rol == "profesional")

        await servicio_miembros.cambiar_papel(
            sesion, negocio_id=salon.negocio_id, membresia_id=otro.id, rol="dueno"
        )
        quitado = await servicio_miembros.revocar(
            sesion, negocio_id=salon.negocio_id, membresia_id=primero.id
        )

    assert quitado.estado == "revocada"


async def test_dar_de_baja_del_equipo_no_puede_dejar_el_salon_sin_dueno(motor):
    """La puerta de atrás: la baja del equipo **revoca la membresía**.

    En un salón de barrio el dueño corta el pelo, así que tiene ficha de equipo. Antes de esta
    comprobación, darse de baja a sí mismo del equipo revocaba su propia membresía de dueño y el
    salón se quedaba sin nadie que pudiera invitar a nadie — sin ningún error por el camino.
    """
    salon = await montar_salon()
    async with conexion_de_dueno() as sesion:
        # El dueño se pone su propia ficha de equipo, como cualquier dueño que además atiende.
        ficha = (
            await sesion.execute(
                text(
                    "INSERT INTO staff_profiles (business_id, user_id, display_name) "
                    "VALUES (:negocio, :usuario, 'Dueño que corta') RETURNING id"
                ),
                {"negocio": salon.negocio_id, "usuario": salon.dueno_user_id},
            )
        ).scalar_one()

    async with _en_el_negocio(motor, salon.negocio_id) as sesion:
        with pytest.raises(SinDueno):
            await servicio_miembros.exigir_que_quede_un_dueno_por_usuario(
                sesion, negocio_id=salon.negocio_id, usuario_id=salon.dueno_user_id
            )
        # Y con otra persona del equipo la baja no está bloqueada por esta regla.
        await servicio_miembros.exigir_que_quede_un_dueno_por_usuario(
            sesion, negocio_id=salon.negocio_id, usuario_id=salon.kevin.user_id
        )
    assert ficha is not None


async def test_la_invitacion_de_un_salon_no_se_ve_desde_otro(motor):
    """El aislamiento sigue en pie: declarar una invitación no abre el negocio entero."""
    uno = await montar_salon()
    otro = await montar_salon()

    async with _en_el_negocio(motor, otro.negocio_id) as sesion:
        enviada = await servicio_miembros.invitar(
            sesion,
            negocio_id=otro.negocio_id,
            invitado_por=otro.dueno_user_id,
            correo=_correo(),
            rol="profesional",
        )
        await sesion.commit()

    async with _en_el_negocio(motor, uno.negocio_id) as sesion:
        await servicio_miembros.declarar_invitacion(sesion, enviada.token)
        # Con la invitación declarada se ve **su fila**, y ninguna más del otro salón.
        vistas = (
            await sesion.execute(
                text("SELECT business_id FROM memberships WHERE business_id = :otro"),
                {"otro": otro.negocio_id},
            )
        ).all()
    assert (
        len(vistas) == 1
    ), "Declarar una invitación ha abierto más membresías del otro salón que la invitada."


async def test_volver_a_invitar_emite_un_token_nuevo_y_el_viejo_deja_de_valer(motor):
    """Quien se fue y vuelve es un caso normal; el enlace viejo circulando por ahí, no."""
    salon = await montar_salon()
    correo = _correo()

    async with _en_el_negocio(motor, salon.negocio_id) as sesion:
        primera = await servicio_miembros.invitar(
            sesion,
            negocio_id=salon.negocio_id,
            invitado_por=salon.dueno_user_id,
            correo=correo,
            rol="profesional",
        )
        await sesion.commit()
    async with _en_el_negocio(motor, salon.negocio_id) as sesion:
        segunda = await servicio_miembros.invitar(
            sesion,
            negocio_id=salon.negocio_id,
            invitado_por=salon.dueno_user_id,
            correo=correo,
            rol="profesional",
        )
        await sesion.commit()

    assert primera.token != segunda.token
    assert primera.miembro.id == segunda.miembro.id, "Se ha creado una segunda membresía."

    async with _sin_negocio(motor) as sesion:
        with pytest.raises(NoAutorizado):
            await servicio_miembros.previsualizar(sesion, token=primera.token)

    async with _sin_negocio(motor) as sesion:
        viva = await servicio_miembros.previsualizar(sesion, token=segunda.token)
    assert viva.caduca > datetime.now(UTC) + timedelta(days=6)
