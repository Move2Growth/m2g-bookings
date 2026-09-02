"""El ranking del marketplace y el rating agregado (MKT-3, MKT-4, REV-5).

Igual que el motor de disponibilidad, esto es **puro**: recibe señales ya calculadas y unos
pesos, y devuelve una puntuación. Los pesos **no están aquí**: viven en la base de datos y se
cambian desde el back-office sin desplegar (ADR-0009). Si algún día aparece un número mágico
en este archivo, es un error: significa que alguien acaba de convertir una decisión de negocio
en un despliegue.

Dos reglas de negocio se materializan en este módulo y no admiten interpretación:

* **El patrocinio no toca el rating ni la puntuación orgánica.** Los patrocinados se resuelven
  aparte y se intercalan; nunca compiten en la fórmula ni desplazan a un orgánico fuera de la
  página.
* **Un negocio nuevo tiene que poder arrancar.** Sin el impulso temporal a los recién llegados,
  el marketplace nace cerrado para todo el que llega después, que el primer día son todos.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PesosRanking:
    """Una versión de los pesos, tal como se leen de `ranking_weights`.

    Los valores por defecto son solo la semilla de la primera fila: la fuente de verdad es la
    base de datos.
    """

    distancia: float = 0.30
    rating: float = 0.20
    reservas_recientes: float = 0.15
    tasa_completado: float = 0.15
    completitud: float = 0.10
    actividad: float = 0.10
    boost_nuevo: float = 0.15

    # Radio a partir del cual la distancia deja de aportar, en metros. Más allá, el negocio
    # sigue apareciendo si el filtro lo permite, pero la cercanía ya no le suma nada.
    radio_metros: float = 8000.0
    # Cuántas reservas recientes se consideran «muchas». Por encima ya no suma: sin techo, el
    # salón grande del centro se lleva todas las posiciones de todas las búsquedas.
    techo_reservas: int = 40
    # Cuántos días dura el impulso a los negocios nuevos y con qué intensidad empieza.
    dias_boost_nuevo: int = 30

    # Media global de la plataforma y número de reviews de confianza para la ponderación
    # bayesiana. La media se siembra con un valor razonable mientras no haya reviews: si se
    # dejara en cero, el primer negocio con una sola review de cinco estrellas se dispararía.
    rating_medio_global: float = 4.3
    reviews_de_confianza: int = 10


@dataclass(frozen=True)
class SenalesNegocio:
    """Lo que se sabe de un negocio en el momento de ordenar.

    Todo menos la distancia está **precalculado** por un trabajo periódico: recorrer las
    reservas de 5.000 negocios en cada búsqueda no cabe en los 500 ms de presupuesto.
    """

    distancia_metros: float | None
    suma_notas: int
    numero_reviews: int
    reservas_recientes: int
    completadas: int
    no_asistidas: int
    canceladas_por_negocio: int
    completitud_perfil: float  # 0 a 1, calculado del checklist del perfil (ONB-7)
    dias_desde_ultima_actividad: int
    dias_desde_publicacion: int


@dataclass(frozen=True)
class Puntuacion:
    """La puntuación y **de dónde sale cada punto**.

    El desglose no es un lujo de depuración: la primera llamada de un dueño enfadado es «¿por
    qué salgo el noveno?», y un ranking que nadie puede explicar es un ranking que nadie puede
    ajustar.
    """

    total: float
    desglose: dict[str, float] = field(default_factory=dict)


def rating_bayesiano(suma_notas: int, numero_reviews: int, pesos: PesosRanking) -> float:
    """Media ponderada hacia la media global cuando hay pocas reviews (REV-5).

    Una sola review de cinco estrellas no puede adelantar a un negocio con ochenta de 4,7. Con
    `n` pequeño el resultado se parece a la media de la plataforma; solo con volumen el negocio
    se separa de ella. Es la diferencia entre un orden creíble y una lotería.
    """
    if numero_reviews <= 0:
        return pesos.rating_medio_global
    confianza = pesos.reviews_de_confianza
    return (confianza * pesos.rating_medio_global + suma_notas) / (confianza + numero_reviews)


def _cercania(distancia_metros: float | None, radio: float) -> float:
    """1 en la puerta del cliente, 0 a partir del radio configurado."""
    if distancia_metros is None:
        return 0.0
    if distancia_metros <= 0:
        return 1.0
    return max(0.0, 1.0 - distancia_metros / radio)


def _tasa_completado(senales: SenalesNegocio) -> float:
    """Completadas sobre el total de citas que llegaron a su hora.

    Castiga a quien confirma y no atiende. Un negocio sin historial no se penaliza: se le da el
    beneficio de la duda con la media, o nunca podría empezar.
    """
    total = senales.completadas + senales.no_asistidas + senales.canceladas_por_negocio
    if total == 0:
        return 0.5
    return senales.completadas / total


def _actividad(dias: int) -> float:
    """Decae en dos semanas. Un perfil abandonado baja; uno que se toca a diario, no."""
    return max(0.0, 1.0 - dias / 14)


def _boost_nuevo(dias_desde_publicacion: int, dias_boost: int) -> float:
    """Impulso decreciente durante los primeros días de vida del negocio."""
    if dias_desde_publicacion >= dias_boost:
        return 0.0
    return 1.0 - dias_desde_publicacion / dias_boost


def puntuar(senales: SenalesNegocio, pesos: PesosRanking) -> Puntuacion:
    """Combina las señales normalizadas a 0–1 con sus pesos. Ni un número suelto por el camino."""
    rating = rating_bayesiano(senales.suma_notas, senales.numero_reviews, pesos)

    componentes = {
        "distancia": _cercania(senales.distancia_metros, pesos.radio_metros) * pesos.distancia,
        # El rating se lleva a 0–1 dividiendo por la nota máxima, que son cinco estrellas.
        "rating": (rating / 5.0) * pesos.rating,
        "reservas_recientes": (
            min(senales.reservas_recientes, pesos.techo_reservas) / pesos.techo_reservas
        )
        * pesos.reservas_recientes,
        "tasa_completado": _tasa_completado(senales) * pesos.tasa_completado,
        "completitud": min(max(senales.completitud_perfil, 0.0), 1.0) * pesos.completitud,
        "actividad": _actividad(senales.dias_desde_ultima_actividad) * pesos.actividad,
        "boost_nuevo": _boost_nuevo(senales.dias_desde_publicacion, pesos.dias_boost_nuevo)
        * pesos.boost_nuevo,
    }

    return Puntuacion(total=sum(componentes.values()), desglose=componentes)


def intercalar_patrocinados(
    organicos: list,
    patrocinados: list,
    *,
    por_pagina: int = 10,
    maximo_patrocinados: int = 2,
) -> list:
    """Mete los patrocinados **entre** los orgánicos sin quitar a ninguno (MKT-4).

    La palabra importante es *entre*. Un patrocinado ocupa una posición nueva, no la de otro:
    la página crece, y el orgánico que iba décimo sigue estando en la página. Si sustituyera,
    pagar equivaldría a tapar a la competencia, que es justo lo que el brief prohíbe.

    Los patrocinados que no caben en esta página **no se arrastran** a la siguiente: cada
    página respeta su propio límite. Quien pagó por aparecer en la primera no gana nada
    apareciendo en la séptima.
    """
    if not patrocinados:
        return list(organicos[:por_pagina])

    elegidos = list(patrocinados[:maximo_patrocinados])
    resultado = list(organicos[:por_pagina])

    # Se reparten en la página en vez de amontonarlos arriba: dos anuncios seguidos en las dos
    # primeras posiciones es exactamente la sensación que hace que la gente deje de mirar.
    hueco = max(1, len(resultado) // (len(elegidos) + 1))
    for indice, patrocinado in enumerate(elegidos):
        posicion = min(hueco * (indice + 1) + indice, len(resultado))
        resultado.insert(posicion, patrocinado)

    return resultado
