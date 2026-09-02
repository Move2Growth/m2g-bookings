"""De dónde salen los pesos del ranking y de la media bayesiana (ADR-0009).

Vive aparte porque lo necesitan **dos** sitios que no se conocen entre sí: la búsqueda, para
ordenar, y las reseñas, para recalcular el agregado de un negocio. Tenerlo duplicado sería la
forma más silenciosa de que la portada ordenara con unos pesos y el rating del perfil se
calculara con otros.

**Ni un número de ranking en el código.** Los valores por defecto del dato-clase
`PesosRanking` son la semilla de la primera fila, no la fuente de verdad: manda `ranking_weights`
y se cambia sin desplegar (ADM-4).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.dominio.ranking import PesosRanking
from agenda.modelos.marketplace import RankingWeights


async def pesos_vigentes(sesion: AsyncSession) -> PesosRanking:
    """La versión que manda hoy. **Si no hay fila, valores por defecto**, nunca ceros.

    Un ranking con todos los pesos a cero ordena al azar y nadie entendería por qué; y una
    media bayesiana con `m = 0` dispararía al primer negocio que reciba una reseña de cinco.
    """
    fila = (
        await sesion.execute(
            select(RankingWeights)
            # La vigente es la que no tiene fecha de cierre; el único parcial de la migración
            # garantiza que hay **exactamente una**. El orden por versión es el desempate por
            # si alguien insertó a mano y se saltó el cierre de la anterior.
            .where(RankingWeights.effective_to.is_(None))
            .order_by(RankingWeights.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if fila is None:
        return PesosRanking()

    return PesosRanking(
        distancia=float(fila.w_distancia),
        rating=float(fila.w_rating),
        reservas_recientes=float(fila.w_reservas_recientes),
        tasa_completado=float(fila.w_tasa_completado),
        completitud=float(fila.w_completitud),
        actividad=float(fila.w_actividad),
        boost_nuevo=float(fila.w_boost_nuevo),
        # La tabla guarda kilómetros porque es como se habla de un radio; la fórmula trabaja en
        # metros porque es lo que devuelve PostGIS. La conversión vive aquí y en un solo sitio:
        # repartirla es como se acaba comparando kilómetros con metros.
        radio_metros=float(fila.radius_km) * 1000,
        techo_reservas=int(fila.recent_cap),
        dias_boost_nuevo=int(fila.boost_days),
        rating_medio_global=float(fila.bayes_m),
        reviews_de_confianza=int(fila.bayes_c),
    )
