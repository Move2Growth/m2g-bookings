"""«Abierto ahora» (MKT-2), incluido el salón que cierra pasada la medianoche.

Es un filtro que parece trivial y tiene dos trampas, las dos con consecuencias visibles para
alguien que busca a las once de la noche:

* **El huso es el del negocio, no el del servidor.** Panamá va cinco horas por detrás de UTC,
  así que preguntar «¿está abierto?» a las 22:00 de Panamá es preguntarlo a las 03:00 UTC del
  día siguiente — y en UTC eso ya es otro día de la semana.
* **El tramo que cruza la medianoche pertenece al día en que abrió.** El spa que abre el
  viernes a las 15:00 y cierra a las 00:30 sigue abierto el sábado a las 00:15, y su fila dice
  «viernes».

Y una distinción que no es cosmética: un negocio **sin horario cargado** devuelve `None`, no
`False`. «No lo sé» y «está cerrado» se pintan distinto y se filtran distinto.
"""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from agenda.servicios.tarjetas import esta_abierto

PANAMA = ZoneInfo("America/Panama")

#: Lunes a viernes de 9:00 a 19:00, hora local. El horario normal de una barbería.
DE_NUEVE_A_SIETE = [(dia, time(9, 0), time(19, 0)) for dia in range(5)]

#: Viernes de 15:00 a 00:30: el spa que cierra pasada la medianoche, en una sola fila.
SPA_DE_NOCHE = [(4, time(15, 0), time(0, 30))]


def _en_panama(anio: int, mes: int, dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(anio, mes, dia, hora, minuto, tzinfo=PANAMA)


def test_sin_horario_cargado_la_respuesta_es_no_lo_se():
    """Un negocio a medio configurar no es un negocio cerrado, y no se pueden confundir."""
    assert esta_abierto([], "America/Panama", ahora=_en_panama(2026, 9, 2, 11)) is None


def test_un_miercoles_a_media_manana_esta_abierto():
    # 2026-09-02 es miércoles.
    abierto = esta_abierto(DE_NUEVE_A_SIETE, "America/Panama", ahora=_en_panama(2026, 9, 2, 11))
    assert abierto is True


def test_el_mismo_miercoles_a_las_ocho_de_la_manana_esta_cerrado():
    abierto = esta_abierto(DE_NUEVE_A_SIETE, "America/Panama", ahora=_en_panama(2026, 9, 2, 8))
    assert abierto is False


def test_justo_a_la_hora_de_cierre_ya_esta_cerrado():
    """Intervalo semiabierto `[abre, cierra)`, la misma convención que el motor y que la base.

    A las 19:00 en punto el salón está cerrando, no atendiendo; ofrecerlo como abierto manda a
    alguien a una puerta que se acaba de cerrar.
    """
    assert (
        esta_abierto(DE_NUEVE_A_SIETE, "America/Panama", ahora=_en_panama(2026, 9, 2, 19)) is False
    )


def test_el_domingo_esta_cerrado():
    # 2026-09-06 es domingo y no hay fila para ese día.
    assert (
        esta_abierto(DE_NUEVE_A_SIETE, "America/Panama", ahora=_en_panama(2026, 9, 6, 11)) is False
    )


def test_el_spa_de_noche_sigue_abierto_pasada_la_medianoche():
    """El caso que rompe la comprobación ingenua: el sábado a las 00:15 con la fila del viernes.

    Una comparación directa `abre <= hora < cierra` daría `15:00 <= 00:15 < 00:30`, que es
    falso, y el spa aparecería cerrado justo en el rato en que más gente lo busca.
    """

    # 2026-09-04 es viernes; 2026-09-05, sábado.
    def spa(dia: int, hora: int, minuto: int = 0) -> bool | None:
        return esta_abierto(
            SPA_DE_NOCHE, "America/Panama", ahora=_en_panama(2026, 9, dia, hora, minuto)
        )

    assert spa(4, 23) is True  # viernes por la noche
    assert spa(5, 0, 15) is True  # sábado de madrugada, todavía dentro del tramo del viernes
    assert spa(5, 0, 45) is False  # ya cerró


def test_el_huso_del_negocio_manda_y_no_el_del_servidor():
    """Las pruebas corren con `TZ=UTC` a propósito; el negocio está en Panamá.

    A las 02:00 UTC del jueves son las 21:00 del miércoles en Panamá: el salón está abierto
    aunque en el reloj del servidor ya sea otro día. Si esto se calculara en UTC, media ciudad
    aparecería cerrada cada noche.
    """
    instante_utc = datetime(2026, 9, 3, 2, 0, tzinfo=ZoneInfo("UTC"))
    # 21:00 de un miércoles en Panamá: fuera del horario de 9 a 19, pero **el mismo miércoles**.
    assert esta_abierto(DE_NUEVE_A_SIETE, "America/Panama", ahora=instante_utc) is False

    # Y a las 16:00 UTC son las 11:00 de Panamá del mismo día: abierto.
    instante_utc = datetime(2026, 9, 2, 16, 0, tzinfo=ZoneInfo("UTC"))
    assert esta_abierto(DE_NUEVE_A_SIETE, "America/Panama", ahora=instante_utc) is True


def test_la_jornada_partida_deja_cerrado_el_hueco_del_almuerzo():
    """Dos filas el mismo día: de 9 a 13 y de 15 a 19, que en un salón es la norma."""
    partida = [(2, time(9, 0), time(13, 0)), (2, time(15, 0), time(19, 0))]
    assert esta_abierto(partida, "America/Panama", ahora=_en_panama(2026, 9, 2, 10)) is True
    assert esta_abierto(partida, "America/Panama", ahora=_en_panama(2026, 9, 2, 14)) is False
    assert esta_abierto(partida, "America/Panama", ahora=_en_panama(2026, 9, 2, 16)) is True
