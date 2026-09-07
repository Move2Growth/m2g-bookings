"""La seguridad por fila de la tabla nueva y del perfil que cada quien puede editar.

Todo lo de aquí se comprueba **contra el catálogo y los roles de verdad**, no leyendo el
código: una política mal escrita no falla, no avisa y no se nota. Las dos formas de fallar son
opuestas y las dos están cubiertas —que se vea de más y que no se vea nada—.

Cada prueba de este archivo se comprobó **rompiéndola a propósito** antes de darla por buena:
quitando la cláusula que defiende, la prueba falla. Una prueba de RLS que pasa con la política
borrada es peor que no tenerla, porque da permiso para dejar de mirar.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pruebas.bd.conftest import URL_APP
from pruebas.bd.escenario_panel import conexion_de_dueno, montar_salon
from pruebas.bd.escenario_profesional import montar_salon_con_perfiles

pytestmark = pytest.mark.bd

URL_PUBLICA = URL_APP.replace("agenda_api:", "agenda_publico:")


@asynccontextmanager
async def sesion_publica() -> AsyncIterator[AsyncSession]:
    """El rol del marketplace, el mismo con el que corre de verdad.

    Probar esto con el rol del negocio taparía cualquier permiso que falte y cualquier
    política que no esté: es el error que convierte una prueba de aislamiento en decoración.
    """
    motor = create_async_engine(URL_PUBLICA, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    try:
        async with crear() as sesion, sesion.begin():
            yield sesion
    finally:
        await motor.dispose()


@asynccontextmanager
async def sesion_de_profesional(
    negocio_id: uuid.UUID, staff_id: uuid.UUID
) -> AsyncIterator[AsyncSession]:
    """El rol de la API con negocio **y profesional** declarados, como en `dependencias.py`."""
    motor = create_async_engine(URL_APP, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    try:
        async with crear() as sesion, sesion.begin():
            await sesion.execute(
                text("SELECT set_config('app.current_business_id', :negocio, true)"),
                {"negocio": str(negocio_id)},
            )
            await sesion.execute(
                text("SELECT set_config('app.current_staff_id', :staff, true)"),
                {"staff": str(staff_id)},
            )
            yield sesion
    finally:
        await motor.dispose()


async def _fotos_publicas(staff_id: uuid.UUID) -> list[uuid.UUID]:
    async with sesion_publica() as sesion:
        filas = await sesion.execute(
            text("SELECT id FROM staff_media WHERE staff_id = :staff"), {"staff": str(staff_id)}
        )
        return [fila[0] for fila in filas]


# ── Que se vea lo que se tiene que ver ────────────────────────────────────────────────────


async def test_el_marketplace_ve_las_fotos_de_un_profesional_visible():
    """El caso contrario del que suele preocupar: **una tabla nueva sin política no se ve.**

    Si esta prueba falla, la galería sale vacía en el perfil público y parece un fallo del
    código de pintado. Se descubre después de un rato largo mirando el sitio equivocado.
    """
    montado = await montar_salon_con_perfiles()
    assert set(await _fotos_publicas(montado.salon.kevin.id)) == {
        montado.foto_de_trabajo,
        montado.foto_de_galeria,
    }


async def test_el_marketplace_ve_que_servicios_hace_cada_quien():
    """Sin `staff_services` abierta al rol público no hay «profesional → servicio → hora»."""
    montado = await montar_salon_con_perfiles()
    async with sesion_publica() as sesion:
        filas = await sesion.execute(
            text("SELECT service_id FROM staff_services WHERE staff_id = :staff"),
            {"staff": str(montado.salon.kevin.id)},
        )
    assert [fila[0] for fila in filas] == [montado.salon.servicio_id]


# ── Que no se vea lo que no se tiene que ver ──────────────────────────────────────────────


async def test_ocultar_al_profesional_apaga_sus_fotos_de_golpe():
    """Quitarle la visibilidad en el marketplace apaga su galería **sin tocar la aplicación**.

    Es la mitad de la política que se olvida siempre: si solo se atara al negocio publicado,
    ocultar a una persona la seguiría enseñando entera a través de sus fotos.
    """
    montado = await montar_salon_con_perfiles()
    assert await _fotos_publicas(montado.salon.kevin.id)

    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("UPDATE staff_profiles SET visible_in_marketplace = false WHERE id = :id"),
            {"id": montado.salon.kevin.id},
        )

    assert await _fotos_publicas(montado.salon.kevin.id) == []


async def test_dar_de_baja_al_profesional_apaga_sus_fotos():
    montado = await montar_salon_con_perfiles()
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("UPDATE staff_profiles SET active = false WHERE id = :id"),
            {"id": montado.salon.kevin.id},
        )
    assert await _fotos_publicas(montado.salon.kevin.id) == []


async def test_despublicar_el_salon_apaga_las_fotos_de_todo_su_equipo():
    """Despublicar tiene que apagar el perfil **entero de una vez**, no tabla a tabla."""
    montado = await montar_salon_con_perfiles()
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("UPDATE businesses SET status = 'borrador' WHERE id = :id"),
            {"id": montado.salon.negocio_id},
        )
    assert await _fotos_publicas(montado.salon.kevin.id) == []


async def test_una_foto_sin_aprobar_no_sale_en_el_perfil_publico():
    """Es exactamente el incidente que la moderación existe para evitar."""
    montado = await montar_salon_con_perfiles()
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("UPDATE staff_media SET moderation_status = 'pendiente' WHERE id = :id"),
            {"id": montado.foto_de_trabajo},
        )
    assert await _fotos_publicas(montado.salon.kevin.id) == [montado.foto_de_galeria]


async def test_las_fotos_de_un_salon_no_se_ven_desde_otro():
    """Garantía nº 1 aplicada a la tabla nueva, con el rol real de la aplicación."""
    uno = await montar_salon_con_perfiles()
    otro = await montar_salon_con_perfiles()

    motor = create_async_engine(URL_APP, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    try:
        async with crear() as sesion, sesion.begin():
            await sesion.execute(
                text("SELECT set_config('app.current_business_id', :negocio, true)"),
                {"negocio": str(uno.salon.negocio_id)},
            )
            # **Sin `WHERE business_id`**, a propósito: lo que se prueba es que la base filtra,
            # no que el `WHERE` de la consulta esté bien escrito.
            filas = await sesion.execute(text("SELECT business_id FROM staff_media"))
            negocios = {fila[0] for fila in filas}
    finally:
        await motor.dispose()

    assert negocios == {uno.salon.negocio_id}
    assert otro.salon.negocio_id not in negocios


# ── Lo que cada profesional puede tocar ───────────────────────────────────────────────────


async def test_un_profesional_no_ve_ni_toca_las_fotos_de_su_companera():
    """Su portafolio es suyo. Lo impide PostgreSQL, no un `if` del endpoint."""
    montado = await montar_salon_con_perfiles()
    async with conexion_de_dueno() as sesion:
        foto_de_marielys = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO staff_media (id, business_id, staff_id, storage_key)
                    VALUES (gen_random_uuid(), :negocio, :staff, '/fotos/spa.webp')
                    RETURNING id
                    """
                ),
                {
                    "negocio": montado.salon.negocio_id,
                    "staff": montado.salon.marielys.id,
                },
            )
        ).scalar_one()

    async with sesion_de_profesional(montado.salon.negocio_id, montado.salon.kevin.id) as sesion:
        visibles = {fila[0] for fila in await sesion.execute(text("SELECT id FROM staff_media"))}
        assert foto_de_marielys not in visibles
        assert montado.foto_de_trabajo in visibles

        borradas = await sesion.execute(
            text("DELETE FROM staff_media WHERE id = :id"), {"id": foto_de_marielys}
        )
        assert borradas.rowcount == 0


