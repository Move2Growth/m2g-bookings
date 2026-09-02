"""La configuración de arq: qué trabajos existen, en qué cola y cada cuánto (ADR-0008).

**Tres colas y tres procesos, no una cola con prioridades.** Es la decisión que más se nota en
un día malo: una exportación grande y una confirmación de reserva no pueden compartir sitio en
la fila, porque el trabajo lento gana siempre por ocupar los trabajadores durante minutos. Con
colas separadas, el que se atasca es el suyo.

* `default` — reactivo: entregar la cola de notificaciones. Es lo que tiene que salir ya.
* `programado` — el planificador: recordatorios, reseñas y el aviso de citas sin cerrar.
* `pesado` — imágenes, exportaciones, recálculo del ranking. Todavía vacía, y declarada desde
  ahora para que el primer trabajo pesado no tenga que elegir dónde meterse.

El `cron` de este archivo **no manda ningún mensaje**: encola. Ejecutarlo dos veces no duplica
nada porque la clave de idempotencia es la misma (ADR-0007). Esa es la única razón por la que
un planificador poco fiable es aceptable aquí.

Se arranca un proceso por cola, todos con la misma imagen y distinto comando::

    arq agenda.trabajos.worker.TrabajadorReactivo
    arq agenda.trabajos.worker.TrabajadorProgramado
    arq agenda.trabajos.worker.TrabajadorPesado
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from arq.connections import RedisSettings
from arq.cron import cron

from agenda.ajustes import obtener_ajustes
from agenda.notificaciones.proveedores import registro_de_proveedores
from agenda.trabajos.cierre import planificar_cierre_de_citas_pasadas
from agenda.trabajos.entrega import (
    barrer_la_cola,
    entregar_cola_de_negocio,
    entregar_cola_de_plataforma,
)
from agenda.trabajos.recordatorios import (
    planificar_recordatorios_2h,
    planificar_recordatorios_24h,
    planificar_reviews,
)

registro = logging.getLogger("agenda.trabajos")

COLA_REACTIVA = "agenda:default"
COLA_PROGRAMADA = "agenda:programado"
COLA_PESADA = "agenda:pesado"


def ajustes_de_redis() -> RedisSettings:
    return RedisSettings.from_dsn(obtener_ajustes().redis_url)


async def al_arrancar(ctx: dict[str, Any]) -> None:
    """Los proveedores se resuelven **una vez por proceso**, no una vez por mensaje.

    Y se dejan en el contexto porque es también el punto por el que las pruebas meten el
    proveedor de desarrollo sin tocar variables de entorno globales.
    """
    ctx["proveedores"] = registro_de_proveedores()
    registro.info(
        "trabajador arrancado con proveedores: %s",
        {canal: proveedor.nombre for canal, proveedor in ctx["proveedores"].items()},
    )


class TrabajadorReactivo:
    """Lo que tiene que salir ahora: las notificaciones recién encoladas."""

    redis_settings = ajustes_de_redis()
    queue_name = COLA_REACTIVA
    functions: ClassVar[list[Any]] = [entregar_cola_de_negocio, entregar_cola_de_plataforma]
    on_startup = al_arrancar
    max_jobs = 20
    job_timeout = 60
    # Los reintentos de verdad los lleva la cola en la tabla, con su retroceso y su tope. arq
    # reintenta solo lo que se cayó a media ejecución, y para eso una vez más basta.
    max_tries = 2


class TrabajadorProgramado:
    """El planificador. Encola y se va."""

    redis_settings = ajustes_de_redis()
    queue_name = COLA_PROGRAMADA
    functions: ClassVar[list[Any]] = [
        planificar_recordatorios_24h,
        planificar_recordatorios_2h,
        planificar_reviews,
        planificar_cierre_de_citas_pasadas,
        barrer_la_cola,
    ]
    on_startup = al_arrancar
    max_jobs = 4
    # Un barrido puede tardar: son muchos negocios y una transacción corta por cada uno.
    job_timeout = 600
    cron_jobs: ClassVar[list[Any]] = [
        # Cada cuarto de hora: la ventana de barrido es de una hora, así que una pasada
        # perdida no deja a nadie sin recordatorio.
        cron(planificar_recordatorios_24h, minute={0, 15, 30, 45}, run_at_startup=False),
        cron(planificar_recordatorios_2h, minute={0, 15, 30, 45}, run_at_startup=False),
        cron(planificar_reviews, minute={5, 35}, run_at_startup=False),
        # Una vez al día y a una hora en la que el salón está abierto: un aviso de gestión a
        # las tres de la mañana se lee a las nueve y molesta a las tres.
        cron(planificar_cierre_de_citas_pasadas, hour={20}, minute={0}, run_at_startup=False),
        # La red debajo de la entrega reactiva: recoge lo reintentable y lo programado.
        cron(barrer_la_cola, minute={10, 40}, run_at_startup=False),
    ]


class TrabajadorPesado:
    """Imágenes, exportaciones y recálculos. Declarada vacía a propósito.

    Existe desde el principio para que el primer trabajo pesado no tenga que decidir dónde
    vivir —y acabe, por comodidad, en la cola de las notificaciones.
    """

    redis_settings = ajustes_de_redis()
    queue_name = COLA_PESADA
    functions: ClassVar[list[Any]] = []
    on_startup = al_arrancar
    max_jobs = 2
    job_timeout = 900


#: El nombre que arq busca cuando no se le dice cuál. Apunta al reactivo porque es el que no
#: puede faltar: sin él no sale ni un mensaje.
WorkerSettings = TrabajadorReactivo
