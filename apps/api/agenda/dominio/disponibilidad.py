"""El motor de disponibilidad (AGD).

    slot libre = horario del negocio ∩ horario del profesional
                 − bloqueos − reservas existentes − buffers

Este módulo es **puro**: no toca la base de datos, no mira el reloj y no sabe qué es una
petición HTTP. Recibe reglas horarias, ocupación y un instante «ahora», y devuelve huecos.
Esa pureza es deliberada: es lo que permite probar los dieciocho casos de
`docs/arquitectura/fase-3-motor-disponibilidad.md` sin levantar nada.

Lo que este módulo **no** decide es si una reserva se puede crear. Eso lo decide la base de
datos con la restricción de exclusión (ADR-0004). Aquí se calcula lo que se ofrece; allí se
resuelve quién gana cuando dos personas quieren el mismo hueco a la vez.

Sobre los buffers hay una asimetría que conviene entender antes de tocar nada:

* El **buffer posterior** tiene que caber dentro de la jornada. Si un servicio termina justo
  al cierre pero su limpieza se sale, ese hueco no se ofrece: el profesional se iría a casa
  dejando el puesto sin recoger.
* El **buffer anterior** solo se comprueba contra la ocupación, no contra el principio de la
  jornada. Es tiempo de preparación entre clientes; a primera hora no hay cliente anterior del
  que separarse, y exigirlo dejaría el primer hueco del día siempre inservible.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from agenda.dominio.tiempo import Intervalo, intersecar, normalizar, restar

# Un día entero. Se usa para recorrer el calendario día a día al materializar el horario.
UN_DIA = timedelta(days=1)


@dataclass(frozen=True)
class ReglaHoraria:
    """Un tramo semanal en **hora local** del negocio: «los martes de 9:00 a 19:00».

    No es un instante y no puede serlo: no tiene fecha. Se convierte a instantes en
    `materializar`, que es el único sitio del proyecto donde se hace aritmética de husos.

    Si `cierra` es menor o igual que `abre`, el tramo **cruza la medianoche**: un spa abierto
    de 15:00 a 00:30 se modela así, con una sola fila, y no partido en dos.
    """

    dia_semana: int  # 0 = lunes … 6 = domingo, como `date.weekday()`
    abre: time
    cierra: time

    def __post_init__(self) -> None:
        if not 0 <= self.dia_semana <= 6:
            raise ValueError(f"día de la semana fuera de rango: {self.dia_semana}")

    @property
    def cruza_medianoche(self) -> bool:
        return self.cierra <= self.abre


@dataclass(frozen=True)
class AjustesAgenda:
    """Los tres parámetros configurables por negocio (AGD-1), con sus valores por defecto."""

    granularidad: timedelta = timedelta(minutes=15)
    antelacion_minima: timedelta = timedelta(hours=1)
    antelacion_maxima: timedelta = timedelta(days=60)

    def __post_init__(self) -> None:
        if self.granularidad <= timedelta(0):
            raise ValueError("la granularidad tiene que ser positiva")


@dataclass(frozen=True)
class Servicio:
    """Lo mínimo que el motor necesita saber de un servicio para colocarlo en la agenda."""

    duracion: timedelta
    buffer_antes: timedelta = timedelta(0)
    buffer_despues: timedelta = timedelta(0)


@dataclass(frozen=True)
class Slot:
    """Un hueco ofrecible. `inicio` y `fin` son los del **servicio**, sin los buffers.

    El slot **no reserva nada** y no lleva identificador reservable: no se aparta un hueco al
    mirarlo. Quien confirma compite por él, y la base decide (ADR-0004).
    """

    inicio: datetime
    fin: datetime
    profesional_id: str | None = None

    @property
    def intervalo(self) -> Intervalo:
        return Intervalo(self.inicio, self.fin)


@dataclass(frozen=True)
class AgendaProfesional:
    """Todo lo que hay que saber de un profesional para calcular sus huecos."""

    profesional_id: str
    horario: Sequence[ReglaHoraria]
    ocupacion: Sequence[Intervalo] = field(default_factory=tuple)
    ausencias: Sequence[Intervalo] = field(default_factory=tuple)
    activo: bool = True


def materializar(
    reglas: Sequence[ReglaHoraria],
    *,
    zona: ZoneInfo,
    desde: datetime,
    hasta: datetime,
) -> list[Intervalo]:
    """Convierte reglas semanales locales en instantes UTC dentro de la ventana pedida.

    **Este es el único sitio donde se convierte hora local a instante.** Todo lo demás del
    motor trabaja ya en UTC, y por eso un negocio en Madrid, con cambio de hora, sale bien
    sin que ninguna otra función se entere de que existe el horario de verano: el 26 de
    octubre una jornada de 00:00 a 06:00 dura siete horas de reloj, y el 29 de marzo dura
    cinco, porque así es como pasa el tiempo esos dos días.
    """
    if hasta <= desde:
        return []

    por_dia: dict[int, list[ReglaHoraria]] = {}
    for regla in reglas:
        por_dia.setdefault(regla.dia_semana, []).append(regla)

    # Se empieza un día antes porque un tramo que cruza la medianoche del día anterior puede
    # asomar dentro de la ventana, y se terminaría perdiendo la madrugada del primer día.
    dia: date = (desde.astimezone(zona) - UN_DIA).date()
    ultimo: date = (hasta.astimezone(zona)).date()

    tramos: list[Intervalo] = []
    while dia <= ultimo:
        for regla in por_dia.get(dia.weekday(), ()):
            inicio_local = datetime.combine(dia, regla.abre, tzinfo=zona)
            fin_dia = dia + UN_DIA if regla.cruza_medianoche else dia
            fin_local = datetime.combine(fin_dia, regla.cierra, tzinfo=zona)
            tramo = Intervalo(
                inicio_local.astimezone(desde.tzinfo),
                fin_local.astimezone(desde.tzinfo),
            )
            recortado = tramo.interseccion(Intervalo(desde, hasta))
            if recortado is not None:
                tramos.append(recortado)
        dia += UN_DIA

    return normalizar(tramos)


def _alinear_a_rejilla(instante: datetime, *, zona: ZoneInfo, granularidad: timedelta) -> datetime:
    """Redondea hacia arriba al siguiente punto de la rejilla, en **hora local**.

    La rejilla se ancla a la medianoche local, no al principio del tramo: con granularidad de
    15 minutos, los comienzos son 9:00, 9:15, 9:30… aunque el negocio abra a las 9:05. Anclarla
    al tramo daría 9:05, 9:20, 9:35, que no es lo que nadie espera ver en un calendario.
    """
    local = instante.astimezone(zona)
    medianoche = datetime.combine(local.date(), time(0, 0), tzinfo=zona)
    transcurrido = local - medianoche
    pasos, resto = divmod(transcurrido, granularidad)
    if resto:
        pasos += 1
    alineado = (medianoche + pasos * granularidad).astimezone(instante.tzinfo)
    return max(alineado, instante)


def calcular_slots(
    *,
    ahora: datetime,
    zona: str,
    horario_negocio: Sequence[ReglaHoraria],
    profesionales: Sequence[AgendaProfesional],
    servicios: Sequence[Servicio],
    desde: datetime,
    hasta: datetime,
    ajustes: AjustesAgenda | None = None,
    cierres: Sequence[Intervalo] = (),
) -> list[Slot]:
    """Devuelve los huecos ofrecibles en la ventana pedida.

    `servicios` en plural y en orden: una reserva encadenada (D13, RSV-2) necesita un **bloque
    continuo** para todos ellos, no tres huecos sueltos. Los buffers intermedios entre
    servicios del mismo profesional no se aplican; el cliente no se levanta de la silla.

    `cierres` son los tramos en los que el negocio entero no trabaja: festivos que aceptó
    (AGD-6) o un cierre puntual.
    """
    if not servicios:
        raise ValueError("hace falta al menos un servicio para calcular disponibilidad")

    ajustes = ajustes or AjustesAgenda()
    zona_negocio = ZoneInfo(zona)

    duracion = sum((s.duracion for s in servicios), timedelta(0))
    buffer_antes = servicios[0].buffer_antes
    buffer_despues = servicios[-1].buffer_despues

    # Ventana efectiva: la antelación mínima y la máxima recortan lo que se pidió (AGD-1).
    # Si el recorte deja la ventana del revés —pedir dentro de un año con máximo de 60 días—
    # no hay nada que ofrecer, y eso no es un error: es una respuesta vacía.
    inicio_ventana = max(desde, ahora + ajustes.antelacion_minima)
    fin_ventana = min(hasta, ahora + ajustes.antelacion_maxima)
    if fin_ventana <= inicio_ventana:
        return []
    ventana = Intervalo(inicio_ventana, fin_ventana)

    jornada_negocio = restar(
        materializar(horario_negocio, zona=zona_negocio, desde=ventana.inicio, hasta=ventana.fin),
        cierres,
    )
    if not jornada_negocio:
        return []

    slots: list[Slot] = []
    for profesional in profesionales:
        if not profesional.activo:
            continue

        jornada = intersecar(
            jornada_negocio,
            materializar(
                profesional.horario, zona=zona_negocio, desde=ventana.inicio, hasta=ventana.fin
            ),
        )
        # Las ausencias (vacaciones, día libre) recortan la jornada: durante ellas el
        # profesional no existe para la agenda. La ocupación se trata aparte, comprobando cada
        # candidato, porque ahí sí importan los buffers y una ausencia no los tiene.
        jornada = restar(jornada, profesional.ausencias)
        ocupacion = normalizar(profesional.ocupacion)

        for tramo in jornada:
            candidato = _alinear_a_rejilla(
                tramo.inicio, zona=zona_negocio, granularidad=ajustes.granularidad
            )
            while True:
                servicio = Intervalo(candidato, candidato + duracion)
                # El servicio y su buffer posterior tienen que caber en la jornada; el buffer
                # anterior, no (ver el docstring del módulo).
                if servicio.fin + buffer_despues > tramo.fin:
                    break

                bloqueado = Intervalo(candidato - buffer_antes, servicio.fin + buffer_despues)
                if not any(bloqueado.solapa(ocupado) for ocupado in ocupacion):
                    slots.append(
                        Slot(
                            inicio=servicio.inicio,
                            fin=servicio.fin,
                            profesional_id=profesional.profesional_id,
                        )
                    )

                candidato += ajustes.granularidad

    slots.sort(key=lambda s: (s.inicio, s.profesional_id or ""))
    return slots


def repartir_por_carga(slots: Sequence[Slot], carga: dict[str, int]) -> list[Slot]:
    """Para «cualquier profesional disponible» (STF-5): una hora, un profesional.

    Cuando varios profesionales pueden atender la misma hora, se ofrece una sola vez y se
    asigna al que **menos ocupación** tenga. Sin esto, el primero de la lista se lleva toda la
    agenda y los demás aparecen vacíos, que es justo lo contrario de lo que quiere un salón.
    """
    elegidos: dict[datetime, Slot] = {}
    for slot in slots:
        actual = elegidos.get(slot.inicio)
        if actual is None:
            elegidos[slot.inicio] = slot
            continue
        carga_actual = carga.get(actual.profesional_id or "", 0)
        carga_nueva = carga.get(slot.profesional_id or "", 0)
        # A igualdad de carga se desempata por identificador, para que el reparto sea
        # determinista y las pruebas no dependan del orden en que llegaron los profesionales.
        if (carga_nueva, slot.profesional_id or "") < (carga_actual, actual.profesional_id or ""):
            elegidos[slot.inicio] = slot
    return sorted(elegidos.values(), key=lambda s: s.inicio)
