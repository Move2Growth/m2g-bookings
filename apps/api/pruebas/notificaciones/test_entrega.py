"""Entregar: lo que caduca se descarta, lo vivo sale, y los reintentos tienen tope.

Todo se ejecuta con el **proveedor de desarrollo**: escribe en un archivo temporal y no llama a
nadie. Estas pruebas pasan en una máquina recién clonada, sin una sola credencial de Meta, que
es justamente lo que ADR-0007 quería comprar con la interfaz de proveedores.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from agenda.modelos.notificaciones import Notification
from agenda.notificaciones.cola import (
    Hecho,
    PoliticaDeReintentos,
    encolar,
    entregar,
    entregar_pendientes,
)
from agenda.notificaciones.proveedores import (
    MensajeSaliente,
    ProveedorDeMensajes,
    ResultadoDeEnvio,
)
from pruebas.notificaciones.escenario import montar_negocio

pytestmark = pytest.mark.bd


class ProveedorQueSiempreFalla(ProveedorDeMensajes):
    """El proveedor caído. Cuenta cuántas veces se le llamó, que es lo que se quiere afirmar."""

    nombre = "roto"
    canales = ("whatsapp", "email", "push", "sms")

    def __init__(self) -> None:
        self.intentos = 0

    async def enviar(self, mensaje: MensajeSaliente) -> ResultadoDeEnvio:
        self.intentos += 1
        raise RuntimeError("el proveedor no responde")


async def _encolar(abrir_negocio, negocio, **cambios) -> uuid.UUID:
    ahora = datetime.now(UTC)
    valores = {
        "hecho": Hecho.RECORDATORIO_2H,
        "entidad": "booking",
        "entidad_id": uuid.uuid4(),
        "canal": "whatsapp",
        "destino": negocio.telefono_de_la_clienta,
        "destinatario": "cliente",
        "negocio_id": negocio.id,
        "programado_para": ahora - timedelta(hours=3),
        "caduca_en": None,
    }
    valores.update(cambios)
    async with abrir_negocio(negocio.id) as sesion:
        creada = await encolar(sesion, **valores)
    assert creada is not None
    return creada


async def test_un_recordatorio_caducado_se_descarta_en_vez_de_reintentarse(
    abrir_negocio, proveedores, proveedor
):
    """El recordatorio de 2 h de una cita que ya empezó **no se manda y no se reintenta**.

    Insistir no lo mejora: llegar tarde es peor que no llegar, y cada intento de WhatsApp se
    paga. Por eso la caducidad se mira **antes** que los intentos y antes que el proveedor: no
    se gasta una llamada en un mensaje que, si llegara, molestaría.
    """
    negocio = await montar_negocio()
    ahora = datetime.now(UTC)
    notificacion_id = await _encolar(
        abrir_negocio, negocio, caduca_en=ahora - timedelta(hours=1)
    )

    async with abrir_negocio(negocio.id) as sesion:
        resumen = await entregar_pendientes(sesion, proveedores=proveedores, ahora=ahora)
        estado, intentos = (
            await sesion.execute(
                text("SELECT status, attempts FROM notifications WHERE id = :id"),
                {"id": notificacion_id},
            )
        ).one()

    assert resumen.descartadas == 1, f"Se esperaba una descartada y salió {resumen}."
    assert estado == "descartada"
    assert intentos == 0, "Se gastó un intento en un mensaje que ya no valía."
    assert proveedor.mensajes() == [], "El proveedor recibió un mensaje caducado."


async def test_una_notificacion_viva_se_entrega_y_queda_escrita(
    abrir_negocio, proveedores, proveedor
):
    """El camino feliz: sale, se marca `enviada` y queda el registro de entrega.

    El registro es lo que permite responder «¿le llegó el recordatorio?» sin adivinar, que es
    la primera pregunta de soporte que va a llegar.
    """
    negocio = await montar_negocio()
    ahora = datetime.now(UTC)
    notificacion_id = await _encolar(
        abrir_negocio, negocio, caduca_en=ahora + timedelta(hours=2)
    )

    async with abrir_negocio(negocio.id) as sesion:
        resumen = await entregar_pendientes(sesion, proveedores=proveedores, ahora=ahora)
        estado = (
            await sesion.execute(
                text("SELECT status FROM notifications WHERE id = :id"), {"id": notificacion_id}
            )
        ).scalar_one()
        entregas = (
            await sesion.execute(
                text(
                    "SELECT count(*) FROM notification_deliveries WHERE notification_id = :id"
                ),
                {"id": notificacion_id},
            )
        ).scalar_one()

    assert resumen.enviadas == 1
    assert estado == "enviada"
    assert entregas == 1
    escritos = proveedor.mensajes()
    assert len(escritos) == 1
    assert escritos[0]["destino"] == negocio.telefono_de_la_clienta


async def test_los_reintentos_respetan_el_tope(abrir_negocio):
    """Con el proveedor caído se insiste **cinco veces y se para**, no para siempre.

    Sin tope, una notificación rota seguiría costando llamadas al proveedor hasta que alguien
    la viera. Y como cada llamada de WhatsApp se paga, «para siempre» tiene factura.
    """
    negocio = await montar_negocio()
    roto = ProveedorQueSiempreFalla()
    proveedores = dict.fromkeys(("whatsapp", "email", "push", "sms"), roto)
    politica = PoliticaDeReintentos()
    notificacion_id = await _encolar(abrir_negocio, negocio)

    async with abrir_negocio(negocio.id) as sesion:
        notificacion = await sesion.get(Notification, notificacion_id)
        assert notificacion is not None
        estados = []
        # Una vuelta de más a propósito: la sexta no tiene que volver a llamar al proveedor.
        for vuelta in range(politica.intentos_maximos + 1):
            estados.append(
                await entregar(
                    sesion,
                    notificacion,
                    proveedores=proveedores,
                    ahora=datetime.now(UTC) + timedelta(hours=vuelta),
                    politica=politica,
                )
            )

    assert roto.intentos == politica.intentos_maximos, (
        f"El proveedor recibió {roto.intentos} llamadas y el tope son "
        f"{politica.intentos_maximos}."
    )
    assert estados[-1] == "fallida"
    assert estados[:-2] == ["pendiente"] * (politica.intentos_maximos - 1)
    assert notificacion.attempts == politica.intentos_maximos
    assert notificacion.next_attempt_at is None, "Una fallida no puede quedar con próxima hora."


async def test_una_fallida_no_la_vuelve_a_coger_el_trabajador(abrir_negocio, proveedores):
    """Cuando se agotó, se agotó: el barrido siguiente ni la mira."""
    negocio = await montar_negocio()
    notificacion_id = await _encolar(abrir_negocio, negocio)

    async with abrir_negocio(negocio.id) as sesion:
        await sesion.execute(
            text("UPDATE notifications SET status = 'fallida' WHERE id = :id"),
            {"id": notificacion_id},
        )
        resumen = await entregar_pendientes(sesion, proveedores=proveedores)

    assert resumen.total == 0


def test_la_espera_crece_y_tiene_techo():
    """La cuenta del retroceso, sin base de datos: es aritmética y se prueba como tal.

    Los dos topes hacen falta por motivos distintos. Sin el de la espera, el quinto intento
    caería dos días después y el mensaje ya no valdría; sin el del número, se insistiría para
    siempre.
    """
    politica = PoliticaDeReintentos(
        intentos_maximos=5,
        espera_base=timedelta(minutes=1),
        factor=4,
        espera_maxima=timedelta(hours=6),
    )

    assert politica.espera_tras(1) == timedelta(minutes=1)
    assert politica.espera_tras(2) == timedelta(minutes=4)
    assert politica.espera_tras(3) == timedelta(minutes=16)
    # A partir de aquí manda el techo, no la potencia.
    assert politica.espera_tras(9) == timedelta(hours=6)
    assert not politica.agotada(4)
    assert politica.agotada(5)
