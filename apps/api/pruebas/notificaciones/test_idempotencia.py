"""Encolar dos veces el mismo hecho deja **una** fila. Contra PostgreSQL, no contra un `if`.

Esta es la prueba que justifica que la cola sea una tabla. Quien impide el duplicado es el
índice único sobre `idempotency_key`, así que probarlo con un diccionario en memoria
demostraría que el diccionario funciona. Aquí se inserta de verdad, dos veces, y se cuenta.

Y se hace en **dos transacciones distintas**, no en una: el caso real es el planificador
ejecutándose dos veces, o dos trabajadores a la vez, no dos líneas seguidas de la misma
función.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from agenda.notificaciones.cola import Hecho, clave_de_idempotencia, encolar
from pruebas.notificaciones.escenario import montar_negocio

pytestmark = pytest.mark.bd


async def _contar(abrir_negocio, negocio_id: uuid.UUID, clave: str) -> int:
    async with abrir_negocio(negocio_id) as sesion:
        return (
            await sesion.execute(
                text("SELECT count(*) FROM notifications WHERE idempotency_key = :clave"),
                {"clave": clave},
            )
        ).scalar_one()


async def test_encolar_el_mismo_hecho_dos_veces_deja_una_sola_fila(abrir_negocio):
    """El segundo intento devuelve `None` y no inserta. **`None` no es un error.**

    Es el resultado correcto de un reintento: quien llama no tiene nada que arreglar. Si esto
    fallara, la clienta recibiría dos recordatorios de la misma cita a las siete de la mañana,
    que es exactamente la queja que el diseño existe para evitar.
    """
    negocio = await montar_negocio()
    reserva_id = uuid.uuid4()
    cita = datetime.now(UTC) + timedelta(days=1)

    async def intentar() -> uuid.UUID | None:
        async with abrir_negocio(negocio.id) as sesion:
            return await encolar(
                sesion,
                hecho=Hecho.RECORDATORIO_24H,
                entidad="booking",
                entidad_id=reserva_id,
                canal="whatsapp",
                destino=negocio.telefono_de_la_clienta,
                destinatario="cliente",
                negocio_id=negocio.id,
                programado_para=cita - timedelta(hours=24),
                caduca_en=cita,
            )

    primera = await intentar()
    segunda = await intentar()

    clave = clave_de_idempotencia(Hecho.RECORDATORIO_24H, "booking", reserva_id)
    assert primera is not None, "La primera vez tiene que encolar."
    assert segunda is None, (
        "La segunda inserción devolvió un identificador: el conflicto no se tragó y hay dos "
        "mensajes para el mismo hecho."
    )
    assert await _contar(abrir_negocio, negocio.id, clave) == 1


async def test_dos_hechos_distintos_sobre_la_misma_cita_son_dos_mensajes(abrir_negocio):
    """El de 24 h y el de 2 h son hechos distintos y **tienen que** convivir.

    Es el espejo de la prueba anterior y hace falta: una clave demasiado ancha —por reserva en
    vez de por hecho— dejaría a la clienta sin el recordatorio de la mañana de la cita.
    """
    negocio = await montar_negocio()
    reserva_id = uuid.uuid4()
    cita = datetime.now(UTC) + timedelta(days=1)

    async with abrir_negocio(negocio.id) as sesion:
        for hecho, horas in ((Hecho.RECORDATORIO_24H, 24), (Hecho.RECORDATORIO_2H, 2)):
            creada = await encolar(
                sesion,
                hecho=hecho,
                entidad="booking",
                entidad_id=reserva_id,
                canal="whatsapp",
                destino=negocio.telefono_de_la_clienta,
                destinatario="cliente",
                negocio_id=negocio.id,
                programado_para=cita - timedelta(hours=horas),
                caduca_en=cita,
            )
            assert creada is not None, f"El hecho {hecho} no llegó a encolarse."

    async with abrir_negocio(negocio.id) as sesion:
        total = (
            await sesion.execute(
                text("SELECT count(*) FROM notifications WHERE idempotency_key LIKE :patron"),
                {"patron": f"%:booking:{reserva_id}"},
            )
        ).scalar_one()
    assert total == 2


async def test_el_sufijo_permite_repetir_un_hecho_cuando_toca(abrir_negocio):
    """El aviso de citas sin cerrar es uno por negocio **y por día**: la fecha entra en la clave.

    Sin el sufijo, el aviso del martes impediría el del miércoles y el negocio dejaría de
    enterarse a partir del segundo día.
    """
    negocio = await montar_negocio()
    ahora = datetime.now(UTC)

    async with abrir_negocio(negocio.id) as sesion:
        hoy = await encolar(
            sesion,
            hecho=Hecho.CITAS_SIN_CERRAR,
            entidad="business",
            entidad_id=negocio.id,
            sufijo_de_clave="2026-09-01",
            canal="whatsapp",
            destino="+50760000000",
            destinatario="negocio",
            negocio_id=negocio.id,
            programado_para=ahora,
        )
        manana = await encolar(
            sesion,
            hecho=Hecho.CITAS_SIN_CERRAR,
            entidad="business",
            entidad_id=negocio.id,
            sufijo_de_clave="2026-09-02",
            canal="whatsapp",
            destino="+50760000000",
            destinatario="negocio",
            negocio_id=negocio.id,
            programado_para=ahora,
        )

    assert hoy is not None and manana is not None
    assert hoy != manana
