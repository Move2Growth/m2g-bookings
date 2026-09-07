"""El portal del dueño (punto 6 del encargo).

Lo que distingue este portal del panel de un profesional **no es una tabla ni una pantalla: es
el rol de la membresía**, que ya existe (`dueno` frente a `profesional`) y ya viaja dentro del
token. Por eso aquí no hay ni una comprobación de «modo dueño»: hay `exigir_dueno` donde toca —
finanzas, anuncios y el interruptor del fichaje son suyos (STF-3)— y, debajo, las políticas
restrictivas de la migración 0006 haciendo el trabajo de verdad. Un endpoint nuevo que se
olvide del `exigir_dueno` sigue sin poder enseñarle a un profesional las finanzas del salón,
porque quien filtra es PostgreSQL.

Seis piezas y **dos tablas**: el resto son consultas sobre las citas que ya existen. Guardar
agregados de dinero habría sido más rápido de leer y habría empezado a mentir el primer día que
alguien cancela una cita a mano.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.api.comunes import url_de_media
from agenda.api.dependencias import SesionNegocio, exigir_dueno
from agenda.dominio.reservas import EstadoReserva
from agenda.errores import DatoInvalido, NoAutorizado
from agenda.modelos.clientes import BusinessClient
from agenda.modelos.equipo import StaffProfile
from agenda.modelos.negocio import Business
from agenda.modelos.reservas import Booking, BookingItem, StaffOccupancy
from agenda.servicios import anuncios as servicio_anuncios
from agenda.servicios import fichaje as servicio_fichaje
from agenda.servicios import finanzas as servicio_finanzas

router = APIRouter(prefix="/api/v1/negocio", tags=["portal del dueño"])

#: Lo máximo que se agrega de una vez. Un año cabe: es lo que hace falta para comparar
#: diciembre con diciembre, y más que eso no se mira desde un móvil.
VENTANA_MAXIMA_FINANZAS = timedelta(days=400)

#: Lo máximo que se pide de partes de fichaje. Dos meses: la quincena y la anterior.
VENTANA_MAXIMA_FICHAJE = timedelta(days=62)


# ── Todos los calendarios ─────────────────────────────────────────────────────────────────


class CitaEnColumna(BaseModel):
    """Una cita dentro de la columna de una persona."""

    id: uuid.UUID
    inicio: datetime
    fin: datetime
    estado: EstadoReserva
    cliente: str
    servicios: list[str]
    #: El importe **congelado en la cita**, no el precio de hoy del servicio.
    importe_centavos: int


class BloqueoEnColumna(BaseModel):
    """Un tramo en el que esa persona no está: almuerzo, vacaciones, el médico."""

    id: uuid.UUID
    inicio: datetime
    fin: datetime
    motivo: str | None


class ColumnaDelDia(BaseModel):
    """La agenda de una persona ese día. Una columna de la pantalla."""

    profesional_id: uuid.UUID
    nombre: str
    foto: str | None
    activo: bool
    citas: list[CitaEnColumna]
    bloqueos: list[BloqueoEnColumna]


class DiaEnColumnas(BaseModel):
    """El día entero del salón, persona a persona."""

    dia: date
    zona: str = Field(description="Zona horaria del negocio, para pintar la hora local")
    inicio: datetime
    fin: datetime
    columnas: list[ColumnaDelDia]


@router.get("/agenda/columnas", summary="Todos los calendarios del día, en columnas (AGD-2)")
async def agenda_en_columnas(
    sesion_negocio: SesionNegocio,
    dia: Annotated[
        date | None, Query(description="Día local del negocio; por defecto, hoy")
    ] = None,
    incluir_inactivos: Annotated[bool, Query()] = False,
) -> DiaEnColumnas:
    """El día de **todas** las personas del salón, una columna por persona.

    La agenda por rango ya existía (`GET /negocio/agenda`) y sirve para la lista; lo que
    faltaba para el portal del dueño es esta forma: el mismo día, varias personas en paralelo,
    que es como se mira un salón con seis sillas.

    El día se recorta **en hora local del negocio** y no en UTC. En Panamá son cinco horas de
    diferencia: pedir «el sábado» en UTC deja fuera las cinco últimas horas del sábado y mete
    dentro cinco del viernes, que es la clase de error que se descubre por una cita que
    desaparece.

    Un profesional que llame aquí ve **su columna y ninguna más**, y no porque este código lo
    filtre: aunque no lo hiciera, las políticas de la migración 0006 le devolverían columnas
    vacías. Se filtra igual para que la respuesta sea honesta y no una lista de huecos.
    """
    sesion, identidad = sesion_negocio
    negocio = await sesion.get(Business, identidad.negocio_id)
    zona = ZoneInfo(negocio.timezone if negocio else "America/Panama")

    dia = dia or datetime.now(zona).date()
    inicio = datetime.combine(dia, time(0, 0), tzinfo=zona)
    fin = inicio + timedelta(days=1)

    consulta = select(StaffProfile).where(
        StaffProfile.business_id == identidad.negocio_id,
        StaffProfile.deleted_at.is_(None),
    )
    if not incluir_inactivos:
        consulta = consulta.where(StaffProfile.active.is_(True))
    if identidad.staff_id is not None:
        consulta = consulta.where(StaffProfile.id == identidad.staff_id)

    equipo = list(
        (await sesion.execute(consulta.order_by(StaffProfile.position, StaffProfile.display_name)))
        .scalars()
        .all()
    )
    if not equipo:
        return DiaEnColumnas(dia=dia, zona=str(zona), inicio=inicio, fin=fin, columnas=[])

    ids = [p.id for p in equipo]
    citas = await _citas_del_dia(sesion, identidad.negocio_id, ids, inicio, fin)
    bloqueos = await _bloqueos_del_dia(sesion, identidad.negocio_id, ids, inicio, fin)

    return DiaEnColumnas(
        dia=dia,
        zona=str(zona),
        inicio=inicio,
        fin=fin,
        columnas=[
            ColumnaDelDia(
                profesional_id=persona.id,
                nombre=persona.display_name,
                foto=url_de_media(persona.photo_key),
                activo=persona.active,
                citas=citas.get(persona.id, []),
                bloqueos=bloqueos.get(persona.id, []),
            )
            for persona in equipo
        ],
    )


async def _citas_del_dia(
    sesion: AsyncSession,
    negocio_id: uuid.UUID,
    ids: list[uuid.UUID],
    inicio: datetime,
    fin: datetime,
) -> dict[uuid.UUID, list[CitaEnColumna]]:
    """Las citas del día, con su cliente y sus servicios, en **tres** consultas y no en 3·N."""
    filas = (
        (
            await sesion.execute(
                select(Booking)
                .where(
                    Booking.business_id == negocio_id,
                    Booking.staff_id.in_(ids),
                    Booking.starts_at < fin,
                    Booking.ends_at > inicio,
                )
                .order_by(Booking.starts_at)
            )
        )
        .scalars()
        .all()
    )
    if not filas:
        return {}

    reservas = [f.id for f in filas]
    nombres: dict[uuid.UUID, str] = dict(
        (
            await sesion.execute(
                select(BusinessClient.id, BusinessClient.display_name).where(
                    BusinessClient.business_id == negocio_id,
                    BusinessClient.id.in_([f.business_client_id for f in filas]),
                )
            )
        ).all()
    )
    servicios: dict[uuid.UUID, list[str]] = {}
    for booking_id, nombre in (
        await sesion.execute(
            select(BookingItem.booking_id, BookingItem.name_snapshot)
            .where(BookingItem.booking_id.in_(reservas))
            .order_by(BookingItem.position)
        )
    ).all():
        servicios.setdefault(booking_id, []).append(nombre)

    columnas: dict[uuid.UUID, list[CitaEnColumna]] = {}
    for fila in filas:
        columnas.setdefault(fila.staff_id, []).append(
            CitaEnColumna(
                id=fila.id,
                inicio=fila.starts_at,
                fin=fila.ends_at,
                estado=EstadoReserva(fila.status),
                # **Sin teléfono**: el listado de la agenda nunca lo lleva (garantía 3).
                cliente=nombres.get(fila.business_client_id, "Cliente"),
                servicios=servicios.get(fila.id, []),
                importe_centavos=fila.total_amount_minor,
            )
        )
    return columnas


async def _bloqueos_del_dia(
    sesion: AsyncSession,
    negocio_id: uuid.UUID,
    ids: list[uuid.UUID],
    inicio: datetime,
    fin: datetime,
) -> dict[uuid.UUID, list[BloqueoEnColumna]]:
    filas = (
        (
            await sesion.execute(
                select(StaffOccupancy)
                .where(
                    StaffOccupancy.business_id == negocio_id,
                    StaffOccupancy.staff_id.in_(ids),
                    StaffOccupancy.kind == "bloqueo",
                    StaffOccupancy.status == "activo",
                    StaffOccupancy.starts_at < fin,
                    StaffOccupancy.ends_at > inicio,
                )
                .order_by(StaffOccupancy.starts_at)
            )
        )
        .scalars()
        .all()
    )
    columnas: dict[uuid.UUID, list[BloqueoEnColumna]] = {}
    for fila in filas:
        columnas.setdefault(fila.staff_id, []).append(
            BloqueoEnColumna(
                id=fila.id, inicio=fila.starts_at, fin=fila.ends_at, motivo=fila.reason
            )
        )
    return columnas


# ── Finanzas ──────────────────────────────────────────────────────────────────────────────


class PeriodoDeCaja(BaseModel):
    inicio: datetime
    citas: int
    importe_centavos: int


class Caja(BaseModel):
    """Lo facturado, con la moneda y la zona para poder pintarlo sin recalcular nada."""

    desde: datetime
    hasta: datetime
    zona: str
    moneda: str
    agrupacion: str
    citas: int
    importe_centavos: int
    ticket_medio_centavos: int
    citas_sin_precio: int = Field(
        description=(
            "Citas con algún servicio «a consultar», que no tiene precio y suma cero. Sin este "
            "número el total parece completo y no lo es"
        )
    )
    periodos: list[PeriodoDeCaja]


@router.get("/finanzas", summary="El dinero que hace el salón (punto 6 del encargo)")
async def finanzas(
    sesion_negocio: SesionNegocio,
    desde: Annotated[datetime, Query()],
    hasta: Annotated[datetime, Query()],
    agrupacion: Annotated[str, Query(pattern="^(dia|semana|mes)$")] = "dia",
    profesional: Annotated[uuid.UUID | None, Query()] = None,
) -> Caja:
    """Lo facturado en el rango, por día, semana o mes.

    **Solo cuenta lo `completada`** —una cita confirmada es una promesa, no un ingreso— y usa
    **el importe que se guardó en la cita**, no el precio de hoy del servicio: subirle el precio
    al balayage no puede reescribir lo que se facturó en marzo.

    Las finanzas son del dueño (STF-3). El profesional no las ve, y no solo porque este
    endpoint lo compruebe: las tablas de dinero le están cerradas en la base.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)

    if hasta - desde > VENTANA_MAXIMA_FINANZAS:
        raise DatoInvalido("Ese periodo es demasiado largo. Pide como mucho un año de una vez.")

    negocio = await sesion.get(Business, identidad.negocio_id)
    resumen = await servicio_finanzas.resumen(
        sesion,
        negocio_id=identidad.negocio_id,
        zona=negocio.timezone if negocio else "America/Panama",
        moneda=negocio.currency if negocio else "USD",
        desde=desde,
        hasta=hasta,
        agrupacion=agrupacion,  # type: ignore[arg-type]
        profesional_id=profesional,
    )

    return Caja(
        desde=resumen.desde,
        hasta=resumen.hasta,
        zona=resumen.zona,
        moneda=resumen.moneda,
        agrupacion=resumen.agrupacion,
        citas=resumen.citas,
        importe_centavos=resumen.importe_centavos,
        ticket_medio_centavos=resumen.ticket_medio_centavos,
        citas_sin_precio=resumen.citas_sin_precio,
        periodos=[
            PeriodoDeCaja(inicio=p.inicio, citas=p.citas, importe_centavos=p.importe_centavos)
            for p in resumen.periodos
        ],
    )


