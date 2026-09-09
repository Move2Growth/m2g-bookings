"""Que un reintento no cree dos citas (ADR-0012).

La app y la web **reintentan solas**. Es la consecuencia de un requisito escrito —«usable en
gama media con 3G»—: en una conexión mala se pierde la respuesta, no la petición, así que el
servidor ya ha creado la cita cuando el cliente decide volver a pedirla.

Sin esto, el reintento choca contra la restricción de exclusión y recibe **«ese horario se
acaba de ocupar»** por una cita que ocupó él mismo. Y ahí empieza el daño de verdad: la persona
se cree que llegó tarde, elige otra hora, y se queda con **dos citas** — la fantasma, a la que
no va a ir, y la nueva. Al salón le sale un plantón de la nada.

## Cómo funciona

La clave se **reclama y se contesta en la misma transacción que la cita**. Esa es toda la
gracia: una fila guardada implica una cita guardada, y no hay ventana en la que la clave diga
que existe algo que se acabó deshaciendo.

El reclamo es un `INSERT … ON CONFLICT DO NOTHING`. Si inserta, esta petición es la primera y
sigue. Si no inserta, alguien se le adelantó con la misma clave.

**Y aquí PostgreSQL hace el trabajo difícil solo, aunque no lo parezca al leerlo:** cuando la
otra transacción todavía no ha confirmado, ese `INSERT` **no se rinde, se queda esperando** a
que termine. Así que las dos peticiones a la vez —los dos dedos impacientes— acaban en una
cita y dos respuestas iguales, sin que este módulo tenga que arbitrar nada. Escrito de la
forma ingenua —mirar si existe y luego insertar— habría dos citas.

Cuando el reclamo no inserta, quedan tres respuestas posibles:

* **la fila ya tiene respuesta** → se devuelve **la misma**, con su mismo código. Es lo único
  que sirve: un cliente que reintenta necesita saber qué pasó, no un error nuevo;
* **el cuerpo no coincide** → no es un reintento, es un error del cliente reusando la clave, y
  contestarle con la respuesta de otra petición sería mentirle;
* **la fila no se ve** → la clave existe pero pertenece a otro salón, y su política de fila la
  esconde. No se inventa nada y no se dice «esa hora se ocupó», que sería mentir sobre un hueco
  que quizá sigue libre: se pide que se repita.

## Por qué el cuerpo se compara por huella y no por igualdad

Se guarda un `sha256` del cuerpo canónico, no el cuerpo. El cuerpo de una reserva lleva a quién
atiende y a qué hora, y no hace falta conservar eso una vez contestado; la huella basta para
saber si el que vuelve pide lo mismo.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as insertar_pg
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.errores import ClaveReutilizada, ReintentoEnVuelo
from agenda.modelos import IdempotencyKey

#: Cuánto vale una clave. Un día cubre de sobra el reintento de una app —que ocurre en
#: segundos— y el del dedo que insiste, sin dejar la tabla creciendo para siempre.
CADUCIDAD = timedelta(days=1)


def huella(cuerpo: Any) -> bytes:
    """Huella del cuerpo, **canónica**: mismas claves en distinto orden son la misma petición.

    Sin ordenar, un cliente que serializa su JSON en otro orden vería su propio reintento
    rechazado como si pidiera otra cosa.
    """
    return hashlib.sha256(
        json.dumps(cuerpo, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).digest()


@dataclass(frozen=True)
class YaContestado:
    """La respuesta que se dio la primera vez, para darla igual."""

    estado: int
    cuerpo: dict[str, Any]


async def reclamar(
    sesion: AsyncSession,
    *,
    clave: str,
    endpoint: str,
    cuerpo: Any,
    usuario_id: uuid.UUID | None = None,
    negocio_id: uuid.UUID | None = None,
) -> YaContestado | None:
    """Reclama la clave. Devuelve `None` si esto es la primera vez y hay que hacer el trabajo.

    Lanza si la clave se está usando para otra cosa o si la primera petición sigue en vuelo.
    """
    mia = huella(cuerpo)

    reclamada = (
        await sesion.execute(
            insertar_pg(IdempotencyKey)
            .values(
                key=clave,
                endpoint=endpoint,
                user_id=usuario_id,
                business_id=negocio_id,
                request_hash=mia,
                expires_at=datetime.now(UTC) + CADUCIDAD,
            )
            .on_conflict_do_nothing(index_elements=["key", "endpoint"])
            .returning(IdempotencyKey.id)
        )
    ).scalar_one_or_none()

    if reclamada is not None:
        return None

    anterior = (
        await sesion.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.key == clave, IdempotencyKey.endpoint == endpoint
            )
        )
    ).scalar_one_or_none()

    # No insertó y tampoco se ve. Al esperar el `INSERT` a la transacción concurrente, esto ya
    # no puede ser «la otra sigue en vuelo»: es una clave de **otro negocio**, que la política
    # de fila esconde. Se pide repetir en vez de afirmar nada sobre el hueco.
    if anterior is None:
        raise ReintentoEnVuelo()

    if anterior.request_hash != mia:
        raise ClaveReutilizada()

    if anterior.response_status is None or anterior.response_body is None:
        raise ReintentoEnVuelo()

    return YaContestado(estado=anterior.response_status, cuerpo=anterior.response_body)


async def contestar(
    sesion: AsyncSession, *, clave: str, endpoint: str, estado: int, cuerpo: Any
) -> None:
    """Guarda la respuesta **en la misma transacción que el trabajo que la produjo**.

    Que sea la misma transacción no es un detalle de implementación: si se guardara aparte,
    existiría un instante en el que la clave promete una cita que todavía puede deshacerse.
    """
    await sesion.execute(
        update(IdempotencyKey)
        .where(IdempotencyKey.key == clave, IdempotencyKey.endpoint == endpoint)
        .values(response_status=estado, response_body=cuerpo)
    )
