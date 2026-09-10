"""Lo que se borra solo pasado su plazo, y lo que no se toca nunca (Ley 81 · ADR-0025).

La Ley 81 no dice solo «guarda los datos con cuidado»: dice **no los guardes más de lo que haga
falta**. Sin un plazo, `audit_logs` crece para siempre — y el día que estorbe, alguien la vacía
con prisa y sin criterio, que es la peor forma de borrar.

Se prueba contra PostgreSQL de verdad porque lo que se ejerce es un `DELETE` por lotes con
`ctid`, que es una columna del propio PostgreSQL y no existe en ningún otro sitio.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from agenda.trabajos import retencion
from pruebas.bd.escenario_panel import conexion_de_dueno, montar_salon

pytestmark = pytest.mark.bd


async def _apuntar(cuando: datetime, marca: str) -> None:
    async with conexion_de_dueno() as sesion:
        await sesion.execute(
            text(
                """
                INSERT INTO audit_logs (actor_kind, action, created_at)
                VALUES ('admin', :accion, :cuando)
                """
            ),
            {"accion": marca, "cuando": cuando},
        )


async def _cuantas(marca: str) -> int:
    async with conexion_de_dueno() as sesion:
        return (
            await sesion.execute(
                text("SELECT count(*) FROM audit_logs WHERE action = :accion"), {"accion": marca}
            )
        ).scalar_one()


def _contexto():
    """El trabajo con la conexión de las pruebas. El rol de sistema no lo tiene esta base."""
    return {"sesion_de_sistema": conexion_de_dueno}


async def test_lo_viejo_del_registro_de_auditoria_se_borra_y_lo_reciente_se_queda():
    """Doce meses es el plazo, y el corte cae donde tiene que caer.

    Se apuntan dos rastros con la misma marca y distinta edad: uno de hace dos años y otro de
    ayer. Después del barrido tiene que quedar **exactamente uno**. Contar solo el total no
    valdría: hay más filas en la tabla y el número no diría cuál se fue.
    """
    marca = f"prueba-retencion-{uuid.uuid4().hex[:8]}"
    ahora = datetime.now(UTC)
    await _apuntar(ahora - timedelta(days=730), marca)
    await _apuntar(ahora - timedelta(days=1), marca)
    assert await _cuantas(marca) == 2

    resumen = await retencion.barrer_lo_caducado(_contexto(), ahora=ahora)

    assert await _cuantas(marca) == 1, (
        "O se borró lo de ayer o se quedó lo de hace dos años. Las dos cosas son un fallo de "
        "la Ley 81: guardar de más incumple, y borrar de menos deja sin prueba de qué hizo el "
        "equipo interno el día que alguien reclame."
    )
    assert resumen.auditoria_borrada >= 1


async def test_lo_del_dia_del_corte_no_se_va_por_un_pelo():
    """Justo dentro del plazo se queda. Un corte mal puesto se lleva un mes entero por delante."""
    marca = f"prueba-corte-{uuid.uuid4().hex[:8]}"
    ahora = datetime.now(UTC)
    # Un día **dentro** del plazo de doce meses (que el trabajo cuenta como 12 × 30 días).
    await _apuntar(ahora - timedelta(days=359), marca)

    await retencion.barrer_lo_caducado(_contexto(), ahora=ahora)

    assert await _cuantas(marca) == 1


async def test_una_factura_de_hace_diez_anos_sigue_ahi_despues_del_barrido():
    """**Nada fiscal se borra por antigüedad**, y esto lo fija con una factura de verdad.

    El plazo de las facturas no lo decide el producto: lo dice la DGI, y equivocarse hacia abajo
    es un problema con Hacienda. El día que alguien amplíe este trabajo «para limpiar un poco
    más», esta prueba se lo dice.

    La primera versión de esta prueba contaba las filas de `invoices` antes y después. La tabla
    está vacía en la base de pruebas, así que comparaba **cero con cero** y habría pasado con un
    trabajo que borrara todas las facturas del mundo. Ahora se mete una, con diez años encima
    —el doble del plazo más largo que nadie propondría— y se comprueba que sigue ahí.
    """
    salon = await montar_salon()
    numero = f"PRUEBA-{uuid.uuid4().hex[:8]}"
    hace_diez_anos = datetime.now(UTC) - timedelta(days=3650)

    async with conexion_de_dueno() as sesion:
        pago = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO payments (business_id, payer_kind, purpose, amount_minor,
                                          currency, status, idempotency_key)
                    VALUES (:negocio, 'negocio', 'suscripcion', 1000, 'USD', 'pagado', :clave)
                    RETURNING id
                    """
                ),
                {"negocio": salon.negocio_id, "clave": f"retencion-{uuid.uuid4()}"},
            )
        ).scalar_one()
        await sesion.execute(
            text(
                """
                INSERT INTO invoices (business_id, payment_id, number, issued_at,
                                      subtotal_minor, total_minor, currency, created_at)
                VALUES (:negocio, :pago, :numero, :cuando, 1000, 1000, 'USD', :cuando)
                """
            ),
            {
                "negocio": salon.negocio_id,
                "pago": pago,
                "numero": numero,
                "cuando": hace_diez_anos,
            },
        )

    await retencion.barrer_lo_caducado(_contexto(), ahora=datetime.now(UTC))

    async with conexion_de_dueno() as sesion:
        quedan = (
            await sesion.execute(
                text("SELECT count(*) FROM invoices WHERE number = :numero"), {"numero": numero}
            )
        ).scalar_one()

    assert quedan == 1, (
        "El barrido se llevó una factura por delante. El plazo fiscal lo dice la DGI y nada de "
        "este trabajo puede tocarlo."
    )