class FilaDelMes(BaseModel):
    profesional_id: uuid.UUID
    nombre: str
    servicios: int
    importe_centavos: int


@router.get("/mejor-del-mes", summary="Quién facturó más o hizo más servicios")
async def mejor_del_mes(
    sesion_negocio: SesionNegocio,
    desde: Annotated[datetime | None, Query()] = None,
    hasta: Annotated[datetime | None, Query()] = None,
    criterio: Annotated[str, Query(pattern="^(importe|servicios)$")] = "importe",
    categoria: Annotated[
        str | None, Query(description="Slug de categoría de servicio, por ejemplo «barberia»")
    ] = None,
) -> list[FilaDelMes]:
    """El equipo ordenado por lo que pidió el encargo: **importe facturado** o **número de
    servicios**, y filtrable por categoría de servicio.

    Sin fechas, el mes natural en curso **en hora local del negocio**. Se devuelve la lista
    entera y no solo el primero: enseñar únicamente al ganador y esconder que el segundo se
    quedó a dos servicios convierte un dato en un concurso.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)

    negocio = await sesion.get(Business, identidad.negocio_id)
    zona = ZoneInfo(negocio.timezone if negocio else "America/Panama")
    if desde is None or hasta is None:
        hoy = datetime.now(zona)
        desde = desde or datetime.combine(hoy.date().replace(day=1), time(0, 0), tzinfo=zona)
        hasta = hasta or _mes_siguiente(desde)

    if hasta - desde > VENTANA_MAXIMA_FINANZAS:
        raise DatoInvalido("Ese periodo es demasiado largo. Pide como mucho un año de una vez.")

    filas = await servicio_finanzas.ranking_del_equipo(
        sesion,
        negocio_id=identidad.negocio_id,
        desde=desde,
        hasta=hasta,
        criterio=criterio,  # type: ignore[arg-type]
        categoria=categoria,
    )
    return [
        FilaDelMes(
            profesional_id=f.profesional_id,
            nombre=f.nombre,
            servicios=f.servicios,
            importe_centavos=f.importe_centavos,
        )
        for f in filas
    ]


def _mes_siguiente(momento: datetime) -> datetime:
    """El día 1 del mes siguiente, en la misma zona. Diciembre pasa a enero del año que viene."""
    if momento.month == 12:
        return momento.replace(year=momento.year + 1, month=1, day=1)
    return momento.replace(month=momento.month + 1, day=1)


# ── Publicidad flash ──────────────────────────────────────────────────────────────────────


class AnuncioDelSalon(BaseModel):
    id: uuid.UUID
    texto: str
    activo: bool
    desde: datetime
    hasta: datetime | None
    vigente: bool = Field(description="Si ahora mismo se está enseñando en la ficha pública")


class NuevoAnuncio(BaseModel):
    texto: str = Field(min_length=1, max_length=280)
    desde: datetime | None = Field(default=None, description="Por defecto, ya")
    hasta: datetime | None = Field(default=None, description="Nulo = sin fecha de fin")
    activo: bool = True


class CambioDeAnuncio(BaseModel):
    texto: str | None = Field(default=None, min_length=1, max_length=280)
    desde: datetime | None = None
    hasta: datetime | None = None
    activo: bool | None = None
    quitar_fin: bool = Field(
        default=False, description="Deja el anuncio sin fecha de fin; «hasta» se ignora"
    )


@router.get("/anuncios", summary="La publicidad flash del salón (punto 6 del encargo)")
async def listar_anuncios(sesion_negocio: SesionNegocio) -> list[AnuncioDelSalon]:
    sesion, identidad = sesion_negocio
    return [
        _pintar_anuncio(a)
        for a in await servicio_anuncios.listar(sesion, negocio_id=identidad.negocio_id)
    ]


@router.post("/anuncios", status_code=201, summary="Escribir un anuncio para la propia ficha")
async def crear_anuncio(alta: NuevoAnuncio, sesion_negocio: SesionNegocio) -> AnuncioDelSalon:
    """Un texto del salón, con vigencia, que sale en **su** ficha pública.

    **No es publicidad del marketplace.** El posicionamiento pagado es otra cosa, se cobra y
    vive en `ad_campaigns`; esto es gratis, no compite con nadie y no toca el ranking.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    return _pintar_anuncio(
        await servicio_anuncios.crear(
            sesion,
            negocio_id=identidad.negocio_id,
            texto=alta.texto,
            desde=alta.desde,
            hasta=alta.hasta,
            activo=alta.activo,
        )
    )


