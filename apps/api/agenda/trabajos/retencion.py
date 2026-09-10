"""Lo que se borra solo, y lo que no se borra nunca (Ley 81 · ADR-0025).

La Ley 81 no dice solo «guarda los datos con cuidado»: dice **no los guardes más de lo que hagan
falta**. Un registro de auditoría sin plazo incumple eso y además crece para siempre — y el día
que ocupe de más, alguien lo vaciará con prisa y sin criterio, que es la peor forma de borrar.

## Lo que este trabajo borra

**El registro de auditoría, pasado su plazo.** Es el rastro de las acciones internas: quién entró
en qué negocio, quién forzó una cancelación, quién suplantó a quién. Doce meses por defecto, que
es lo que se usa en el oficio: cubre de sobra una reclamación —que llega en semanas, no en años— y
no convierte la tabla en un archivo histórico de la vida privada de nadie.

## Lo que este trabajo NO borra, y por qué está escrito aquí

**Nada que sea un documento fiscal.** Las facturas y los recibos tienen un plazo que no lo decide
el producto sino la DGI, y equivocarse hacia abajo es un problema con Hacienda. El valor por
defecto son **cinco años**, y lleva una marca bien visible: hay que confirmarlo con la asesoría.
Mientras `RETENCION_FACTURAS_ANOS` no se toque, este trabajo **no borra ni una factura**: prefiere
guardar de más a borrar de menos.

**El texto de una opinión cuyo autor se dio de baja.** Se conserva con el autor anonimizado (P14):
un salón que reunió cuarenta opiniones no puede perderlas porque un cliente se dé de baja, y quien
las lee tampoco. Eso lo resuelve la lápida del usuario, no un borrado por antigüedad.

## Por qué borra por lotes

Un `DELETE` de un millón de filas mantiene una transacción abierta y una tabla bloqueada el rato
que tarde. Se hace por trozos: el trabajo puede correr a las tres de la mañana, pero a las tres de
la mañana también hay salones abiertos en otra zona horaria.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text

from agenda.ajustes import obtener_ajustes
from agenda.trabajos.bd import fabrica_de_sistema

#: Cuántas filas por vuelta. Ni tan pocas que el trabajo tarde una hora ni tantas que la tabla se
#: quede bloqueada un rato largo.
LOTE = 5_000

#: Cuántas vueltas como mucho en una pasada. Un tope explícito y no un `while True`: si algo va
#: mal —un reloj movido, un plazo puesto en cero— este trabajo se para y se nota, en vez de
#: vaciar la tabla entera en silencio.
VUELTAS_MAXIMAS = 200


@dataclass(frozen=True)
class ResumenDeRetencion:
    auditoria_borrada: int
    corte: datetime
    se_quedo_corto: bool


async def barrer_lo_caducado(
    ctx: dict[str, Any], *, ahora: datetime | None = None
) -> ResumenDeRetencion:
    """Borra el registro de auditoría más viejo que el plazo. Nada más.

    Corre con el rol de sistema porque `audit_logs` es de la plataforma, no de un negocio.
    """
    ajustes = obtener_ajustes()
    ahora = ahora or datetime.now(UTC)
    corte = ahora - timedelta(days=ajustes.retencion_auditoria_meses * 30)

    borradas = 0
    se_quedo_corto = False
    abrir = fabrica_de_sistema(ctx)

    for vuelta in range(VUELTAS_MAXIMAS):
        async with abrir() as sesion:
            # `ctid` es la dirección física de la fila en PostgreSQL: es la forma barata de
            # coger un trozo sin ordenar un millón de filas por fecha en cada vuelta.
            resultado = await sesion.execute(
                text(
                    """
                    DELETE FROM audit_logs
                    WHERE ctid IN (
                        SELECT ctid FROM audit_logs WHERE created_at < :corte LIMIT :lote
                    )
                    """
                ),
                {"corte": corte, "lote": LOTE},
            )
            await sesion.commit()
            borradas += resultado.rowcount or 0
            if (resultado.rowcount or 0) < LOTE:
                break
        if vuelta == VUELTAS_MAXIMAS - 1:
            # Queda trabajo para la próxima pasada. Se dice en vez de seguir dando vueltas.
            se_quedo_corto = True

    return ResumenDeRetencion(
        auditoria_borrada=borradas, corte=corte, se_quedo_corto=se_quedo_corto
    )
