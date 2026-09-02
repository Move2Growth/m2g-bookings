"""El trabajador que consume la cola y habla con los proveedores.

Es el único sitio del sistema desde el que sale un mensaje. Todo lo demás encola.

Está partido en dos por una razón de aislamiento, no de estilo: las notificaciones de un
negocio se entregan **con su tenant fijado**, y las de plataforma —los OTP, los avisos que no
son de ningún salón— llevan `business_id` nulo y solo se ven desde una sesión sin tenant. Con
las políticas de `notifications` comparando con `IS NOT DISTINCT FROM`, las dos mitades ven
exactamente lo suyo y nada más.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from agenda.notificaciones.cola import ResumenDeEntrega, entregar_pendientes
from agenda.notificaciones.proveedores import ProveedorDeMensajes, registro_de_proveedores
from agenda.trabajos.bd import fabrica_de_negocio, fabrica_de_sistema, negocios_vivos

registro = logging.getLogger("agenda.trabajos")

#: Cuántas se intentan por pasada y por negocio. Un tope bajo mantiene la transacción corta:
#: una pasada de mil mensajes tendría una transacción abierta durante minutos, y una caída a
#: mitad tiraría el trabajo entero en vez de perder una tanda.
TANDA = 50


async def entregar_cola_de_negocio(
    ctx: dict[str, Any],
    negocio_id: str,
    *,
    ahora: datetime | None = None,
    limite: int = TANDA,
) -> ResumenDeEntrega:
    """Manda lo que toque de un negocio. **Recibe el identificador**, no la fila."""
    proveedores = _proveedores(ctx)
    async with fabrica_de_negocio(ctx)(uuid.UUID(negocio_id)) as sesion:
        return await entregar_pendientes(
            sesion, proveedores=proveedores, ahora=ahora or datetime.now(UTC), limite=limite
        )


async def entregar_cola_de_plataforma(
    ctx: dict[str, Any], *, ahora: datetime | None = None, limite: int = TANDA
) -> ResumenDeEntrega:
    """Lo que no es de ningún negocio: OTP y avisos de la plataforma."""
    proveedores = _proveedores(ctx)
    async with fabrica_de_sistema(ctx)() as sesion:
        return await entregar_pendientes(
            sesion, proveedores=proveedores, ahora=ahora or datetime.now(UTC), limite=limite
        )


async def barrer_la_cola(ctx: dict[str, Any], *, ahora: datetime | None = None) -> ResumenDeEntrega:
    """`cron` de respaldo: una pasada por todos los negocios y por la plataforma.

    La entrega normal la dispara quien encola, en cuanto encola. Esto es la red debajo: recoge
    lo que quedó reintentable y lo que se encoló para más tarde. Que exista es lo que permite
    que un fallo del proveedor a las tres de la mañana no deje mensajes muertos hasta que
    alguien lo mire.
    """
    ahora = ahora or datetime.now(UTC)
    total = ResumenDeEntrega()

    resumen = await entregar_cola_de_plataforma(ctx, ahora=ahora)
    _sumar(total, resumen)

    async with fabrica_de_sistema(ctx)() as sesion:
        negocios = await negocios_vivos(sesion)
    for negocio_id in negocios:
        _sumar(total, await entregar_cola_de_negocio(ctx, str(negocio_id), ahora=ahora))

    registro.info(
        "cola barrida: %d enviadas, %d reintentables, %d descartadas, %d fallidas",
        total.enviadas,
        total.reintentables,
        total.descartadas,
        total.fallidas,
    )
    return total


def _proveedores(ctx: dict[str, Any]) -> dict[str, ProveedorDeMensajes]:
    """Los del contexto si el trabajador los preparó al arrancar; si no, los de configuración."""
    return ctx.get("proveedores") or registro_de_proveedores()


def _sumar(total: ResumenDeEntrega, parcial: ResumenDeEntrega) -> None:
    total.enviadas += parcial.enviadas
    total.fallidas += parcial.fallidas
    total.descartadas += parcial.descartadas
    total.reintentables += parcial.reintentables
