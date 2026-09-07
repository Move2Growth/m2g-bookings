"""Entrar con correo y contraseña, contra la base de verdad.

Va aquí y no en dominio porque **lo que garantiza casi todo es la base**: el único del correo,
el hecho de que el bloqueo por intentos sobreviva a la excepción que lo provoca, y que cambiar
la contraseña revoque de verdad las demás sesiones. Con dobles, las tres dirían que sí.

La prueba que importa de este archivo es `test_ocho_fallos_cierran_la_puerta`: si el contador de
intentos se escribiera en la transacción de la petición, se desharía con el `raise` y el bloqueo
sería decorativo. La API respondería 401 para siempre y nadie se enteraría hasta que alguien
probara diez mil contraseñas y entrara.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.errores import (
    CredencialesInvalidas,
    DatoInvalido,
    DemasiadosIntentos,
    YaExiste,
)
from agenda.modelos.identidad import Session, User
from agenda.servicios import identidad as servicio
from pruebas.bd.escenario import URL_DUENO_ASYNC

pytestmark = pytest.mark.bd

CONTRASENA = "una contrasena larga"


async def _sesion() -> tuple[AsyncSession, object]:
    motor = create_async_engine(URL_DUENO_ASYNC, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    return crear(), motor


def _correo() -> str:
    return f"prueba-{uuid.uuid4().hex[:10]}@demo.pa"


async def test_alta_y_entrada():
    """Darse de alta deja dentro, y la cuenta sirve para volver a entrar después."""
    sesion, motor = await _sesion()
    correo = _correo()
    try:
        async with sesion.begin():
            alta = await servicio.registrar(
                sesion, nombre="Yaris Batista", correo=correo, contrasena=CONTRASENA
            )
        assert alta.acceso and alta.refresco

        async with sesion.begin():
            entrada = await servicio.entrar(sesion, correo=correo, contrasena=CONTRASENA)
        assert entrada.usuario_id == alta.usuario_id
    finally:
        await sesion.close()
        await motor.dispose()


async def test_el_correo_no_distingue_mayusculas_ni_espacios():
    """«  ANA@X.COM » y «ana@x.com» son la misma cuenta.

    El único de la base es sobre `lower(email)`. Si el código no normalizara igual, existiría
    una cuenta a la que su dueña no podría entrar escribiendo su propio correo con mayúscula.
    """
    sesion, motor = await _sesion()
    correo = _correo()
    try:
        async with sesion.begin():
            await servicio.registrar(
                sesion, nombre="Ana", correo=correo.upper(), contrasena=CONTRASENA
            )
        async with sesion.begin():
            credenciales = await servicio.entrar(
                sesion, correo=f"  {correo.upper()}  ", contrasena=CONTRASENA
            )
        assert credenciales.acceso
    finally:
        await sesion.close()
        await motor.dispose()


async def test_correo_inexistente_y_contrasena_mala_dan_el_mismo_error():
    """Separarlos le confirma a quien prueba combinaciones qué cuentas existen."""
    sesion, motor = await _sesion()
    correo = _correo()
    try:
        async with sesion.begin():
            await servicio.registrar(sesion, nombre="Ana", correo=correo, contrasena=CONTRASENA)

        with pytest.raises(CredencialesInvalidas):
            async with sesion.begin():
                await servicio.entrar(sesion, correo=correo, contrasena="no es esta ni de lejos")

        with pytest.raises(CredencialesInvalidas):
            async with sesion.begin():
                await servicio.entrar(sesion, correo=_correo(), contrasena=CONTRASENA)
    finally:
        await sesion.close()
        await motor.dispose()


async def test_ocho_fallos_cierran_la_puerta():
    """El bloqueo por intentos **tiene que sobrevivir al `raise` que lo provoca**.

    Es la prueba de que el contador vive en su propia transacción. Si viviera en la de la
    petición, `sesion.begin()` lo desharía en cada fallo, el contador volvería a cero siempre y
    la novena línea de aquí abajo entraría tan tranquila con la contraseña correcta.
    """
    sesion, motor = await _sesion()
    correo = _correo()
    try:
        async with sesion.begin():
            await servicio.registrar(sesion, nombre="Ana", correo=correo, contrasena=CONTRASENA)

        # `pytest.raises` va **por fuera** de `sesion.begin()`, y esa es toda la prueba. Al
        # revés, el bloque de transacción no ve ninguna excepción, confirma tan contento, y el
        # contador se guardaría hasta con el fallo dentro: la prueba pasaría en verde sin
        # comprobar nada. Así se reproduce lo que hace de verdad una petición que falla.
        for _ in range(servicio.MAXIMO_FALLOS):
            with pytest.raises(CredencialesInvalidas):
                async with sesion.begin():
                    await servicio.entrar(sesion, correo=correo, contrasena="no es esta")

        with pytest.raises(DemasiadosIntentos):
            async with sesion.begin():
                await servicio.entrar(sesion, correo=correo, contrasena=CONTRASENA)
    finally:
        await sesion.close()
        await motor.dispose()


async def test_entrar_bien_borra_los_fallos_acumulados():
    """Siete fallos y un acierto no dejan a la cuenta a un fallo de bloquearse mañana."""
    sesion, motor = await _sesion()
    correo = _correo()
    try:
        async with sesion.begin():
            alta = await servicio.registrar(
                sesion, nombre="Ana", correo=correo, contrasena=CONTRASENA
            )

        for _ in range(servicio.MAXIMO_FALLOS - 1):
            with pytest.raises(CredencialesInvalidas):
                async with sesion.begin():
                    await servicio.entrar(sesion, correo=correo, contrasena="no es esta")

        async with sesion.begin():
            await servicio.entrar(sesion, correo=correo, contrasena=CONTRASENA)

        async with sesion.begin():
            usuario = await sesion.get(User, alta.usuario_id)
            assert usuario is not None
            assert usuario.failed_logins == 0
            assert usuario.locked_until is None
    finally:
        await sesion.close()
        await motor.dispose()


async def test_no_se_puede_repetir_el_correo():
    sesion, motor = await _sesion()
    correo = _correo()
    try:
        async with sesion.begin():
            await servicio.registrar(sesion, nombre="Ana", correo=correo, contrasena=CONTRASENA)
        with pytest.raises(YaExiste):
            async with sesion.begin():
                await servicio.registrar(
                    sesion, nombre="Otra", correo=correo.upper(), contrasena=CONTRASENA
                )
    finally:
        await sesion.close()
        await motor.dispose()


async def test_la_contrasena_tiene_un_minimo():
    sesion, motor = await _sesion()
    try:
        with pytest.raises(DatoInvalido):
            async with sesion.begin():
                await servicio.registrar(sesion, nombre="Ana", correo=_correo(), contrasena="corta")
        with pytest.raises(DatoInvalido):
            async with sesion.begin():
                await servicio.registrar(
                    sesion, nombre="Ana", correo=_correo(), contrasena="1234567890123"
                )
    finally:
        await sesion.close()
        await motor.dispose()


async def test_una_cuenta_sin_contrasena_no_entra_con_contrasena():
    """Quien entró alguna vez por código y nunca puso contraseña no tiene una vacía.

    `password_hash` nulo significa «demuestra quién eres por otra vía», no «pasa sin más».
    """
    sesion, motor = await _sesion()
    telefono = f"+5076{uuid.uuid4().int % 10**7:07d}"
    correo = _correo()
    try:
        async with sesion.begin():
            codigo = await servicio.solicitar_otp(sesion, telefono=telefono)
            credenciales = await servicio.verificar_otp(sesion, telefono=telefono, codigo=codigo)
            usuario = await sesion.get(User, credenciales.usuario_id)
            assert usuario is not None
            usuario.email = correo

        with pytest.raises(CredencialesInvalidas):
            async with sesion.begin():
                await servicio.entrar(sesion, correo=correo, contrasena=CONTRASENA)
    finally:
        await sesion.close()
        await motor.dispose()


async def test_cambiar_la_contrasena_cierra_las_demas_sesiones():
    """Es lo que hace quien cree que alguien entró en su cuenta.

    Si el intruso siguiera dentro con su refresco, el gesto no habría servido de nada.
    """
    sesion, motor = await _sesion()
    correo = _correo()
    try:
        async with sesion.begin():
            alta = await servicio.registrar(
                sesion, nombre="Ana", correo=correo, contrasena=CONTRASENA
            )
        async with sesion.begin():
            await servicio.entrar(sesion, correo=correo, contrasena=CONTRASENA)

        async with sesion.begin():
            await servicio.cambiar_contrasena(
                sesion, usuario_id=alta.usuario_id, actual=CONTRASENA, nueva="otra bien larga"
            )

        async with sesion.begin():
            vivas = (
                (
                    await sesion.execute(
                        select(Session).where(
                            Session.user_id == alta.usuario_id, Session.revoked_at.is_(None)
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert vivas == []

        async with sesion.begin():
            await servicio.entrar(sesion, correo=correo, contrasena="otra bien larga")
    finally:
        await sesion.close()
        await motor.dispose()


async def test_cambiar_la_contrasena_exige_la_actual():
    sesion, motor = await _sesion()
    correo = _correo()
    try:
        async with sesion.begin():
            alta = await servicio.registrar(
                sesion, nombre="Ana", correo=correo, contrasena=CONTRASENA
            )
        with pytest.raises(CredencialesInvalidas):
            async with sesion.begin():
                await servicio.cambiar_contrasena(
                    sesion,
                    usuario_id=alta.usuario_id,
                    actual="no es la suya",
                    nueva="otra bien larga",
                )
    finally:
        await sesion.close()
        await motor.dispose()


async def test_verificar_el_telefono_no_cambia_de_cuenta():
    """La prueba que sostiene todo el camino de reserva de una clienta nueva.

    Verificar el teléfono desde una sesión abierta **no puede** abrir otra sesión. Con
    `verificar_otp` —que es *entrar*— la persona acababa dentro de una cuenta recién creada,
    vacía y sin sus citas, y no saltaba ningún error: parecía que había funcionado.
    """
    sesion, motor = await _sesion()
    correo = _correo()
    telefono = f"+5076{uuid.uuid4().int % 10**7:07d}"
    try:
        async with sesion.begin():
            alta = await servicio.registrar(
                sesion, nombre="Ana", correo=correo, contrasena=CONTRASENA
            )
            usuario = await sesion.get(User, alta.usuario_id)
            assert usuario is not None
            assert usuario.phone_e164 is None  # con correo y contraseña no hace falta

        async with sesion.begin():
            codigo = await servicio.solicitar_otp(
                sesion, telefono=telefono, proposito="verificacion_telefono"
            )

        async with sesion.begin():
            await servicio.verificar_telefono_de(
                sesion, usuario_id=alta.usuario_id, telefono=telefono, codigo=codigo
            )

        async with sesion.begin():
            # Sigue siendo **una sola** cuenta con ese número, y es la del alta.
            cuentas = (
                (await sesion.execute(select(User).where(User.phone_e164 == telefono)))
                .scalars()
                .all()
            )
            assert [c.id for c in cuentas] == [alta.usuario_id]
            assert cuentas[0].phone_verified_at is not None
            assert cuentas[0].full_name == "Ana"
    finally:
        await sesion.close()
        await motor.dispose()


async def test_un_telefono_de_otra_cuenta_no_se_puede_robar():
    """Dos personas con el mismo número serían el salón llamando a quien no es."""
    sesion, motor = await _sesion()
    telefono = f"+5076{uuid.uuid4().int % 10**7:07d}"
    try:
        async with sesion.begin():
            primera = await servicio.registrar(
                sesion, nombre="Primera", correo=_correo(), contrasena=CONTRASENA, telefono=telefono
            )
            assert primera.usuario_id

        async with sesion.begin():
            segunda = await servicio.registrar(
                sesion, nombre="Segunda", correo=_correo(), contrasena=CONTRASENA
            )

        async with sesion.begin():
            codigo = await servicio.solicitar_otp(
                sesion, telefono=telefono, proposito="verificacion_telefono"
            )

        with pytest.raises(YaExiste):
            async with sesion.begin():
                await servicio.verificar_telefono_de(
                    sesion, usuario_id=segunda.usuario_id, telefono=telefono, codigo=codigo
                )
    finally:
        await sesion.close()
        await motor.dispose()
