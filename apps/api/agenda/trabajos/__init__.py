"""Trabajos en segundo plano (ADR-0008).

Tres reglas gobiernan todo lo que hay en este paquete y no se negocian por trabajo:

* **El planificador encola, no envía.** Los trabajos periódicos recorren su ventana e insertan
  filas en `notifications` con su clave de idempotencia. Que el `cron` se dispare dos veces no
  duplica nada, y eso hace que la garantía no dependa de la fiabilidad del planificador.
* **Los argumentos son identificadores, nunca objetos.** El trabajo relee de la base. Un
  trabajo que arrastra una copia del estado manda el estado viejo cuando se reintenta.
* **El tenant se fija a mano.** Un trabajador no tiene sesión de usuario, así que no hereda el
  negocio de ninguna parte. Es donde más fácil se cuela una consulta sin filtrar (ADR-0002).
"""

from agenda.trabajos.cierre import (
    marcar_citas_sin_cerrar_de_negocio,
    planificar_cierre_de_citas_pasadas,
)
from agenda.trabajos.entrega import (
    barrer_la_cola,
    entregar_cola_de_negocio,
    entregar_cola_de_plataforma,
)
from agenda.trabajos.recordatorios import (
    encolar_recordatorios_de_negocio,
    encolar_reviews_de_negocio,
    planificar_recordatorios_2h,
    planificar_recordatorios_24h,
    planificar_reviews,
)

__all__ = [
    "barrer_la_cola",
    "encolar_recordatorios_de_negocio",
    "encolar_reviews_de_negocio",
    "entregar_cola_de_negocio",
    "entregar_cola_de_plataforma",
    "marcar_citas_sin_cerrar_de_negocio",
    "planificar_cierre_de_citas_pasadas",
    "planificar_recordatorios_24h",
    "planificar_recordatorios_2h",
    "planificar_reviews",
]
