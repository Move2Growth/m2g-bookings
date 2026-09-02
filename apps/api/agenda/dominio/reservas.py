"""La máquina de estados de una reserva (RSV-3, RSV-4, RSV-5).

Los estados y quién puede moverlos están aquí, en un solo sitio y en forma de datos, en vez de
repartidos en condicionales por los endpoints. La razón práctica: las transiciones son la
clase de regla que se copia mal. Basta con que un endpoint permita marcar `completada` una
cita ya cancelada para que las métricas de la tasa de completado —que alimentan el ranking—
empiecen a mentir sin que nadie lo note.

Dos matices del brief que este módulo hace explícitos:

* **La reprogramación no es un estado.** Es un evento sobre una reserva que sigue viva. Si
  fuera un estado terminal, el historial de un cliente que movió su cita dos veces se
  convertiría en tres reservas y el negocio no sabría cuál vale.
* **Auto-confirmar es lo normal, pero configurable** (D10). Un negocio puede querer revisar
  cada cita antes de aceptarla, y entonces `pendiente` es un estado en el que se vive un rato,
  no un trámite instantáneo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from agenda.errores import FueraDeVentanaDeCancelacion, ReservaNoModificable


class EstadoReserva(StrEnum):
    """Los estados del brief, en minúsculas con guion bajo.

    El formato importa: se serializan tal cual en la API, se guardan tal cual en la base y se
    comparan tal cual en el cliente. *En esta casa ya se ha roto un front porque el backend
    mandaba mayúsculas y el front comparaba minúsculas.* Aquí hay un solo formato.
    """

    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    COMPLETADA = "completada"
    NO_SHOW = "no_show"
    CANCELADA_CLIENTE = "cancelada_cliente"
    CANCELADA_NEGOCIO = "cancelada_negocio"


#: Estados en los que la cita sigue viva y **ocupa hueco en la agenda**. Son exactamente los
#: que la restricción de exclusión de la base considera (ADR-0004): si esta lista y la
#: cláusula `WHERE` de la restricción se separan, el motor y la base dejan de estar de acuerdo
#: sobre qué está ocupado, que es la peor discrepancia posible.
ESTADOS_ACTIVOS = frozenset({EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA})

#: Estados de los que ya no se sale.
ESTADOS_TERMINALES = frozenset(
    {
        EstadoReserva.COMPLETADA,
        EstadoReserva.NO_SHOW,
        EstadoReserva.CANCELADA_CLIENTE,
        EstadoReserva.CANCELADA_NEGOCIO,
    }
)


class Actor(StrEnum):
    CLIENTE = "cliente"
    NEGOCIO = "negocio"
    SISTEMA = "sistema"


#: Qué transiciones existen y quién puede hacerlas.
TRANSICIONES: dict[EstadoReserva, dict[EstadoReserva, frozenset[Actor]]] = {
    EstadoReserva.PENDIENTE: {
        EstadoReserva.CONFIRMADA: frozenset({Actor.NEGOCIO, Actor.SISTEMA}),
        EstadoReserva.CANCELADA_CLIENTE: frozenset({Actor.CLIENTE}),
        EstadoReserva.CANCELADA_NEGOCIO: frozenset({Actor.NEGOCIO}),
    },
    EstadoReserva.CONFIRMADA: {
        EstadoReserva.COMPLETADA: frozenset({Actor.NEGOCIO}),
        # Solo el negocio marca el no-show: es quien estaba allí. Y nunca lo marca el sistema
        # automáticamente al pasar la hora, porque una cita puede haberse atendido sin que
        # nadie toque el móvil, y un no-show injusto le cuenta al cliente para bloquearlo.
        EstadoReserva.NO_SHOW: frozenset({Actor.NEGOCIO}),
        EstadoReserva.CANCELADA_CLIENTE: frozenset({Actor.CLIENTE}),
        EstadoReserva.CANCELADA_NEGOCIO: frozenset({Actor.NEGOCIO}),
    },
}


@dataclass(frozen=True)
class PoliticaDeCancelacion:
    """Hasta cuándo puede cancelar el cliente por su cuenta (RSV-4).

    Pasado el plazo, cancelar deja de ser cosa del cliente y pasa a serlo del negocio: a dos
    horas de la cita, el hueco ya no se vuelve a llenar y el salón tiene derecho a saberlo por
    una conversación, no por una notificación.
    """

    horas_antes: int = 2


def puede_transicionar(desde: EstadoReserva, hacia: EstadoReserva, actor: Actor) -> bool:
    return actor in TRANSICIONES.get(desde, {}).get(hacia, frozenset())


def validar_transicion(desde: EstadoReserva, hacia: EstadoReserva, actor: Actor) -> None:
    """Lanza un error de dominio si la transición no existe o no es de ese actor."""
    if desde in ESTADOS_TERMINALES:
        raise ReservaNoModificable(
            f"La reserva ya está {desde.value.replace('_', ' ')} y no se puede cambiar."
        )
    if not puede_transicionar(desde, hacia, actor):
        raise ReservaNoModificable("Ese cambio de estado no está permitido para la reserva.")


def validar_cancelacion_del_cliente(
    *,
    ahora: datetime,
    empieza_en: datetime,
    politica: PoliticaDeCancelacion,
) -> None:
    """El cliente cancela por su cuenta solo dentro de la ventana."""
    limite = empieza_en - timedelta(hours=politica.horas_antes)
    if ahora > limite:
        raise FueraDeVentanaDeCancelacion(
            "Ya pasó el plazo para cancelar por tu cuenta. Escríbele al negocio y lo arreglan.",
            limite=limite.isoformat(),
        )


def estado_inicial(*, auto_confirmar: bool) -> EstadoReserva:
    """D10: auto-confirmar por defecto, configurable por negocio."""
    return EstadoReserva.CONFIRMADA if auto_confirmar else EstadoReserva.PENDIENTE


def libera_el_hueco(estado: EstadoReserva) -> bool:
    """Si la reserva deja de ocupar agenda al llegar a este estado.

    Cancelar libera el hueco **de inmediato** y sin borrar la fila: el historial se conserva
    para el negocio y para el contador de no-shows, pero el hueco vuelve a ofrecerse.
    """
    return estado in ESTADOS_TERMINALES