@router.patch("/anuncios/{anuncio_id}", summary="Cambiar el anuncio o sus fechas")
async def editar_anuncio(
    anuncio_id: uuid.UUID, cambio: CambioDeAnuncio, sesion_negocio: SesionNegocio
) -> AnuncioDelSalon:
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    return _pintar_anuncio(
        await servicio_anuncios.editar(
            sesion,
            negocio_id=identidad.negocio_id,
            anuncio_id=anuncio_id,
            texto=cambio.texto,
            desde=cambio.desde,
            hasta=cambio.hasta,
            activo=cambio.activo,
            quitar_fin=cambio.quitar_fin,
        )
    )


@router.delete("/anuncios/{anuncio_id}", summary="Retirar el anuncio de la ficha")
async def retirar_anuncio(anuncio_id: uuid.UUID, sesion_negocio: SesionNegocio) -> AnuncioDelSalon:
    """Lo apaga **sin borrar la fila**: el salón puede querer volver a lanzarlo en diciembre."""
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    return _pintar_anuncio(
        await servicio_anuncios.retirar(
            sesion, negocio_id=identidad.negocio_id, anuncio_id=anuncio_id
        )
    )


def _pintar_anuncio(anuncio: servicio_anuncios.Anuncio) -> AnuncioDelSalon:
    return AnuncioDelSalon(
        id=anuncio.id,
        texto=anuncio.texto,
        activo=anuncio.activo,
        desde=anuncio.desde,
        hasta=anuncio.hasta,
        vigente=anuncio.vigente,
    )


