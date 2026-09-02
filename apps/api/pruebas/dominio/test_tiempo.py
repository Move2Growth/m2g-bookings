"""Operaciones sobre intervalos: el ∩ y el − de la fórmula del slot libre.

Son cuatro funciones cortas de las que depende todo el motor, así que se prueban solas: si
`restar` se equivoca en un extremo, el error aparece como «a veces se ofrece un hueco ocupado»
tres capas más arriba, y ahí no hay quien lo encuentre.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from agenda.dominio.tiempo import Intervalo, intersecar, normalizar, restar

UTC = ZoneInfo("UTC")


def i(desde: int, hasta: int) -> Intervalo:
    """Un intervalo escrito en horas del 1 de septiembre de 2026, para leer las pruebas rápido."""
    base = datetime(2026, 9, 1, tzinfo=UTC)
    return Intervalo(base + timedelta(hours=desde), base + timedelta(hours=hasta))


def como_horas(intervalos) -> list[tuple[int, int]]:
    base = datetime(2026, 9, 1, tzinfo=UTC)
    return [
        (
            int((x.inicio - base).total_seconds() // 3600),
            int((x.fin - base).total_seconds() // 3600),
        )
        for x in intervalos
    ]


def test_un_intervalo_necesita_huso_horario():
    """Una fecha ingenua aquí sería un error de conversión esperando a pasar en producción."""
    with pytest.raises(ValueError):
        Intervalo(datetime(2026, 9, 1, 9, 0), datetime(2026, 9, 1, 10, 0))


def test_un_intervalo_al_reves_es_un_error():
    with pytest.raises(ValueError):
        i(10, 9)


def test_los_extremos_no_se_solapan():
    """Semiabierto: lo que acaba a las 10 y lo que empieza a las 10 no chocan."""
    assert not i(9, 10).solapa(i(10, 11))
    assert i(9, 11).solapa(i(10, 12))


def test_normalizar_funde_los_tramos_contiguos():
    """Dos tramos que se tocan son una jornada continua, no dos."""
    assert como_horas(normalizar([i(9, 13), i(13, 19)])) == [(9, 19)]


def test_normalizar_ordena_funde_y_tira_los_vacios():
    assert como_horas(normalizar([i(14, 19), i(9, 11), i(10, 12), i(15, 15)])) == [
        (9, 12),
        (14, 19),
    ]


def test_intersecar_es_el_horario_comun():
    """El negocio abre de 9 a 19; la profesional trabaja de 14 a 22. Coinciden de 14 a 19."""
    assert como_horas(intersecar([i(9, 19)], [i(14, 22)])) == [(14, 19)]


def test_intersecar_con_varios_tramos_por_lado():
    negocio = [i(9, 13), i(15, 19)]
    profesional = [i(11, 16), i(18, 20)]

    assert como_horas(intersecar(negocio, profesional)) == [(11, 13), (15, 16), (18, 19)]


def test_intersecar_sin_solape_no_devuelve_nada():
    assert intersecar([i(9, 12)], [i(14, 19)]) == []


def test_restar_parte_un_tramo_por_el_medio():
    """El almuerzo parte la jornada en dos."""
    assert como_horas(restar([i(9, 19)], [i(13, 14)])) == [(9, 13), (14, 19)]


def test_restar_recorta_por_los_extremos():
    assert como_horas(restar([i(9, 19)], [i(8, 10), i(18, 21)])) == [(10, 18)]


def test_restar_puede_dejar_el_dia_entero_fuera():
    assert restar([i(9, 19)], [i(0, 24)]) == []