async def test_un_profesional_no_puede_colgar_una_foto_a_nombre_de_otra_persona():
    """Sin esto, «quién hizo qué» se podría escribir con el nombre de la compañera."""
    montado = await montar_salon_con_perfiles()
    async with sesion_de_profesional(montado.salon.negocio_id, montado.salon.kevin.id) as sesion:
        with pytest.raises((IntegrityError, ProgrammingError)):
            await sesion.execute(
                text(
                    """
                    INSERT INTO staff_media (id, business_id, staff_id, storage_key)
                    VALUES (gen_random_uuid(), :negocio, :staff, '/fotos/spa.webp')
                    """
                ),
                {
                    "negocio": montado.salon.negocio_id,
                    "staff": montado.salon.marielys.id,
                },
            )


async def test_un_profesional_edita_su_ficha_pero_no_la_de_su_companera():
    """La 0009 abre el `UPDATE` de `staff_profiles` **solo sobre la fila propia**.

    Las dos mitades importan: si se abriera de más, cualquiera cambiaría el titular de la
    compañera; si no se abriera, el encargo «que el profesional edite su perfil» no se cumple.
    """
    montado = await montar_salon_con_perfiles()
    async with sesion_de_profesional(montado.salon.negocio_id, montado.salon.kevin.id) as sesion:
        propia = await sesion.execute(
            text("UPDATE staff_profiles SET headline = 'Barbero y colorista' WHERE id = :id"),
            {"id": montado.salon.kevin.id},
        )
        assert propia.rowcount == 1

        ajena = await sesion.execute(
            text("UPDATE staff_profiles SET headline = 'Yo mando aquí' WHERE id = :id"),
            {"id": montado.salon.marielys.id},
        )
        assert ajena.rowcount == 0