# ── Fichaje ───────────────────────────────────────────────────────────────────────────────


class InterruptorDeFichaje(BaseModel):
    activo: bool


class FichajeDeUnaPersona(BaseModel):
    profesional_id: uuid.UUID
    fichaje_activo: bool


class MarcaDeFichaje(BaseModel):
    id: uuid.UUID
    profesional_id: uuid.UUID
    clase: str = Field(description="entrada | salida")
    instante: datetime
    origen: str = Field(description="profesional | dueno")
    nota: str | None


class ParteDeFichaje(BaseModel):
    profesional_id: uuid.UUID
    nombre: str
    fichaje_activo: bool
    minutos_trabajados: int
    jornada_abierta: bool
    marcas: list[MarcaDeFichaje]


class NuevaMarca(BaseModel):
    clase: str = Field(pattern="^(entrada|salida)$")
    profesional_id: uuid.UUID | None = Field(
        default=None,
        description="Solo lo manda el dueño para fichar por otra persona; el profesional, no",
    )
    nota: str | None = Field(default=None, max_length=200)


@router.put(
    "/profesionales/{profesional_id}/fichaje",
    summary="Encender o apagar el fichaje de una persona (punto 6 del encargo)",
)
async def cambiar_fichaje(
    profesional_id: uuid.UUID,
    interruptor: InterruptorDeFichaje,
    sesion_negocio: SesionNegocio,
) -> FichajeDeUnaPersona:
    """**Persona a persona, y apagado por defecto.**

    No hay un interruptor para todo el salón a la vez, y es la parte del encargo que más se
    presta a construirse mal: un fichaje que se enciende para todos porque alguien lo quería
    para uno se lee como vigilancia. Apagarlo **no borra** lo ya fichado: el parte de las
    semanas anteriores sigue siendo cierto.
    """
    sesion, identidad = sesion_negocio
    exigir_dueno(identidad)
    perfil = await servicio_fichaje.encender(
        sesion,
        negocio_id=identidad.negocio_id,
        profesional_id=profesional_id,
        activo=interruptor.activo,
    )
    return FichajeDeUnaPersona(profesional_id=perfil.id, fichaje_activo=perfil.clock_in_enabled)


