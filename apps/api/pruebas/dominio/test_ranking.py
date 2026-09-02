"""El ranking del marketplace: las reglas de negocio que no se negocian.

Estas pruebas existen sobre todo para que nadie «mejore» el ranking sin darse cuenta de que
está rompiendo una promesa del producto: que una review de cinco estrellas no adelante a un
negocio con ochenta, que un negocio nuevo pueda arrancar, y que pagar nunca tape a nadie.
"""

from __future__ import annotations

from dataclasses import replace

from agenda.dominio.ranking import (
    PesosRanking,
    SenalesNegocio,
    intercalar_patrocinados,
    puntuar,
    rating_bayesiano,
)

PESOS = PesosRanking()


def senales(**cambios) -> SenalesNegocio:
    """Una barbería promedio de Ciudad de Panamá: dos años abierta, buen historial, cerca."""
    base = SenalesNegocio(
        distancia_metros=1200,
        suma_notas=376,  # 80 reviews de 4,7 de media
        numero_reviews=80,
        reservas_recientes=25,
        completadas=200,
        no_asistidas=8,
        canceladas_por_negocio=2,
        completitud_perfil=0.9,
        dias_desde_ultima_actividad=0,
        dias_desde_publicacion=700,
    )
    return replace(base, **cambios)


# ── Rating bayesiano (REV-5) ──────────────────────────────────────────────────────────────


def test_una_sola_review_de_cinco_no_adelanta_a_ochenta_de_casi_cinco():
    """El caso exacto que el brief pide evitar."""
    novato = rating_bayesiano(suma_notas=5, numero_reviews=1, pesos=PESOS)
    veterano = rating_bayesiano(suma_notas=376, numero_reviews=80, pesos=PESOS)

    assert novato < veterano


def test_sin_reviews_el_negocio_vale_lo_que_la_media_de_la_plataforma():
    """Ni premiado ni castigado por no tener historial todavía."""
    assert rating_bayesiano(0, 0, PESOS) == PESOS.rating_medio_global


def test_con_muchas_reviews_el_rating_converge_a_la_media_real():
    """Con volumen, la ponderación deja de tirar hacia la media global."""
    real = 4.9
    con_volumen = rating_bayesiano(suma_notas=int(real * 500), numero_reviews=500, pesos=PESOS)

    assert abs(con_volumen - real) < 0.05


def test_un_negocio_malo_con_volumen_tampoco_se_salva_por_la_media():
    malo = rating_bayesiano(suma_notas=int(2.1 * 300), numero_reviews=300, pesos=PESOS)

    assert malo < 2.3


# ── La fórmula ────────────────────────────────────────────────────────────────────────────


def test_el_desglose_explica_de_donde_sale_cada_punto():
    """Sin desglose no se puede responder a «¿por qué salgo el noveno?»."""
    resultado = puntuar(senales(), PESOS)

    assert set(resultado.desglose) == {
        "distancia",
        "rating",
        "reservas_recientes",
        "tasa_completado",
        "completitud",
        "actividad",
        "boost_nuevo",
    }
    assert abs(sum(resultado.desglose.values()) - resultado.total) < 1e-9


def test_mas_cerca_puntua_mas_si_todo_lo_demas_es_igual():
    cerca = puntuar(senales(distancia_metros=300), PESOS)
    lejos = puntuar(senales(distancia_metros=6000), PESOS)

    assert cerca.total > lejos.total


def test_pasado_el_radio_la_distancia_deja_de_restar():
    """Más allá del radio configurado, estar el doble de lejos ya no cambia nada."""
    lejos = puntuar(senales(distancia_metros=20_000), PESOS)
    lejisimos = puntuar(senales(distancia_metros=40_000), PESOS)

    assert lejos.desglose["distancia"] == lejisimos.desglose["distancia"] == 0.0


def test_el_salon_enorme_no_puede_dominarlo_todo_por_volumen():
    """Las reservas recientes tienen techo: por encima, más volumen ya no suma."""
    grande = puntuar(senales(reservas_recientes=PESOS.techo_reservas), PESOS)
    gigante = puntuar(senales(reservas_recientes=PESOS.techo_reservas * 10), PESOS)

    assert grande.desglose["reservas_recientes"] == gigante.desglose["reservas_recientes"]