async def test_un_profesional_sigue_sin_poder_crear_ni_borrar_fichas():
    """Dar de alta y dar de baja es del dueño (STF-3). La 0009 no lo tocó."""
    montado = await montar_salon_con_perfiles()
    async with sesion_de_profesional(montado.salon.negocio_id, montado.salon.kevin.id) as sesion:
        with pytest.raises((IntegrityError, ProgrammingError)):
            await sesion.execute(
                text(
                    """
                    INSERT INTO staff_profiles (id, business_id, display_name)
                    VALUES (gen_random_uuid(), :negocio, 'Alguien que me invento')
                    """
                ),
                {"negocio": montado.salon.negocio_id},
            )

    async with sesion_de_profesional(montado.salon.negocio_id, montado.salon.kevin.id) as sesion:
        borradas = await sesion.execute(
            text("DELETE FROM staff_profiles WHERE id = :id"),
            {"id": montado.salon.marielys.id},
        )
        assert borradas.rowcount == 0


# ── Lo que la base no deja escribir ───────────────────────────────────────────────────────


async def test_el_slug_es_unico_dentro_del_salon_y_libre_entre_salones():
    """La misma persona puede ser `yaris` en dos salones; dos `yaris` en uno, no.

    Que sea único **por negocio** y no global no es un detalle: un único global obligaría a la
    segunda Yaris a llamarse `yaris-2` en un salón donde no hay ninguna otra.
    """
    uno = await montar_salon()
    otro = await montar_salon()

    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("UPDATE staff_profiles SET slug = 'yaris' WHERE id = :id"),
            {"id": uno.kevin.id},
        )
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("UPDATE staff_profiles SET slug = 'yaris' WHERE id = :id"),
            {"id": otro.kevin.id},
        )

    with pytest.raises(IntegrityError):
        async with conexion_de_dueno() as sesion:
            await sesion.execute(
                text("UPDATE staff_profiles SET slug = 'yaris' WHERE id = :id"),
                {"id": uno.marielys.id},
            )


async def test_un_slug_dado_de_baja_libera_el_nombre():
    """Quien se va no puede quedarse ocupando el nombre bonito de quien llega."""
    salon = await montar_salon()
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("UPDATE staff_profiles SET slug = 'yaris', deleted_at = now() WHERE id = :id"),
            {"id": salon.kevin.id},
        )
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text("UPDATE staff_profiles SET slug = 'yaris' WHERE id = :id"),
            {"id": salon.marielys.id},
        )


@pytest.mark.parametrize(
    ("columna", "valor"),
    [
        ("instagram", "https://instagram.com/yaris"),
        ("instagram", "yaris/nails"),
        ("facebook", "https://facebook.com/yaris"),
        ("x", "yaris.nails"),
        ("slug", "Kevin Ortega"),
    ],
)
async def test_la_base_no_deja_guardar_una_url_donde_va_un_usuario(columna, valor):
    """**La defensa de verdad de «el usuario, no la URL»**, y está en la base.

    El endpoint normaliza, sí. Pero el endpoint es lo que un compañero futuro puede olvidar
    escribir; la restricción no. En estos patrones no cabe ni una barra ni dos puntos.
    """
    salon = await montar_salon()
    with pytest.raises(IntegrityError):
        async with conexion_de_dueno() as sesion:
            await sesion.execute(
                text(f"UPDATE staff_profiles SET {columna} = :valor WHERE id = :id"),
                {"valor": valor, "id": salon.kevin.id},
            )