@router.post("/fichajes", status_code=201, summary="Fichar entrada o salida")
async def fichar(marca: NuevaMarca, sesion_negocio: SesionNegocio) -> MarcaDeFichaje:
    """Cada quien ficha lo suyo; el dueño puede ficharlo desde el mostrador.

    Un profesional **no puede fichar por otro**, y no es este `if` lo que lo impide: la política
    restrictiva de la migración 0010 acota sus filas a las suyas, así que una fila con el
    identificador de otra persona no entra aunque el endpoint se despiste.
    """
    sesion, identidad = sesion_negocio

    if identidad.es_dueno:
        profesional_id = marca.profesional_id
        if profesional_id is None:
            raise DatoInvalido("Di de quién es el fichaje.")
        origen = "dueno"
    else:
        if marca.profesional_id not in (None, identidad.staff_id):
            raise NoAutorizado("Solo puedes fichar lo tuyo.")
        profesional_id = identidad.staff_id
        origen = "profesional"

    if profesional_id is None:
        raise DatoInvalido("Tu cuenta no tiene ficha de profesional en este negocio.")

    guardada = await servicio_fichaje.fichar(
        sesion,
        negocio_id=identidad.negocio_id,
        profesional_id=profesional_id,
        clase=marca.clase,
        actor_user_id=identidad.usuario_id,
        origen=origen,
        nota=marca.nota,
    )
    return MarcaDeFichaje(
        id=guardada.id,
        profesional_id=guardada.profesional_id,
        clase=guardada.clase,
        instante=guardada.instante,
        origen=guardada.origen,
        nota=guardada.nota,
    )


