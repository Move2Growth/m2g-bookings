"""La máquina de estados de la reserva: lo que se puede hacer y quién puede hacerlo."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from agenda.dominio.reservas import (
    ESTADOS_ACTIVOS,
    ESTADOS_TERMINALES,
    Actor,
    EstadoReserva,
    PoliticaDeCancelacion,
    estado_inicial,
    libera_el_hueco,
    puede_transicionar,
    validar_cancelacion_del_cliente,
    validar_transicion,
)
from agenda.errores import FueraDeVentanaDeCancelacion, ReservaNoModificable

PANAMA = ZoneInfo("America/Panama")


def cuando(hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 9, 2, hora, minuto, tzinfo=PANAMA)


def test_los_valores_del_enumerado_son_exactamente_los_del_brief():
    """Se serializan tal cual a la API y al cliente: si cambian, rompen a alguien."""
    assert [estado.value for estado in EstadoReserva] == [
        "pendiente",
        "confirmada",
        "completada",
        "no_show",
        "cancelada_cliente",
        "cancelada_negocio",
    ]


def test_solo_pendiente_y_confirmada_ocupan_agenda():
    """Esta lista tiene que coincidir con el WHERE de la restricción de exclusión de la base.

    Si se separan, el motor y la base dejan de estar de acuerdo sobre qué está ocupado: el
    motor ofrecería huecos que la base rechaza, o peor, la base dejaría entrar solapes.
    """
    assert EstadoReserva.PENDIENTE in ESTADOS_ACTIVOS
    assert EstadoReserva.CONFIRMADA in ESTADOS_ACTIVOS
    assert len(ESTADOS_ACTIVOS) == 2
    assert ESTADOS_ACTIVOS.isdisjoint(ESTADOS_TERMINALES)
    assert set(EstadoReserva) == ESTADOS_ACTIVOS | ESTADOS_TERMINALES


def test_auto_confirmar_es_el_valor_por_defecto():
    """D10. El salón que quiere revisar cada cita lo desactiva en sus ajustes."""
    assert estado_inicial(auto_confirmar=True) is EstadoReserva.CONFIRMADA
    assert estado_inicial(auto_confirmar=False) is EstadoReserva.PENDIENTE


def test_el_negocio_completa_y_marca_el_no_show():
    assert puede_transicionar(EstadoReserva.CONFIRMADA, EstadoReserva.COMPLETADA, Actor.NEGOCIO)
    assert puede_transicionar(EstadoReserva.CONFIRMADA, EstadoReserva.NO_SHOW, Actor.NEGOCIO)


def test_el_cliente_no_puede_marcarse_a_si_mismo_como_completado():
    """La tasa de completado alimenta el ranking: no la escribe quien sale beneficiado."""
    assert not puede_transicionar(EstadoReserva.CONFIRMADA, EstadoReserva.COMPLETADA, Actor.CLIENTE)


def test_el_sistema_no_marca_no_shows_por_su_cuenta():
    """Una cita puede haberse atendido sin que nadie toque el móvil.

    Un no-show automático al pasar la hora le contaría al cliente para bloquearlo, y sería
    culpa del salón por no haber actualizado la agenda.
    """
    assert not puede_transicionar(EstadoReserva.CONFIRMADA, EstadoReserva.NO_SHOW, Actor.SISTEMA)


def test_de_un_estado_terminal_no_se_sale():
    with pytest.raises(ReservaNoModificable):
        validar_transicion(EstadoReserva.CANCELADA_CLIENTE, EstadoReserva.CONFIRMADA, Actor.NEGOCIO)

    with pytest.raises(ReservaNoModificable):
        validar_transicion(EstadoReserva.COMPLETADA, EstadoReserva.NO_SHOW, Actor.NEGOCIO)


def test_una_cita_pendiente_no_se_puede_completar_sin_confirmar():
    with pytest.raises(ReservaNoModificable):
        validar_transicion(EstadoReserva.PENDIENTE, EstadoReserva.COMPLETADA, Actor.NEGOCIO)


def test_cancelar_libera_el_hueco_sin_borrar_la_fila():
    """El historial se conserva para el negocio y para el contador de no-shows."""
    assert libera_el_hueco(EstadoReserva.CANCELADA_CLIENTE)
    assert libera_el_hueco(EstadoReserva.NO_SHOW)
    assert not libera_el_hueco(EstadoReserva.CONFIRMADA)


def test_el_cliente_cancela_dentro_de_la_ventana():
    """Cita a las 18:00, política de dos horas: a las 15:00 todavía puede."""
    validar_cancelacion_del_cliente(
        ahora=cuando(15, 0), empieza_en=cuando(18, 0), politica=PoliticaDeCancelacion()
    )


def test_pasada_la_ventana_cancelar_ya_no_es_cosa_del_cliente():
    """A dos horas de la cita el hueco ya no se vuelve a llenar."""
    with pytest.raises(FueraDeVentanaDeCancelacion) as error:
        validar_cancelacion_del_cliente(
            ahora=cuando(17, 30), empieza_en=cuando(18, 0), politica=PoliticaDeCancelacion()
        )

    assert error.value.codigo == "FUERA_DE_VENTANA_DE_CANCELACION"
    assert error.value.estado_http == 422


def test_la_ventana_de_cancelacion_es_configurable():
    """Un salón puede pedir 24 horas y otro ninguna: es un ajuste del negocio."""
    politica = PoliticaDeCancelacion(horas_antes=24)

    with pytest.raises(FueraDeVentanaDeCancelacion):
        validar_cancelacion_del_cliente(
            ahora=cuando(18, 0) - timedelta(hours=12),
            empieza_en=cuando(18, 0),
            politica=politica,
        )
