"""Los casos que rompen un motor de disponibilidad.

Cada prueba lleva el número del caso de `docs/arquitectura/fase-3-motor-disponibilidad.md` §6.
Los casos que necesitan una base de datos de verdad —la carrera por el mismo slot, el
aislamiento entre negocios, la idempotencia— viven en `pruebas/bd/`, porque lo que prueban es
la restricción de exclusión y el RLS, no esta aritmética.

Los datos son de un salón panameño real, no «Servicio 1 · 100,00»: con datos de mentira no se
ve que un balayage de tres horas no cabe en el hueco de las cinco de la tarde.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from agenda.dominio.disponibilidad import (
    AgendaProfesional,
    AjustesAgenda,
    ReglaHoraria,
    Servicio,
    calcular_slots,
    materializar,
    repartir_por_carga,
)
from agenda.dominio.tiempo import Intervalo

PANAMA = ZoneInfo("America/Panama")
MADRID = ZoneInfo("Europe/Madrid")
UTC = ZoneInfo("UTC")

# Servicios de verdad de una barbería y un salón de Ciudad de Panamá.
CORTE_BARBA = Servicio(duracion=timedelta(minutes=45), buffer_despues=timedelta(minutes=10))
CORTE = Servicio(duracion=timedelta(minutes=30), buffer_despues=timedelta(minutes=5))
BALAYAGE = Servicio(duracion=timedelta(hours=3), buffer_despues=timedelta(minutes=15))
MANICURA = Servicio(duracion=timedelta(minutes=75))

# Lunes a sábado, de 9:00 a 19:00.
HORARIO_NEGOCIO = [ReglaHoraria(dia, time(9, 0), time(19, 0)) for dia in range(0, 6)]


def local(anio: int, mes: int, dia: int, hora: int, minuto: int = 0, zona: ZoneInfo = PANAMA):
    """Un instante escrito en hora local, que es como lo diría el dueño del salón."""
    return datetime(anio, mes, dia, hora, minuto, tzinfo=zona).astimezone(UTC)


# Un miércoles cualquiera, con el reloj a las 8:00 de la mañana en Panamá.
AHORA = local(2026, 9, 2, 8, 0)


def horas_locales(slots, zona: ZoneInfo = PANAMA) -> list[str]:
    """Las horas de comienzo tal como se verían en la pantalla del salón."""
    return [s.inicio.astimezone(zona).strftime("%H:%M") for s in slots]


def calcular(**kwargs):
    base = dict(
        ahora=AHORA,
        zona="America/Panama",
        horario_negocio=HORARIO_NEGOCIO,
        servicios=[CORTE_BARBA],
        desde=local(2026, 9, 2, 0, 0),
        hasta=local(2026, 9, 3, 0, 0),
    )
    base.update(kwargs)
    return calcular_slots(**base)


def profesional(
    identificador: str = "ana",
    horario=None,
    ocupacion=(),
    ausencias=(),
    activo: bool = True,
) -> AgendaProfesional:
    return AgendaProfesional(
        profesional_id=identificador,
        horario=horario if horario is not None else HORARIO_NEGOCIO,
        ocupacion=ocupacion,
        ausencias=ausencias,
        activo=activo,
    )


# ── Caso 16 · La rejilla es de comienzos, no de duraciones ────────────────────────────────


def test_la_rejilla_marca_los_comienzos_no_la_duracion():
    """Con rejilla de 15 min y servicio de 45, se empieza a las 9:00, 9:15, 9:30…

    Confundir la rejilla con la duración es el error clásico: obliga a que todo dure múltiplos
    de quince minutos y deja huecos muertos por toda la agenda.
    """
    slots = calcular(profesionales=[profesional()])

    assert horas_locales(slots)[:4] == ["09:00", "09:15", "09:30", "09:45"]


def test_la_rejilla_se_ancla_a_la_medianoche_no_a_la_apertura():
    """Un negocio que abre a las 9:05 ofrece 9:15, no 9:05, 9:20, 9:35."""
    horario = [ReglaHoraria(2, time(9, 5), time(19, 0))]
    slots = calcular(horario_negocio=horario, profesionales=[profesional(horario=horario)])

    assert horas_locales(slots)[0] == "09:15"


# ── Caso 2 · Un buffer que cruza el final de la jornada ───────────────────────────────────


def test_el_buffer_posterior_tiene_que_caber_antes_del_cierre():
    """El corte de 45 min con 10 de limpieza no cabe empezando a las 18:15: cierra a las 19:00.

    18:15 + 45 = 19:00, que encaja justo… pero la limpieza se sale hasta las 19:10. Ese hueco
    no se ofrece: el profesional se iría a casa dejando el puesto sin recoger.
    """
    slots = calcular(profesionales=[profesional()])

    assert horas_locales(slots)[-1] == "18:00"
    assert "18:15" not in horas_locales(slots)


def test_sin_buffer_el_ultimo_hueco_llega_hasta_el_cierre():
    """El mismo servicio sin limpieza sí puede terminar clavado a las 19:00."""
    sin_buffer = Servicio(duracion=timedelta(minutes=45))
    slots = calcular(servicios=[sin_buffer], profesionales=[profesional()])

    assert horas_locales(slots)[-1] == "18:15"


def test_el_buffer_anterior_no_bloquea_el_primer_hueco_del_dia():
    """A primera hora no hay cliente anterior del que separarse."""
    con_preparacion = Servicio(duracion=timedelta(minutes=30), buffer_antes=timedelta(minutes=20))
    slots = calcular(servicios=[con_preparacion], profesionales=[profesional()])

    assert horas_locales(slots)[0] == "09:00"


# ── Caso 3 · El profesional con horario distinto del negocio ──────────────────────────────


def test_solo_se_ofrece_la_interseccion_con_el_horario_del_profesional():
    """La peluquera que solo trabaja de tarde es la mitad de los salones, no la excepción."""
    solo_tardes = [ReglaHoraria(2, time(14, 0), time(19, 0))]
    slots = calcular(profesionales=[profesional(horario=solo_tardes)])

    assert horas_locales(slots)[0] == "14:00"
    assert horas_locales(slots)[-1] == "18:00"


def test_el_profesional_no_puede_trabajar_con_el_negocio_cerrado():
    """Aunque su horario diga que empieza a las 7:00, el negocio abre a las 9:00."""
    madruga = [ReglaHoraria(2, time(7, 0), time(19, 0))]
    slots = calcular(profesionales=[profesional(horario=madruga)])

    assert horas_locales(slots)[0] == "09:00"


# ── Caso 5 · Un servicio más largo que el hueco que queda ─────────────────────────────────


def test_un_balayage_de_tres_horas_no_cabe_a_las_cinco_de_la_tarde():
    """Cierra a las 19:00: el último balayage posible empieza a las 15:45 por los 15 de recogida."""
    slots = calcular(servicios=[BALAYAGE], profesionales=[profesional()])

    assert horas_locales(slots)[-1] == "15:45"
    assert "17:00" not in horas_locales(slots)


def test_un_servicio_que_no_cabe_en_ningun_hueco_no_devuelve_nada():
    jornada_corta = [ReglaHoraria(2, time(9, 0), time(11, 0))]
    slots = calcular(
        servicios=[BALAYAGE],
        horario_negocio=jornada_corta,
        profesionales=[profesional(horario=jornada_corta)],
    )

    assert slots == []


# ── Caso 6 · Multi-servicio encadenado (D13) ──────────────────────────────────────────────


def test_los_servicios_encadenados_necesitan_un_bloque_continuo():
    """Corte + barba y manicura seguidos son 45 + 75 = 2 h, no dos huecos sueltos de 45 y 75."""
    ocupado_a_las_diez = [Intervalo(local(2026, 9, 2, 10, 0), local(2026, 9, 2, 10, 30))]
    slots = calcular(
        servicios=[CORTE_BARBA, MANICURA],
        profesionales=[profesional(ocupacion=ocupado_a_las_diez)],
    )

    horas = horas_locales(slots)
    # A las 9:00 no cabe: el bloque de dos horas chocaría con la cita de las 10:00.
    assert "09:00" not in horas
    assert horas[0] == "10:30"
    assert slots[0].fin.astimezone(PANAMA).strftime("%H:%M") == "12:30"


def test_los_buffers_intermedios_no_se_aplican_entre_servicios_encadenados():
    """El cliente no se levanta de la silla entre el corte y la manicura.

    Se aplican el buffer anterior del primero y el posterior del último, y nada más: si se
    aplicaran todos, dos servicios seguidos ocuparían más tiempo del que de verdad llevan.
    """
    slots = calcular(servicios=[CORTE_BARBA, MANICURA], profesionales=[profesional()])

    primero = slots[0]
    assert primero.fin - primero.inicio == timedelta(minutes=120)


# ── Caso 7 · Bloqueo recurrente contra bloqueo puntual ────────────────────────────────────


def test_el_almuerzo_diario_y_un_bloqueo_puntual_conviven():
    """El almuerzo de todos los días parte la jornada; el bloqueo del miércoles se suma."""
    manana_y_tarde = [
        ReglaHoraria(2, time(9, 0), time(13, 0)),
        ReglaHoraria(2, time(14, 0), time(19, 0)),
    ]
    dentista = [Intervalo(local(2026, 9, 2, 16, 0), local(2026, 9, 2, 17, 0))]
    slots = calcular(
        profesionales=[profesional(horario=manana_y_tarde, ausencias=dentista)],
    )
    horas = horas_locales(slots)

    assert "12:00" in horas  # cabe antes del almuerzo: 12:00 + 45 + 10 = 12:55
    assert "12:15" not in horas  # se saldría del almuerzo
    assert "14:00" in horas
    assert "16:00" not in horas  # el dentista
    assert "17:00" in horas


def test_dos_tramos_contiguos_son_una_jornada_continua():
    """9:00–13:00 y 13:00–19:00 no son dos jornadas: un balayage a las 12:00 tiene que caber."""
    partido = [
        ReglaHoraria(2, time(9, 0), time(13, 0)),
        ReglaHoraria(2, time(13, 0), time(19, 0)),
    ]
    slots = calcular(
        servicios=[BALAYAGE], horario_negocio=partido, profesionales=[profesional(horario=partido)]
    )

    assert "12:00" in horas_locales(slots)


# ── Caso 9 · Un cierre que cruza la medianoche ────────────────────────────────────────────


def test_un_spa_abierto_hasta_las_00_30_ofrece_huecos_despues_de_medianoche():
    """15:00 → 00:30 es un solo tramo, no dos, y la última cita tiene que caber entera."""
    nocturno = [ReglaHoraria(2, time(15, 0), time(0, 30))]
    slots = calcular(
        servicios=[MANICURA],
        horario_negocio=nocturno,
        profesionales=[profesional(horario=nocturno)],
        desde=local(2026, 9, 2, 0, 0),
        hasta=local(2026, 9, 4, 0, 0),
    )
    horas = horas_locales(slots)

    assert horas[0] == "15:00"
    assert "23:00" in horas
    assert "23:30" not in horas  # 23:30 + 1 h 15 = 00:45, se pasaría del cierre
    # La última manicura empieza a las 23:15 y termina clavada a las 00:30, ya del día siguiente.
    assert horas[-1] == "23:15"
    assert slots[-1].fin.astimezone(PANAMA).strftime("%H:%M") == "00:30"
    assert slots[-1].fin.astimezone(PANAMA).day == 3


# ── Caso 10 · Antelación mínima y máxima ──────────────────────────────────────────────────


def test_no_se_ofrece_nada_dentro_de_la_antelacion_minima():
    """Son las 8:00 y la antelación es de una hora: las 9:00 valen, pero por los pelos."""
    ahora_tarde = local(2026, 9, 2, 9, 30)
    slots = calcular(ahora=ahora_tarde, profesionales=[profesional()])

    assert horas_locales(slots)[0] == "10:30"


def test_la_antelacion_maxima_corta_la_ventana():
    """Con 60 días de máximo, pedir dentro de un año no devuelve nada. Y no es un error."""
    slots = calcular(
        profesionales=[profesional()],
        desde=local(2027, 9, 2, 0, 0),
        hasta=local(2027, 9, 3, 0, 0),
    )

    assert slots == []


def test_la_antelacion_es_configurable_por_negocio():
    sin_antelacion = AjustesAgenda(antelacion_minima=timedelta(0))
    slots = calcular(
        ahora=local(2026, 9, 2, 9, 30), ajustes=sin_antelacion, profesionales=[profesional()]
    )

    assert horas_locales(slots)[0] == "09:30"


# ── Caso 8 · Husos horarios: Panamá no tiene cambio de hora, Madrid sí ────────────────────


def test_panama_no_tiene_horario_de_verano():
    """El mismo horario en marzo y en noviembre da exactamente los mismos huecos locales."""
    marzo = calcular(
        ahora=local(2026, 3, 3, 8, 0),
        desde=local(2026, 3, 4, 0, 0),
        hasta=local(2026, 3, 5, 0, 0),
        profesionales=[profesional()],
    )
    noviembre = calcular(
        ahora=local(2026, 11, 3, 8, 0),
        desde=local(2026, 11, 4, 0, 0),
        hasta=local(2026, 11, 5, 0, 0),
        profesionales=[profesional()],
    )

    assert horas_locales(marzo) == horas_locales(noviembre)


def test_el_dia_que_adelantan_el_reloj_en_madrid_la_jornada_dura_una_hora_menos():
    """29 de marzo de 2026: a las 2:00 son las 3:00. Una jornada de 00:00 a 06:00 dura cinco horas.

    Es la prueba de que el modelo aguanta España sin tocar el motor: nada en el cálculo sabe
    que existe el horario de verano, y aun así sale bien.
    """
    madrugada = [ReglaHoraria(6, time(0, 0), time(6, 0))]  # domingo
    tramos = materializar(
        madrugada,
        zona=MADRID,
        desde=datetime(2026, 3, 28, tzinfo=UTC),
        hasta=datetime(2026, 3, 30, tzinfo=UTC),
    )

    assert len(tramos) == 1
    assert tramos[0].duracion == timedelta(hours=5)


def test_el_dia_que_atrasan_el_reloj_en_madrid_la_jornada_dura_una_hora_mas():
    """25 de octubre de 2026: las 3:00 vuelven a ser las 2:00. Seis horas de reloj son siete."""
    madrugada = [ReglaHoraria(6, time(0, 0), time(6, 0))]
    tramos = materializar(
        madrugada,
        zona=MADRID,
        desde=datetime(2026, 10, 24, tzinfo=UTC),
        hasta=datetime(2026, 10, 26, tzinfo=UTC),
    )

    assert len(tramos) == 1
    assert tramos[0].duracion == timedelta(hours=7)


# ── Caso 13 y 14 · Varios profesionales ───────────────────────────────────────────────────


def test_cualquier_profesional_disponible_no_duplica_la_misma_hora():
    """Tres barberos libres a las 10:00 son un hueco de las 10:00, no tres."""
    equipo = [profesional("ana"), profesional("beto"), profesional("carlos")]
    slots = calcular(profesionales=equipo)
    unicos = repartir_por_carga(slots, carga={"ana": 5, "beto": 1, "carlos": 3})
    horas = horas_locales(unicos)

    assert len(horas) == len(set(horas))
    # A igualdad de hora se lo lleva quien menos agenda tiene, no el primero de la lista.
    assert unicos[0].profesional_id == "beto"


def test_el_profesional_de_vacaciones_no_aparece_ni_por_cualquiera():
    vacaciones = [Intervalo(local(2026, 9, 1, 0, 0), local(2026, 9, 15, 0, 0))]
    slots = calcular(profesionales=[profesional("ana", ausencias=vacaciones), profesional("beto")])

    assert {s.profesional_id for s in slots} == {"beto"}


def test_el_profesional_inactivo_no_ofrece_nada():
    slots = calcular(profesionales=[profesional("ana", activo=False)])

    assert slots == []


# ── Caso 17 · Festivos aceptados ──────────────────────────────────────────────────────────


def test_un_festivo_aceptado_cierra_el_dia_entero():
    """3 de noviembre, separación de Colombia. Si el negocio aceptó el feriado, no abre."""
    feriado = [Intervalo(local(2026, 11, 3, 0, 0), local(2026, 11, 4, 0, 0))]
    slots = calcular(
        ahora=local(2026, 11, 2, 8, 0),
        desde=local(2026, 11, 3, 0, 0),
        hasta=local(2026, 11, 4, 0, 0),
        cierres=feriado,
        profesionales=[profesional()],
    )

    assert slots == []


def test_un_festivo_rechazado_deja_el_dia_normal():
    slots = calcular(
        ahora=local(2026, 11, 2, 8, 0),
        desde=local(2026, 11, 3, 0, 0),
        hasta=local(2026, 11, 4, 0, 0),
        cierres=[],
        profesionales=[profesional()],
    )

    assert horas_locales(slots)[0] == "09:00"


# ── Ocupación y buffers frente a citas ya existentes ──────────────────────────────────────


def test_una_cita_existente_tapa_su_hueco_y_el_buffer_de_la_siguiente():
    """Cita de 10:00 a 10:45 con 10 de limpieza: la siguiente no puede empezar antes de 10:55.

    Con rejilla de 15 minutos, el primer comienzo posible es las 11:00.
    """
    cita = [Intervalo(local(2026, 9, 2, 10, 0), local(2026, 9, 2, 10, 55))]
    slots = calcular(profesionales=[profesional(ocupacion=cita)])
    horas = horas_locales(slots)

    assert "09:45" not in horas  # terminaría a las 10:30, dentro de la cita
    assert "10:45" not in horas
    assert "11:00" in horas


def test_dos_citas_pegadas_no_se_solapan_por_el_extremo():
    """Los intervalos son semiabiertos: lo que acaba a las 10:00 y lo que empieza a las 10:00 caben.

    Es la misma convención que la restricción de exclusión de la base (ADR-0004). Si aquí se
    usara una y allí otra, el motor ofrecería huecos que la base rechazaría al confirmar.
    """
    sin_buffer = Servicio(duracion=timedelta(hours=1))
    cita = [Intervalo(local(2026, 9, 2, 10, 0), local(2026, 9, 2, 11, 0))]
    slots = calcular(servicios=[sin_buffer], profesionales=[profesional(ocupacion=cita)])
    horas = horas_locales(slots)

    assert "09:00" in horas  # termina justo cuando empieza la cita
    assert "11:00" in horas  # empieza justo cuando termina
    assert "10:00" not in horas


def test_el_dia_de_cierre_no_ofrece_nada():
    """Domingo: el negocio abre de lunes a sábado."""
    slots = calcular(
        ahora=local(2026, 9, 5, 8, 0),
        desde=local(2026, 9, 6, 0, 0),
        hasta=local(2026, 9, 7, 0, 0),
        profesionales=[profesional()],
    )

    assert slots == []


def test_sin_servicios_es_un_error_de_programacion_no_una_lista_vacia():
    with pytest.raises(ValueError):
        calcular(servicios=[], profesionales=[profesional()])
