"""La consola interna: entrar con 2FA y que suspender signifique algo (ADM-2, ADM-5).

Dos cosas se comprueban aquí y las dos son de las que no avisan cuando se rompen:

* **Entrar exige las tres credenciales** y las tres fallan con el mismo error. Si el segundo
  factor se pudiera saltar, el back-office de toda la plataforma quedaría detrás de una
  contraseña.
* **Suspender un negocio lo saca del marketplace de verdad**, no solo de una pantalla. Se
  comprueba desde el **rol público**, que es quien sirve la portada: si el negocio siguiera
  visible ahí, la suspensión sería un adorno.

Y una que se ve poco y cuesta cara: un token de consola **no vale** en `/mi` ni en `/negocio`.
Están firmados con la misma clave porque es el mismo proceso, así que sin la marca de
superficie una sesión de consola serviría para todo.
"""

from __future__ import annotations

import uuid

import jwt
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agenda.ajustes import obtener_ajustes
from agenda.api.dependencias import _leer_token
from agenda.dominio import totp
from agenda.errores import CredencialesInvalidas, NoAutorizado
from agenda.servicios import consola as servicio_consola
from pruebas.bd.conftest import URL_APP
from pruebas.bd.escenario_panel import conexion_de_dueno, montar_salon

pytestmark = pytest.mark.bd

ajustes = obtener_ajustes()

#: La consola se conecta con el rol del back-office, que es el único con permiso sobre
#: `admin_users` y `admin_sessions`.
URL_CONSOLA = URL_APP.replace("agenda_api:", "agenda_admin:")

#: La contraseña de las pruebas **no es un secreto del proyecto**: se genera aquí, se usa aquí
#: y no vale en ningún sitio. La cuenta real se crea con `python -m agenda.consola_alta`.
PASSWORD_DE_PRUEBA = "consola-de-pruebas-no-sirve-fuera"


async def _crear_admin() -> tuple[str, bytes]:
    """Da de alta una cuenta de consola y devuelve su correo y el secreto de su 2FA."""
    email = f"consola-{uuid.uuid4().hex[:8]}@m2g.dev"
    secreto = totp.secreto_nuevo()
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text(
                """
                INSERT INTO admin_users (email, full_name, password_hash, totp_secret, role)
                VALUES (:email, 'Equipo M2G', :hash, :secreto, 'superadmin')
                """
            ),
            {
                "email": email,
                "hash": servicio_consola.hashear_password(PASSWORD_DE_PRUEBA),
                "secreto": secreto,
            },
        )
    return email, secreto


