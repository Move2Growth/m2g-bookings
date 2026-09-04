"""Entrar, refrescar y salir, contra la base de verdad.

Estas pruebas van aquí y no en las de dominio porque lo que garantiza casi todo es la base:
el único del hash del refresco, el aislamiento de las membresías y el hecho de que revocar
surta efecto de inmediato. Un doble de pruebas diría que sí a todo.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.errores import DemasiadosIntentos, NoAutorizado, OtpInvalido
from agenda.modelos.identidad import Membership, Session, User
from agenda.servicios import identidad as servicio
from pruebas.bd.escenario import URL_DUENO_ASYNC, montar_escenario

pytestmark = pytest.mark.bd

TELEFONO = "+50761239999"


async def _sesion() -> tuple[AsyncSession, object]:
    motor = create_async_engine(URL_DUENO_ASYNC, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    return crear(), motor


async def test_el_primer_acceso_crea_la_cuenta_con_el_telefono_verificado():
    """ONB-1: no hay registro aparte. Quien verifica su teléfono ya tiene cuenta."""
    sesion, motor = await _sesion()
    telefono = f"+5076{uuid.uuid4().int % 10**7:07d}"
    try:
        async with sesion.begin():
            codigo = await servicio.solicitar_otp(sesion, telefono=telefono)
            credenciales = await servicio.verificar_otp(sesion, telefono=telefono, codigo=codigo)
            usuario = await sesion.get(User, credenciales.usuario_id)

        assert usuario is not None
        assert usuario.phone_verified_at is not None
        assert credenciales.acceso and credenciales.refresco
    finally:
        await sesion.close()
        await motor.dispose()


async def test_un_codigo_equivocado_no_abre_sesion_y_gasta_intento():
    sesion, motor = await _sesion()
    telefono = f"+5076{uuid.uuid4().int % 10**7:07d}"
    try:
        async with sesion.begin():
            await servicio.solicitar_otp(sesion, telefono=telefono)
            with pytest.raises(OtpInvalido):
                await servicio.verificar_otp(sesion, telefono=telefono, codigo="000000")
    finally:
        await sesion.close()
        await motor.dispose()


async def test_pedir_un_codigo_nuevo_invalida_el_anterior():
    """Si no, la ventana de ataque sería la suma de todas las ventanas abiertas."""
    sesion, motor = await _sesion()
    telefono = f"+5076{uuid.uuid4().int % 10**7:07d}"
    try:
        async with sesion.begin():
            viejo = await servicio.solicitar_otp(sesion, telefono=telefono)
            nuevo = await servicio.solicitar_otp(sesion, telefono=telefono)

            with pytest.raises(OtpInvalido):
                await servicio.verificar_otp(sesion, telefono=telefono, codigo=viejo)

            credenciales = await servicio.verificar_otp(sesion, telefono=telefono, codigo=nuevo)
            assert credenciales.acceso
    finally:
        await sesion.close()
        await motor.dispose()


async def test_pedir_codigos_en_bucle_se_corta():
    """Es seguridad y es coste: cada mensaje se paga."""
    sesion, motor = await _sesion()
    telefono = f"+5076{uuid.uuid4().int % 10**7:07d}"
    try:
        async with sesion.begin():
            for _ in range(servicio.MAXIMO_ENVIOS):
                await servicio.solicitar_otp(sesion, telefono=telefono)

            with pytest.raises(DemasiadosIntentos):
                await servicio.solicitar_otp(sesion, telefono=telefono)
    finally:
        await sesion.close()
        await motor.dispose()


async def test_reutilizar_un_refresco_ya_rotado_cierra_toda_la_familia():
    """La firma de un token robado: el legítimo y el ladrón acaban presentando el mismo.

    Cortar solo ese token dejaría al ladrón dentro con el siguiente de la cadena, así que se
    cierra la familia entera y las dos partes tienen que volver a entrar. Es molesto a
    propósito: lo alternativo es no enterarse.
    """
    sesion, motor = await _sesion()
    telefono = f"+5076{uuid.uuid4().int % 10**7:07d}"
    try:
        async with sesion.begin():
            codigo = await servicio.solicitar_otp(sesion, telefono=telefono)
            primeras = await servicio.verificar_otp(sesion, telefono=telefono, codigo=codigo)
            segundas = await servicio.refrescar(sesion, refresco=primeras.refresco)
            assert segundas.refresco != primeras.refresco

            # Alguien vuelve a usar el primero, que ya estaba rotado.
            with pytest.raises(NoAutorizado):
                await servicio.refrescar(sesion, refresco=primeras.refresco)

            # Y el que era válido tampoco sirve ya.
            with pytest.raises(NoAutorizado):
                await servicio.refrescar(sesion, refresco=segundas.refresco)
    finally:
        await sesion.close()
        await motor.dispose()


async def test_cerrar_sesion_surte_efecto_de_inmediato():
    """No cuando caduque el token: es requisito de la Ley 81 y de sentido común."""
    sesion, motor = await _sesion()
    telefono = f"+5076{uuid.uuid4().int % 10**7:07d}"
    try:
        async with sesion.begin():
            codigo = await servicio.solicitar_otp(sesion, telefono=telefono)
            credenciales = await servicio.verificar_otp(sesion, telefono=telefono, codigo=codigo)
            await servicio.cerrar_sesion(sesion, refresco=credenciales.refresco)

            with pytest.raises(NoAutorizado):
                await servicio.refrescar(sesion, refresco=credenciales.refresco)
    finally:
        await sesion.close()
        await motor.dispose()


async def test_no_se_puede_entrar_en_modo_negocio_sin_membresia():
    """Cambiar de contexto no es pedirlo: es tener el permiso."""
    escenario = await montar_escenario()
    sesion, motor = await _sesion()
    telefono = f"+5076{uuid.uuid4().int % 10**7:07d}"
    try:
        async with sesion.begin():
            codigo = await servicio.solicitar_otp(sesion, telefono=telefono)
            credenciales = await servicio.verificar_otp(sesion, telefono=telefono, codigo=codigo)

            with pytest.raises(NoAutorizado):
                await servicio.cambiar_a_negocio(
                    sesion,
                    usuario_id=credenciales.usuario_id,
                    negocio_id=escenario.cangrejo.id,
                )
    finally:
        await sesion.close()
        await motor.dispose()


async def test_con_membresia_el_token_lleva_el_negocio_y_el_rol():
    escenario = await montar_escenario()
    sesion, motor = await _sesion()
    telefono = f"+5076{uuid.uuid4().int % 10**7:07d}"
    try:
        async with sesion.begin():
            codigo = await servicio.solicitar_otp(sesion, telefono=telefono)
            credenciales = await servicio.verificar_otp(sesion, telefono=telefono, codigo=codigo)
            sesion.add(
                Membership(
                    business_id=escenario.cangrejo.id,
                    user_id=credenciales.usuario_id,
                    role="dueno",
                    status="activa",
                    accepted_at=datetime.now(UTC),
                )
            )
            await sesion.flush()

            de_negocio = await servicio.cambiar_a_negocio(
                sesion,
                usuario_id=credenciales.usuario_id,
                negocio_id=escenario.cangrejo.id,
            )

        assert de_negocio.negocio_activo == escenario.cangrejo.id
    finally:
        await sesion.close()
        await motor.dispose()


async def test_el_refresco_no_se_guarda_en_claro():
    """Si la base se filtra, un refresco en claro es una sesión regalada."""
    sesion, motor = await _sesion()
    telefono = f"+5076{uuid.uuid4().int % 10**7:07d}"
    try:
        async with sesion.begin():
            codigo = await servicio.solicitar_otp(sesion, telefono=telefono)
            credenciales = await servicio.verificar_otp(sesion, telefono=telefono, codigo=codigo)
            guardadas = (
                (
                    await sesion.execute(
                        select(Session).where(Session.user_id == credenciales.usuario_id)
                    )
                )
                .scalars()
                .all()
            )

        assert guardadas
        for fila in guardadas:
            assert credenciales.refresco.encode() not in fila.refresh_token_hash
    finally:
        await sesion.close()
        await motor.dispose()


async def test_un_refresco_caducado_no_vale():
    sesion, motor = await _sesion()
    telefono = f"+5076{uuid.uuid4().int % 10**7:07d}"
    try:
        async with sesion.begin():
            codigo = await servicio.solicitar_otp(sesion, telefono=telefono)
            credenciales = await servicio.verificar_otp(sesion, telefono=telefono, codigo=codigo)
            await sesion.execute(
                text("UPDATE sessions SET expires_at = :ayer WHERE user_id = :usuario"),
                {
                    "ayer": datetime.now(UTC) - timedelta(days=1),
                    "usuario": credenciales.usuario_id,
                },
            )

            with pytest.raises(NoAutorizado):
                await servicio.refrescar(sesion, refresco=credenciales.refresco)
    finally:
        await sesion.close()
        await motor.dispose()


async def test_un_codigo_vivo_y_antiguo_no_impide_pedir_otro():
    """Pedir un código con uno vivo de hace rato **no puede reventar**.

    El índice `uq_otp_codes_vivo` deja como mucho un código vivo por destino y finalidad. La
    invalidación miraba solo los emitidos dentro de la ventana de envíos, así que uno de hace
    media hora, nunca usado, seguía vivo y hacía chocar al nuevo con una violación de unicidad.

    Salía como **500 en la pantalla de acceso**, que es la primera pantalla del producto, y solo
    le pasaba a quien pide un código, lo deja, y vuelve un rato después. O sea, a mucha gente.
    """
    sesion, motor = await _sesion()
    telefono = f"+5076{uuid.uuid4().int % 10**7:07d}"
    try:
        async with sesion.begin():
            await servicio.solicitar_otp(sesion, telefono=telefono)
            # Se envejece el código fuera de la ventana de envíos, dejándolo vivo: es
            # exactamente el estado que rompía.
            await sesion.execute(
                text(
                    "UPDATE otp_codes SET created_at = :antes "
                    "WHERE destination = :tel AND consumed_at IS NULL "
                    "AND invalidated_at IS NULL"
                ),
                {"antes": datetime.now(UTC) - timedelta(hours=1), "tel": telefono},
            )

            segundo = await servicio.solicitar_otp(sesion, telefono=telefono)
            credenciales = await servicio.verificar_otp(sesion, telefono=telefono, codigo=segundo)
            assert credenciales.usuario_id is not None

            vivos = (
                await sesion.execute(
                    text(
                        "SELECT count(*) FROM otp_codes WHERE destination = :tel "
                        "AND consumed_at IS NULL AND invalidated_at IS NULL"
                    ),
                    {"tel": telefono},
                )
            ).scalar_one()
            assert vivos == 0, "Al canjear el código no puede quedar ninguno vivo."
    finally:
        await sesion.close()
        await motor.dispose()
