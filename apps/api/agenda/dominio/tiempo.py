"""Intervalos de tiempo y operaciones sobre ellos.

Todo lo que sale de aquí son **instantes en UTC** (ADR-0003). La conversión desde las reglas
horarias locales de un negocio ocurre en `disponibilidad.py` y en ningún otro sitio.

Los intervalos son **semiabiertos**: `[inicio, fin)`. Es la misma convención que usa la
restricción de exclusión de la base de datos (ADR-0004), y es lo que hace que una cita que
termina a las 10:00 y otra que empieza a las 10:00 no se solapen. Si aquí se usara una
convención y en la base otra, el motor ofrecería huecos que la base rechaza.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, order=True)
class Intervalo:
    """Un tramo de tiempo semiabierto `[inicio, fin)`, siempre con huso horario."""

    inicio: datetime
    fin: datetime

    def __post_init__(self) -> None:
        if self.inicio.tzinfo is None or self.fin.tzinfo is None:
            raise ValueError("Un Intervalo necesita instantes con huso horario, no fechas ingenuas")
        if self.fin < self.inicio:
            raise ValueError(
                f"Intervalo al revés: {self.inicio.isoformat()} → {self.fin.isoformat()}"
            )

    @property
    def duracion(self) -> timedelta:
        return self.fin - self.inicio

    @property
    def vacio(self) -> bool:
        return self.fin <= self.inicio

    def solapa(self, otro: Intervalo) -> bool:
        return self.inicio < otro.fin and otro.inicio < self.fin

    def contiene(self, otro: Intervalo) -> bool:
        return self.inicio <= otro.inicio and otro.fin <= self.fin

    def interseccion(self, otro: Intervalo) -> Intervalo | None:
        inicio = max(self.inicio, otro.inicio)
        fin = min(self.fin, otro.fin)
        return Intervalo(inicio, fin) if inicio < fin else None


def normalizar(intervalos: Iterable[Intervalo]) -> list[Intervalo]:
    """Ordena, funde los que se tocan o se solapan y descarta los vacíos.

    Fundir los que se **tocan** (y no solo los que se solapan) es importante: dos tramos
    contiguos como 09:00–13:00 y 13:00–19:00 son una jornada continua, y si no se fundieran,
    un servicio de tres horas a las 12:00 parecería no caber en ninguno de los dos.
    """
    ordenados = sorted((i for i in intervalos if not i.vacio), key=lambda i: (i.inicio, i.fin))
    fundidos: list[Intervalo] = []
    for actual in ordenados:
        if fundidos and actual.inicio <= fundidos[-1].fin:
            ultimo = fundidos[-1]
            fundidos[-1] = Intervalo(ultimo.inicio, max(ultimo.fin, actual.fin))
        else:
            fundidos.append(actual)
    return fundidos


def intersecar(a: Sequence[Intervalo], b: Sequence[Intervalo]) -> list[Intervalo]:
    """Intersección de dos listas de tramos. Es el ∩ de la fórmula del slot libre."""
    izquierda, derecha = normalizar(a), normalizar(b)
    resultado: list[Intervalo] = []
    i = j = 0
    while i < len(izquierda) and j < len(derecha):
        comun = izquierda[i].interseccion(derecha[j])
        if comun is not None:
            resultado.append(comun)
        # Avanza el que termina antes: el otro todavía puede cruzarse con el siguiente.
        if izquierda[i].fin <= derecha[j].fin:
            i += 1
        else:
            j += 1
    return resultado


def restar(base: Sequence[Intervalo], quitar: Sequence[Intervalo]) -> list[Intervalo]:
    """Quita de `base` todo lo que cubra `quitar`. Es el − de la fórmula del slot libre."""
    pendientes = normalizar(base)
    for hueco in normalizar(quitar):
        siguiente: list[Intervalo] = []
        for tramo in pendientes:
            if not tramo.solapa(hueco):
                siguiente.append(tramo)
                continue
            if tramo.inicio < hueco.inicio:
                siguiente.append(Intervalo(tramo.inicio, hueco.inicio))
            if hueco.fin < tramo.fin:
                siguiente.append(Intervalo(hueco.fin, tramo.fin))
        pendientes = siguiente
    return normalizar(pendientes)