@router.get("/fichajes", summary="El parte de entradas y salidas")
async def partes_de_fichaje(
    sesion_negocio: SesionNegocio,
    desde: Annotated[datetime | None, Query()] = None,
    hasta: Annotated[datetime | None, Query()] = None,
    profesional: Annotated[uuid.UUID | None, Query()] = None,
) -> list[ParteDeFichaje]:
    """Los partes del rango. Por defecto, los últimos siete días.

    El dueño ve el equipo entero; un profesional ve **el suyo**, y quien lo acota es la base.
    """
    sesion, identidad = sesion_negocio

    hasta = hasta or datetime.now(UTC)
    desde = desde or hasta - timedelta(days=7)
    if hasta - desde > VENTANA_MAXIMA_FICHAJE:
        raise DatoInvalido("Ese periodo es demasiado largo. Pide como mucho dos meses.")

    if identidad.staff_id is not None:
        profesional = identidad.staff_id

    partes = await servicio_fichaje.partes(
        sesion,
        negocio_id=identidad.negocio_id,
        desde=desde,
        hasta=hasta,
        profesional_id=profesional,
    )
    return [
        ParteDeFichaje(
            profesional_id=p.profesional_id,
            nombre=p.nombre,
            fichaje_activo=p.fichaje_activo,
            minutos_trabajados=p.minutos_trabajados,
            jornada_abierta=p.jornada_abierta,
            marcas=[
                MarcaDeFichaje(
                    id=m.id,
                    profesional_id=m.profesional_id,
                    clase=m.clase,
                    instante=m.instante,
                    origen=m.origen,
                    nota=m.nota,
                )
                for m in p.marcas
            ],
        )
        for p in partes
    ]
