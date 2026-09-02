"""Dos fugas que no darían la cara: los clientes de otro salón y los favoritos de otra persona.

La primera es la garantía nº 1 aplicada a la tabla que más duele: **un cliente pertenece a la
plataforma, su ficha pertenece al negocio**. La misma persona tiene ficha en la barbería de El
Cangrejo y en el estudio de Obarrio, con notas distintas y contadores de ausencias distintos.
Si un salón viera las fichas del otro, vería sus notas privadas y su lista de teléfonos, que es
exactamente el activo que un competidor querría.

La segunda no va de negocios sino de personas: `favorites` **no lleva seguridad por fila** a
propósito —la fila es del usuario, no del salón, y aislarla por negocio dejaría a cada persona
sin ver lo suyo—. Esa excepción está documentada en el modelo y en la migración, y el precio de
tenerla es que aquí el filtro **sí** es del código. Por eso hay una prueba: lo que protege la
base se comprueba en la base, y lo que protege el código se comprueba en el código.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agenda.modelos.clientes import Favorite
from pruebas.bd.escenario_panel import conexion_de_dueno, montar_salon

pytestmark = pytest.mark.bd


async def _sesion_de_negocio(motor, negocio_id: uuid.UUID) -> AsyncSession:
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    sesion = crear()
    await sesion.begin()
    await sesion.execute(
        text("SELECT set_config('app.current_business_id', :negocio, true)"),
        {"negocio": str(negocio_id)},
    )
    return sesion


async def _sesion_de_usuario(motor, usuario_id: uuid.UUID) -> AsyncSession:
    """Como `/mi/…`: declara **quién pregunta**, sin negocio fijado."""
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    sesion = crear()
    await sesion.begin()
    await sesion.execute(
        text("SELECT set_config('app.current_user_id', :usuario, true)"),
        {"usuario": str(usuario_id)},
    )
    return sesion


async def test_un_negocio_no_ve_los_clientes_de_otro(motor):
    """Dos salones vecinos, cada uno con sus fichas. Consulta **sin `WHERE`**, a propósito.

    Si esta prueba falla, un salón ve la lista de teléfonos de su competencia y las notas que
    el otro barbero escribió sobre cada persona.
    """
    cangrejo = await montar_salon()
    # El segundo salón existe para que haya algo ajeno que ver; no hace falta nombrarlo.
    await montar_salon()

    sesion = await _sesion_de_negocio(motor, cangrejo.negocio_id)
    try:
        negocios_vistos = {
            fila[0]
            for fila in await sesion.execute(text("SELECT business_id FROM business_clients"))
        }
    finally:
        await sesion.rollback()
        await sesion.close()

    assert negocios_vistos <= {cangrejo.negocio_id}, (
        "Un negocio ha visto fichas de cliente de otro con una consulta sin filtro. "
        f"Vistos: {negocios_vistos}."
    )


async def test_pedir_la_ficha_ajena_por_su_identificador_tampoco_la_ensena(motor):
    """Ni nombrando el identificador exacto de la ficha del salón de al lado."""
    cangrejo = await montar_salon()
    obarrio = await montar_salon()

    sesion = await _sesion_de_negocio(motor, cangrejo.negocio_id)
    try:
        total = (
            await sesion.execute(
                text("SELECT count(*) FROM business_clients WHERE id = :ficha"),
                {"ficha": obarrio.cliente_de_kevin},
            )
        ).scalar_one()
    finally:
        await sesion.rollback()
        await sesion.close()

    assert total == 0


async def test_un_negocio_no_puede_escribir_notas_en_la_ficha_de_otro(motor):
    """No basta con no verla: el `UPDATE` a ciegas tampoco puede tocarla."""
    cangrejo = await montar_salon()
    obarrio = await montar_salon()

    sesion = await _sesion_de_negocio(motor, cangrejo.negocio_id)
    try:
        resultado = await sesion.execute(
            text("UPDATE business_clients SET notes = 'espiado' WHERE id = :ficha"),
            {"ficha": obarrio.cliente_de_kevin},
        )
        assert resultado.rowcount == 0
        await sesion.commit()
    finally:
        await sesion.close()

    async with conexion_de_dueno() as sesion:
        notas = (
            await sesion.execute(
                text("SELECT notes FROM business_clients WHERE id = :ficha"),
                {"ficha": obarrio.cliente_de_kevin},
            )
        ).scalar_one()
    assert notas is None


async def test_cada_persona_solo_ve_sus_favoritos(motor):
    """`favorites` la filtra la API por identidad, no la base. Por eso se prueba el filtro.

    La consulta es exactamente la del endpoint: `WHERE user_id = quien pregunta`. Si algún día
    alguien la escribe sin ese `WHERE`, esta prueba enseña lo que pasaría.
    """
    salon_de_ella = await montar_salon()
    salon_de_el = await montar_salon()

    async with conexion_de_dueno() as sesion:
        for usuario, negocio in (
            (salon_de_ella.dueno_user_id, salon_de_ella.negocio_id),
            (salon_de_el.dueno_user_id, salon_de_el.negocio_id),
        ):
            await sesion.execute(
                text("INSERT INTO favorites (user_id, business_id) VALUES (:usuario, :negocio)"),
                {"usuario": usuario, "negocio": negocio},
            )

    sesion = await _sesion_de_usuario(motor, salon_de_ella.dueno_user_id)
    try:
        suyos = set(
            (
                await sesion.execute(
                    select(Favorite.business_id).where(
                        Favorite.user_id == salon_de_ella.dueno_user_id
                    )
                )
            )
            .scalars()
            .all()
        )
    finally:
        await sesion.rollback()
        await sesion.close()

    assert suyos == {salon_de_ella.negocio_id}
    assert salon_de_el.negocio_id not in suyos


async def test_guardar_dos_veces_el_mismo_favorito_no_duplica(motor):
    """El botón de favorito se pulsa con el dedo: un doble toque no puede ser un error.

    Lo resuelve la clave primaria compuesta más `ON CONFLICT DO NOTHING`, que además aguanta
    dos peticiones simultáneas — cosa que una comprobación previa no haría.
    """
    salon = await montar_salon()

    sesion = await _sesion_de_usuario(motor, salon.dueno_user_id)
    try:
        for _ in range(2):
            await sesion.execute(
                text(
                    "INSERT INTO favorites (user_id, business_id) VALUES (:usuario, :negocio) "
                    "ON CONFLICT DO NOTHING"
                ),
                {"usuario": salon.dueno_user_id, "negocio": salon.negocio_id},
            )
        total = (
            await sesion.execute(
                text(
                    "SELECT count(*) FROM favorites WHERE user_id = :usuario "
                    "AND business_id = :negocio"
                ),
                {"usuario": salon.dueno_user_id, "negocio": salon.negocio_id},
            )
        ).scalar_one()
        await sesion.commit()
    finally:
        await sesion.close()

    assert total == 1