def test_confirmar_y_no_atender_penaliza():
    """La tasa de completado es lo que separa a quien acepta citas de quien las cumple."""
    cumplidor = puntuar(senales(completadas=200, no_asistidas=2), PESOS)
    incumplidor = puntuar(senales(completadas=200, no_asistidas=150), PESOS)

    assert cumplidor.total > incumplidor.total


def test_un_perfil_abandonado_baja():
    activo = puntuar(senales(dias_desde_ultima_actividad=0), PESOS)
    olvidado = puntuar(senales(dias_desde_ultima_actividad=60), PESOS)

    assert activo.total > olvidado.total
    assert olvidado.desglose["actividad"] == 0.0


def test_el_perfil_completo_puntua_mas_que_el_perfil_a_medias():
    """Es la palanca que el negocio controla, y por eso el checklist tiene sentido."""
    completo = puntuar(senales(completitud_perfil=1.0), PESOS)
    a_medias = puntuar(senales(completitud_perfil=0.3), PESOS)

    assert completo.total > a_medias.total


# ── El boost a los negocios nuevos ────────────────────────────────────────────────────────


def test_un_negocio_recien_publicado_puede_competir_desde_el_primer_dia():
    """Sin este impulso el marketplace nace cerrado para todo el que llegue después.

    El recién llegado no tiene reviews, ni reservas, ni historial de completado: sin boost, su
    puntuación sería casi cero y nunca aparecería, así que nunca conseguiría su primera
    reserva. Es el bucle que hay que romper.
    """
    recien_llegado = puntuar(
        senales(
            suma_notas=0,
            numero_reviews=0,
            reservas_recientes=0,
            completadas=0,
            no_asistidas=0,
            canceladas_por_negocio=0,
            dias_desde_publicacion=0,
        ),
        PESOS,
    )
    veterano_flojo = puntuar(
        senales(
            suma_notas=int(3.0 * 40),
            numero_reviews=40,
            reservas_recientes=2,
            completadas=40,
            no_asistidas=25,
            completitud_perfil=0.4,
            dias_desde_ultima_actividad=20,
        ),
        PESOS,
    )

    assert recien_llegado.total > veterano_flojo.total


def test_el_impulso_se_apaga_solo_al_pasar_los_dias():
    dia_uno = puntuar(senales(dias_desde_publicacion=0), PESOS)
    a_mitad = puntuar(senales(dias_desde_publicacion=PESOS.dias_boost_nuevo // 2), PESOS)
    pasado = puntuar(senales(dias_desde_publicacion=PESOS.dias_boost_nuevo + 1), PESOS)

    assert dia_uno.desglose["boost_nuevo"] > a_mitad.desglose["boost_nuevo"] > 0
    assert pasado.desglose["boost_nuevo"] == 0.0


# ── Patrocinados (MKT-4, ADS-7) ───────────────────────────────────────────────────────────


def test_los_patrocinados_se_intercalan_sin_echar_a_nadie():
    """La página crece: el orgánico que iba décimo sigue en la página."""
    organicos = [f"organico-{n}" for n in range(1, 11)]
    patrocinados = ["pagado-a", "pagado-b"]

    pagina = intercalar_patrocinados(organicos, patrocinados)

    for negocio in organicos:
        assert negocio in pagina
    assert len(pagina) == 12


def test_nunca_hay_mas_de_dos_patrocinados_por_pagina():
    organicos = [f"organico-{n}" for n in range(1, 11)]
    muchos = [f"pagado-{n}" for n in range(1, 9)]

    pagina = intercalar_patrocinados(organicos, muchos)

    assert sum(1 for x in pagina if x.startswith("pagado")) == 2


def test_los_patrocinados_no_se_amontonan_al_principio():
    """Dos anuncios seguidos arriba es lo que hace que la gente deje de mirar la lista."""
    organicos = [f"organico-{n}" for n in range(1, 11)]
    pagina = intercalar_patrocinados(organicos, ["pagado-a", "pagado-b"])

    posiciones = [i for i, x in enumerate(pagina) if x.startswith("pagado")]

    assert posiciones[0] > 0  # el primer resultado es orgánico
    assert posiciones[1] - posiciones[0] > 1  # y no van pegados


def test_sin_patrocinados_la_pagina_es_solo_organica():
    organicos = [f"organico-{n}" for n in range(1, 15)]

    assert intercalar_patrocinados(organicos, []) == organicos[:10]
