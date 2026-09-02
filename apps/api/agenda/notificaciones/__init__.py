"""Notificaciones: la cola y los proveedores (ADR-0007).

Dos piezas y una frontera entre ellas:

* `cola` sabe **qué hay que mandar, a quién y cuándo**, y lleva la contabilidad de intentos.
* `proveedores` sabe **cómo se manda** por cada canal, y nada más.

La frontera es la que permite que la Fase 1 se construya y se pruebe entera sin una sola
credencial de Meta: el proveedor de desarrollo escribe a disco y a la consola, y el resto del
sistema no se entera de la diferencia.
"""

from agenda.notificaciones.cola import (
    Decision,
    Hecho,
    PoliticaDeReintentos,
    ResumenDeEntrega,
    clave_de_idempotencia,
    decidir_canal,
    encolar,
    entregar,
    entregar_pendientes,
)
from agenda.notificaciones.proveedores import (
    MensajeSaliente,
    ProveedorCorreo,
    ProveedorDeDesarrollo,
    ProveedorDeMensajes,
    ProveedorNoConfigurado,
    ProveedorWhatsApp,
    ResultadoDeEnvio,
    registro_de_proveedores,
)

__all__ = [
    "Decision",
    "Hecho",
    "MensajeSaliente",
    "PoliticaDeReintentos",
    "ProveedorCorreo",
    "ProveedorDeDesarrollo",
    "ProveedorDeMensajes",
    "ProveedorNoConfigurado",
    "ProveedorWhatsApp",
    "ResultadoDeEnvio",
    "ResumenDeEntrega",
    "clave_de_idempotencia",
    "decidir_canal",
    "encolar",
    "entregar",
    "entregar_pendientes",
    "registro_de_proveedores",
]
