"""La aritmética del parte de horas, sin base de datos.

Los casos raros de un fichaje no son teóricos: alguien ficha, se le cierra la aplicación y
vuelve a fichar; alguien olvida fichar la entrada y solo apunta la salida; alguien sigue dentro
cuando se abre la pantalla. Cada uno tiene una respuesta y las tres se pueden equivocar en
silencio, porque el resultado siempre es un número que parece razonable.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from agenda.servicios.fichaje import minutos_trabajados

BASE = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


def _en(minutos: int) -> datetime:
    return BASE + timedelta(minutes=minutos)


def test_una_jornada_normal():
    assert minutos_trabajados([("entrada", _en(0)), ("salida", _en(480))]) == 480


def test_dos_tramos_se_suman():
    """La mañana y la tarde, con el almuerzo en medio, son dos tramos y no uno de nueve horas."""
    marcas = [
        ("entrada", _en(0)),
        ("salida", _en(240)),
        ("entrada", _en(300)),
        ("salida", _en(540)),
    ]
    assert minutos_trabajados(marcas) == 480


def test_dos_entradas_seguidas_manda_la_ultima():
    """Contar desde la primera entrada le regalaría al parte una hora que nadie trabajó."""
    marcas = [("entrada", _en(0)), ("entrada", _en(60)), ("salida", _en(120))]
    assert minutos_trabajados(marcas) == 60


def test_una_salida_sin_entrada_se_ignora():
    """No se puede saber desde cuándo, así que no se inventa."""
    assert minutos_trabajados([("salida", _en(120))]) == 0


def test_la_jornada_abierta_no_suma():
    """Sumar «hasta ahora» daría un total que crece solo mientras la pantalla está abierta."""
    assert minutos_trabajados([("entrada", _en(0))]) == 0
    jornada = [("entrada", _en(0)), ("salida", _en(60)), ("entrada", _en(90))]
    assert minutos_trabajados(jornada) == 60


def test_las_marcas_desordenadas_se_ordenan_antes_de_contar():
    """Llegan de la base ordenadas, pero un total que depende del orden de una lista es un total
    que algún día sale negativo."""
    marcas = [("salida", _en(480)), ("entrada", _en(0))]
    assert minutos_trabajados(marcas) == 480