async def _sesion_consola() -> AsyncSession:
    motor = create_async_engine(URL_CONSOLA, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    sesion = crear()
    await sesion.begin()
    return sesion


async def test_entrar_con_las_tres_credenciales_abre_sesion():
    email, secreto = await _crear_admin()

    sesion = await _sesion_consola()
    try:
        credenciales = await servicio_consola.entrar(
            sesion,
            email=email,
            password=PASSWORD_DE_PRUEBA,
            codigo_2fa=totp.codigo(secreto),
        )
        assert credenciales.rol == "superadmin"
        assert credenciales.refresco
        await sesion.commit()
    finally:
        await sesion.close()


async def test_sin_el_segundo_factor_no_se_entra():
    """La contraseña correcta **no basta**. El 2FA no es opcional en la consola (ADR-0006)."""
    email, _ = await _crear_admin()

    sesion = await _sesion_consola()
    try:
        with pytest.raises(CredencialesInvalidas):
            await servicio_consola.entrar(
                sesion, email=email, password=PASSWORD_DE_PRUEBA, codigo_2fa="000000"
            )
    finally:
        await sesion.rollback()
        await sesion.close()


async def test_la_contrasena_equivocada_da_el_mismo_error_que_el_correo_inexistente():
    """Distinguirlos le diría a quien prueba combinaciones qué correos son de verdad."""
    email, secreto = await _crear_admin()

    sesion = await _sesion_consola()
    try:
        with pytest.raises(CredencialesInvalidas) as mala_clave:
            await servicio_consola.entrar(
                sesion, email=email, password="otra-cosa", codigo_2fa=totp.codigo(secreto)
            )
        with pytest.raises(CredencialesInvalidas) as no_existe:
            await servicio_consola.entrar(
                sesion,
                email="nadie@m2g.dev",
                password=PASSWORD_DE_PRUEBA,
                codigo_2fa=totp.codigo(secreto),
            )
        assert str(mala_clave.value) == str(no_existe.value)
    finally:
        await sesion.rollback()
        await sesion.close()


async def test_reutilizar_un_refresco_ya_rotado_cierra_la_familia():
    """Es la firma de un token robado: el legítimo ya rotó y siguió su camino.

    Sin cerrar la familia entera, el ladrón y la víctima se turnarían indefinidamente y ninguno
    de los dos notaría nada.
    """
    email, secreto = await _crear_admin()

    sesion = await _sesion_consola()
    try:
        primera = await servicio_consola.entrar(
            sesion, email=email, password=PASSWORD_DE_PRUEBA, codigo_2fa=totp.codigo(secreto)
        )
        await sesion.commit()
    finally:
        await sesion.close()

    sesion = await _sesion_consola()
    try:
        await servicio_consola.refrescar(sesion, refresco=primera.refresco)
        await sesion.commit()
    finally:
        await sesion.close()

    # El mismo refresco, otra vez: ya está rotado.
    sesion = await _sesion_consola()
    try:
        with pytest.raises(NoAutorizado):
            await servicio_consola.refrescar(sesion, refresco=primera.refresco)
        await sesion.commit()
    finally:
        await sesion.close()

    async with conexion_de_dueno() as sesion:
        vivas = (
            await sesion.execute(
                text(
                    """
                    SELECT count(*) FROM admin_sessions s
                    JOIN admin_users u ON u.id = s.admin_user_id
                    WHERE u.email = :email AND s.revoked_at IS NULL
                    """
                ),
                {"email": email},
            )
        ).scalar_one()
    assert vivas == 0, "Al detectar el reúso hay que cerrar la familia entera, no solo esa fila."


async def test_un_token_de_consola_no_sirve_en_la_superficie_del_cliente():
    """Misma clave de firma, superficies distintas. La marca del token es el separador."""
    email, secreto = await _crear_admin()

    sesion = await _sesion_consola()
    try:
        credenciales = await servicio_consola.entrar(
            sesion, email=email, password=PASSWORD_DE_PRUEBA, codigo_2fa=totp.codigo(secreto)
        )
        await sesion.commit()
    finally:
        await sesion.close()

    # El token es válido y está firmado por nosotros…
    assert jwt.decode(credenciales.acceso, ajustes.secret_key, algorithms=["HS256"])

    # …pero la puerta del cliente lo rechaza.
    with pytest.raises(NoAutorizado) as fallo:
        _leer_token(f"Bearer {credenciales.acceso}")
    assert "consola" in str(fallo.value)


async def test_suspender_saca_al_negocio_del_marketplace(motor):
    """La comprobación que importa: **desde el rol público**, el negocio deja de existir.

    Comprobarlo con el rol de la aplicación no valdría de nada: quien sirve la portada es
    `agenda_publico`, y su política mira `status = 'publicado'`. Si la suspensión no cambiara
    eso, el salón seguiría saliendo en la búsqueda con un cartel de suspendido en el panel.
    """
    salon = await montar_salon()

    motor_publico = create_async_engine(
        URL_APP.replace("agenda_api:", "agenda_publico:"), poolclass=None
    )
    crear_publica = async_sessionmaker(motor_publico, class_=AsyncSession, expire_on_commit=False)
    try:
        async with crear_publica() as publica, publica.begin():
            antes = (
                await publica.execute(
                    text("SELECT count(*) FROM businesses WHERE id = :negocio"),
                    {"negocio": salon.negocio_id},
                )
            ).scalar_one()
        assert antes == 1, "El escenario monta el salón publicado y tiene que verse."

        sesion = await _sesion_consola()
        try:
            await sesion.execute(
                text(
                    """
                    UPDATE businesses
                       SET status = 'suspendido', suspended_at = now(),
                           suspension_reason = 'prueba'
                     WHERE id = :negocio
                    """
                ),
                {"negocio": salon.negocio_id},
            )
            await sesion.commit()
        finally:
            await sesion.close()

        async with crear_publica() as publica, publica.begin():
            despues = (
                await publica.execute(
                    text("SELECT count(*) FROM businesses WHERE id = :negocio"),
                    {"negocio": salon.negocio_id},
                )
            ).scalar_one()
        assert despues == 0, "Un negocio suspendido sigue visible para el rol del marketplace."
    finally:
        await motor_publico.dispose()


async def test_suspender_no_borra_ni_una_cita(motor):
    """Suspender **no puede parecerse a borrar** (ADR-0010): regularizar y volver es inmediato.

    Las citas, los clientes y la agenda siguen ahí; lo único que cambia es que el salón deja de
    aparecer y de recibir reservas nuevas.
    """
    salon = await montar_salon()

    sesion = await _sesion_consola()
    try:
        await sesion.execute(
            text("UPDATE businesses SET status = 'suspendido' WHERE id = :negocio"),
            {"negocio": salon.negocio_id},
        )
        citas = (
            await sesion.execute(
                text("SELECT count(*) FROM bookings WHERE business_id = :negocio"),
                {"negocio": salon.negocio_id},
            )
        ).scalar_one()
        await sesion.commit()
    finally:
        await sesion.close()

    assert citas == 2, "Suspender ha hecho desaparecer citas, y no puede."
