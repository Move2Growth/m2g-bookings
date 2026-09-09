"""Un reintento no puede crear dos citas ni recibir un error que no le corresponde (ADR-0012).

Esto se prueba contra PostgreSQL de verdad y no se puede simular. Lo que hay que ver funcionar
es exactamente lo que solo existe en la base: la **unicidad** de `(key, endpoint)`, que es la
que arbitra entre dos peticiones a la vez, y la **política de fila** de `idempotency_keys`, que
compara el negocio de la fila con el de la sesión — si estuviera mal, la clave se guardaría y
al leerla no se vería, y el reintento crearía la segunda cita sin que nada fallara.

El fallo que esto arregla estaba vivo y se reprodujo contra la API en marcha: reservar dos
veces con la misma clave y el mismo cuerpo daba `201` y luego **`409 SLOT_NO_DISPONIBLE`** —
«ese horario se acaba de ocupar», por una cita que había ocupado él mismo.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agenda.errores import ClaveReutilizada, ReintentoEnVuelo
from agenda.servicios import idempotencia
from pruebas.bd.escenario import montar_escenario

pytestmark = pytest.mark.bd

ENDPOINT = "POST /api/v1/mi/reservas"


async def _sesion(motor, negocio_id: uuid.UUID) -> AsyncSession:
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    sesion = crear()
    await sesion.begin()
    await sesion.execute(
        text("SELECT set_config('app.current_business_id', :negocio, true)"),
        {"negocio": str(negocio_id)},
    )
    return sesion


def _cuerpo(hora: str = "2026-10-01T10:00:00-05:00") -> dict:
    return {"negocio_slug": "barberia", "servicios": ["uno"], "inicio": hora}


async def test_el_reintento_recibe_la_misma_respuesta_y_no_repite_el_trabajo(motor):
    """La segunda vez con la misma clave devuelve **la respuesta guardada**, no un error.

    Es el caso que importa: la respuesta se perdió por el camino, la cita existe, y el cliente
    vuelve a pedir. Lo que tiene que recibir es su cita, con su identificador, para poder
    enseñarla; cualquier otra cosa le hace creer que no reservó.
    """
    escenario = await montar_escenario()
    clave = f"reintento-{uuid.uuid4().hex[:12]}"

    sesion = await _sesion(motor, escenario.cangrejo.id)
    try:
        primera = await idempotencia.reclamar(
            sesion,
            clave=clave,
            endpoint=ENDPOINT,
            cuerpo=_cuerpo(),
            negocio_id=escenario.cangrejo.id,
        )
        assert primera is None, "La primera vez no hay nada guardado: hay que hacer el trabajo."

        await idempotencia.contestar(
            sesion,
            clave=clave,
            endpoint=ENDPOINT,
            estado=201,
            cuerpo={"id": "la-cita", "estado": "confirmada"},
        )
        await sesion.commit()
    finally:
        await sesion.close()

    # Segunda petición: otra transacción, como sería otra petición HTTP de verdad.
    sesion = await _sesion(motor, escenario.cangrejo.id)
    try:
        repetida = await idempotencia.reclamar(
            sesion,
            clave=clave,
            endpoint=ENDPOINT,
            cuerpo=_cuerpo(),
            negocio_id=escenario.cangrejo.id,
        )
        assert repetida is not None, (
            "El reintento no encontró su propia respuesta. Con esto, el segundo intento vuelve "
            "a crear la cita y choca con la restricción de exclusión: la persona lee «ese "
            "horario se acaba de ocupar» por la cita que acaba de hacer ella misma."
        )
        assert repetida.estado == 201
        assert repetida.cuerpo["id"] == "la-cita"
    finally:
        await sesion.rollback()
        await sesion.close()


async def test_el_orden_de_las_claves_del_cuerpo_no_lo_convierte_en_otra_peticion(motor):
    """Mismo cuerpo, distinto orden, sigue siendo un reintento.

    Un cliente no promete el orden de su JSON. Si la huella fuera del texto tal cual, un
    reintento legítimo se leería como una clave reutilizada y le saldría un error inventado.
    """
    escenario = await montar_escenario()
    clave = f"orden-{uuid.uuid4().hex[:12]}"
    derecho = {
        "negocio_slug": "barberia",
        "servicios": ["uno"],
        "inicio": "2026-10-01T10:00:00-05:00",
    }
    del_reves = {
        "inicio": "2026-10-01T10:00:00-05:00",
        "servicios": ["uno"],
        "negocio_slug": "barberia",
    }

    sesion = await _sesion(motor, escenario.cangrejo.id)
    try:
        await idempotencia.reclamar(
            sesion,
            clave=clave,
            endpoint=ENDPOINT,
            cuerpo=derecho,
            negocio_id=escenario.cangrejo.id,
        )
        await idempotencia.contestar(
            sesion, clave=clave, endpoint=ENDPOINT, estado=201, cuerpo={"id": "la-cita"}
        )
        await sesion.commit()
    finally:
        await sesion.close()

    sesion = await _sesion(motor, escenario.cangrejo.id)
    try:
        repetida = await idempotencia.reclamar(
            sesion,
            clave=clave,
            endpoint=ENDPOINT,
            cuerpo=del_reves,
            negocio_id=escenario.cangrejo.id,
        )
        assert repetida is not None and repetida.cuerpo["id"] == "la-cita"
    finally:
        await sesion.rollback()
        await sesion.close()


async def test_la_misma_clave_con_otro_cuerpo_no_recibe_la_respuesta_de_la_anterior(motor):
    """Reusar la clave para otra reserva **no** es un reintento, y contestarle sería mentirle.

    Si se le devolviera la cita anterior, el cliente se quedaría convencido de haber reservado
    las once cuando pidió las doce, y no se enteraría hasta el día de la cita.
    """
    escenario = await montar_escenario()
    clave = f"reusada-{uuid.uuid4().hex[:12]}"

    sesion = await _sesion(motor, escenario.cangrejo.id)
    try:
        await idempotencia.reclamar(
            sesion,
            clave=clave,
            endpoint=ENDPOINT,
            cuerpo=_cuerpo("2026-10-01T11:00:00-05:00"),
            negocio_id=escenario.cangrejo.id,
        )
        await idempotencia.contestar(
            sesion, clave=clave, endpoint=ENDPOINT, estado=201, cuerpo={"id": "las-once"}
        )
        await sesion.commit()
    finally:
        await sesion.close()

    sesion = await _sesion(motor, escenario.cangrejo.id)
    try:
        with pytest.raises(ClaveReutilizada):
            await idempotencia.reclamar(
                sesion,
                clave=clave,
                endpoint=ENDPOINT,
                cuerpo=_cuerpo("2026-10-01T12:00:00-05:00"),
                negocio_id=escenario.cangrejo.id,
            )
    finally:
        await sesion.rollback()
        await sesion.close()


async def test_dos_peticiones_a_la_vez_con_la_misma_clave_acaban_en_una_sola_cita(motor):
    """Las dos a la vez: la segunda **espera** a la primera y se lleva su respuesta.

    Esto no es la teoría del reintento, es lo que hace PostgreSQL y hay que verlo: un
    `INSERT … ON CONFLICT DO NOTHING` contra una fila que otra transacción está insertando
    **no se rinde, se queda esperando** a que esa transacción termine. Y ahí está la parte
    buena: cuando la primera confirma, la segunda encuentra la respuesta ya guardada y la
    devuelve. Con dos dedos impacientes sale **una cita y dos respuestas iguales**.

    Escrito de la forma ingenua —comprobar y luego insertar— aquí habría dos citas o un 409.
    """
    escenario = await montar_escenario()
    clave = f"a-la-vez-{uuid.uuid4().hex[:12]}"
    ya_reclamada = asyncio.Event()

    async def primera() -> None:
        sesion = await _sesion(motor, escenario.cangrejo.id)
        try:
            libre = await idempotencia.reclamar(
                sesion,
                clave=clave,
                endpoint=ENDPOINT,
                cuerpo=_cuerpo(),
                negocio_id=escenario.cangrejo.id,
            )
            assert libre is None
            await idempotencia.contestar(
                sesion, clave=clave, endpoint=ENDPOINT, estado=201, cuerpo={"id": "la-unica"}
            )
            ya_reclamada.set()
            # Se tarda a propósito en confirmar: es la ventana en la que la segunda llega.
            await asyncio.sleep(0.4)
            await sesion.commit()
        finally:
            await sesion.close()

    async def segunda():
        await ya_reclamada.wait()
        sesion = await _sesion(motor, escenario.cangrejo.id)
        try:
            return await idempotencia.reclamar(
                sesion,
                clave=clave,
                endpoint=ENDPOINT,
                cuerpo=_cuerpo(),
                negocio_id=escenario.cangrejo.id,
            )
        finally:
            await sesion.rollback()
            await sesion.close()

    _, repetida = await asyncio.gather(primera(), segunda())

    assert (
        repetida is not None
    ), "La segunda petición no vio la respuesta de la primera y habría creado otra cita."
    assert repetida.cuerpo["id"] == "la-unica"


async def test_la_clave_de_un_salon_no_se_ve_desde_otro(motor):
    """La política de fila también cubre esta tabla, y aquí se comprueba.

    No es celo: si la fila se guardara con el negocio de uno y se leyera sin filtrar, dos
    salones compartirían el pozo de claves y una coincidencia bastaría para que a un cliente le
    devolvieran la cita de otro. Al no verla, el otro salón la reclama como nueva.
    """
    escenario = await montar_escenario()
    clave = f"cruzada-{uuid.uuid4().hex[:12]}"

    sesion = await _sesion(motor, escenario.cangrejo.id)
    try:
        await idempotencia.reclamar(
            sesion,
            clave=clave,
            endpoint=ENDPOINT,
            cuerpo=_cuerpo(),
            negocio_id=escenario.cangrejo.id,
        )
        await idempotencia.contestar(
            sesion, clave=clave, endpoint=ENDPOINT, estado=201, cuerpo={"id": "del-cangrejo"}
        )
        await sesion.commit()
    finally:
        await sesion.close()

    otro = await _sesion(motor, escenario.obarrio.id)
    try:
        # Desde el otro salón la fila no existe, así que el reclamo choca con la unicidad —que
        # sí es global— y se lee como en vuelo. Lo que **no** puede pasar es que le devuelvan
        # «del-cangrejo».
        with pytest.raises(ReintentoEnVuelo):
            await idempotencia.reclamar(
                otro,
                clave=clave,
                endpoint=ENDPOINT,
                cuerpo=_cuerpo(),
                negocio_id=escenario.obarrio.id,
            )
    finally:
        await otro.rollback()
        await otro.close()
