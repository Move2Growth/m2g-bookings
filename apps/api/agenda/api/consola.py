"""La consola interna de M2G: el back-office (ADM-1 a ADM-6).

**No cuelga del router público ni comparte nada con él.** Prefijo propio (`/api/v1/consola`),
tabla de cuentas propia, sesión propia con segundo factor obligatorio y **rol de base de datos
propio** (`agenda_admin`). Esa separación es la que hace que un fallo de autorización en un
endpoint de cliente no pueda acabar teniendo los permisos del equipo interno: no hay ningún
camino que suba de una superficie a la otra, porque la conexión a la base ya es otra.

Lo que se puede hacer desde aquí sale del brief y no se amplía por comodidad:

* **ADM-1** métricas: negocios, reservas por día, impresiones y clics.
* **ADM-2** negocios: buscar, ver y **suspender** o reactivar. *Impersonar es v2 y no está: sin
  caducidad corta, aviso al negocio y auditoría de las tres cosas, no se construye (ADR-0006).*
* **ADM-3** moderación de reseñas: la cola de reportes y ocultar o mantener.
* **ADM-4** configuración sin desplegar: pesos del ranking y planes.
* **ADM-6** auditoría y exportaciones CSV.

Todo lo que cambia algo deja fila en `audit_logs`. Ahí no hay excepciones: **una de las
funciones de la auditoría es registrar lo que hace el equipo interno**, y por eso la tabla ni
siquiera es accesible desde el rol de la aplicación.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Header, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.api.dependencias import SesionConsola, SesionConsolaAnonima
from agenda.errores import DatoInvalido, NoExiste
from agenda.modelos.clientes import BusinessClient
from agenda.modelos.interno import AuditLog
from agenda.modelos.marketplace import ListingClickDaily, ListingImpressionDaily, RankingWeights
from agenda.modelos.monetizacion import Plan
from agenda.modelos.negocio import Business, Location
from agenda.modelos.reservas import Booking
from agenda.modelos.reviews import BusinessRatingStats, Review, ReviewReport
from agenda.servicios import consola as servicio_consola
from agenda.servicios import resenas as servicio_resenas

router = APIRouter(prefix="/api/v1/consola", tags=["consola interna"])

#: Cuántos negocios se sirven por página en la consola. Más alto que en el marketplace: aquí
#: se trabaja en un escritorio y lo que se hace es barrer una lista, no elegir un salón.
POR_PAGINA = 50

#: Cuántos días de serie devuelve el panel por defecto.
DIAS_DE_SERIE = 30

#: Techo de filas de una exportación. Sin él, un CSV de un año de reservas se come la memoria
#: del proceso que además está atendiendo a los salones.
MAXIMO_EXPORTACION = 50_000


class Entrada(BaseModel):
    email: str
    password: str
    codigo_2fa: str = Field(min_length=6, max_length=8, description="Seis dígitos del autenticador")


class SesionAbierta(BaseModel):
    acceso: str
    refresco: str
    expira_en_segundos: int
    admin_id: uuid.UUID
    rol: str
    nombre: str


class PeticionRefresco(BaseModel):
    refresco: str


class NegocioEnConsola(BaseModel):
    id: uuid.UUID
    slug: str
    nombre: str
    estado: str
    zona_horaria: str
    direccion: str | None
    creado: datetime
    publicado: datetime | None
    suspendido: datetime | None
    motivo_suspension: str | None
    reservas: int
    clientes: int
    reviews: int
    rating: float | None


class Suspension(BaseModel):
    motivo: str = Field(min_length=4, max_length=300)


class ReporteEnCola(BaseModel):
    """Una reseña reportada esperando decisión (ADM-3)."""

    reporte_id: uuid.UUID
    resena_id: uuid.UUID
    negocio: str
    negocio_slug: str
    nota: int
    texto: str | None
    motivo: str
    reportado_por: str
    estado_resena: str
    estado_reporte: str
    fecha: datetime


class DecisionDeModeracion(BaseModel):
    accion: str = Field(
        pattern="^(ocultar|mantener)$",
        description="«ocultar» retira la reseña del perfil; «mantener» descarta el reporte",
    )
    nota: str | None = Field(default=None, max_length=500)


class PesosDelRanking(BaseModel):
    """Los pesos vigentes (ADM-4, ADR-0009). **Ni uno de estos números vive en el código.**"""

    version: int
    vigente_desde: datetime
    distancia: float
    rating: float
    reservas_recientes: float
    tasa_completado: float
    completitud: float
    actividad: float
    boost_nuevo: float
    radio_km: float
    decaimiento_km: float
    dias_recientes: int
    techo_reservas: int
    dias_actividad: int
    dias_boost: int
    bayes_m: float = Field(description="Media global sembrada de la ponderación bayesiana")
    bayes_c: int = Field(description="Reviews de confianza de la ponderación bayesiana")
    patrocinados_por_pagina: int
    tamano_pagina: int
    notas: str | None


class NuevosPesos(BaseModel):
    """Lo que se puede cambiar. Todo opcional: lo que no venga se hereda de la versión vigente."""

    distancia: float | None = Field(default=None, ge=0, le=1)
    rating: float | None = Field(default=None, ge=0, le=1)
    reservas_recientes: float | None = Field(default=None, ge=0, le=1)
    tasa_completado: float | None = Field(default=None, ge=0, le=1)
    completitud: float | None = Field(default=None, ge=0, le=1)
    actividad: float | None = Field(default=None, ge=0, le=1)
    boost_nuevo: float | None = Field(default=None, ge=0, le=1)
    radio_km: float | None = Field(default=None, gt=0, le=200)
    decaimiento_km: float | None = Field(default=None, gt=0, le=200)
    dias_recientes: int | None = Field(default=None, ge=1, le=365)
    techo_reservas: int | None = Field(default=None, ge=1)
    dias_actividad: int | None = Field(default=None, ge=1, le=365)
    dias_boost: int | None = Field(default=None, ge=0, le=365)
    bayes_m: float | None = Field(default=None, ge=0, le=5)
    bayes_c: int | None = Field(default=None, ge=0, le=1000)
    patrocinados_por_pagina: int | None = Field(default=None, ge=0, le=5)
    tamano_pagina: int | None = Field(default=None, ge=1, le=50)
    notas: str | None = Field(default=None, max_length=500)


class PlanEnConsola(BaseModel):
    id: uuid.UUID
    codigo: str
    version: int
    nombre: str
    precio_centavos: int
    moneda: str
    periodo: str
    dias_prueba: int
    limites: dict[str, Any]
    caracteristicas: dict[str, Any]
    vigente_desde: datetime
    vigente_hasta: datetime | None
    activo: bool


class NuevoPlan(BaseModel):
    """Cambiar el precio de un plan **no es un `UPDATE`**: es una versión nueva (ADR-0010)."""

    codigo: str = Field(min_length=2, max_length=40)
    nombre: str = Field(min_length=2, max_length=80)
    precio_centavos: int = Field(ge=0)
    periodo: str = Field(default="mensual", pattern="^(mensual|anual)$")
    dias_prueba: int = Field(default=0, ge=0, le=365)
    limites: dict[str, Any] = Field(default_factory=dict)
    caracteristicas: dict[str, Any] = Field(default_factory=dict)


class PuntoDeSerie(BaseModel):
    dia: date
    valor: int


class Metricas(BaseModel):
    """Lo mínimo con lo que se dirige esto (ADM-1). Nada que no se pueda explicar."""

    negocios_totales: int
    negocios_publicados: int
    negocios_suspendidos: int
    reservas_por_dia: list[PuntoDeSerie]
    impresiones_por_dia: list[PuntoDeSerie]
    clics_por_dia: list[PuntoDeSerie]
    reportes_abiertos: int


# ── Entrar ────────────────────────────────────────────────────────────────────────────────


@router.post("/entrar", summary="Entrar en la consola con 2FA (ADM-5, ADR-0006)")
async def entrar(entrada: Entrada, sesion: SesionConsolaAnonima) -> SesionAbierta:
    """Correo, contraseña y segundo factor. **Login separado del de clientes.**

    Es la única ruta de la consola que abre conexión sin identidad, porque quien pide entrar
    todavía no la tiene. Aun así usa el rol del back-office y no el de la aplicación: las
    tablas `admin_users` y `admin_sessions` **solo tienen permiso concedido a `agenda_admin`**,
    de modo que un token de cliente no sirve de nada aquí ni aunque llegue.
    """
    credenciales = await servicio_consola.entrar(
        sesion,
        email=entrada.email,
        password=entrada.password,
        codigo_2fa=entrada.codigo_2fa,
    )
    return SesionAbierta(**credenciales.__dict__)


@router.post("/refrescar", summary="Rotar el refresco de la consola")
async def refrescar(peticion: PeticionRefresco, sesion: SesionConsolaAnonima) -> SesionAbierta:
    credenciales = await servicio_consola.refrescar(sesion, refresco=peticion.refresco)
    return SesionAbierta(**credenciales.__dict__)


@router.post("/salir", status_code=204, summary="Cerrar la sesión de consola")
async def salir(peticion: PeticionRefresco, sesion: SesionConsolaAnonima) -> None:
    await servicio_consola.salir(sesion, refresco=peticion.refresco)


# ── Negocios (ADM-2) ──────────────────────────────────────────────────────────────────────


@router.get("/negocios", summary="Buscar negocios (ADM-2)")
async def listar_negocios(
    sesion_consola: SesionConsola,
    buscar: Annotated[str | None, Query(description="Parte del nombre o del slug")] = None,
    estado: Annotated[str | None, Query(pattern="^(borrador|publicado|suspendido)$")] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
) -> list[NegocioEnConsola]:
    """Todos los negocios de la plataforma, que es justo lo que la API del salón no puede ver.

    La diferencia no está en un permiso del código: está en el **rol de la conexión**. Con
    `agenda_api` esta misma consulta devolvería, como mucho, un negocio.
    """
    sesion, _ = sesion_consola

    consulta = select(Business).where(Business.deleted_at.is_(None))
    if buscar:
        patron = f"%{buscar.strip()}%"
        consulta = consulta.where(
            or_(Business.display_name.ilike(patron), Business.slug.ilike(patron))
        )
    if estado:
        consulta = consulta.where(Business.status == estado)

    negocios = list(
        (
            await sesion.execute(
                consulta.order_by(Business.created_at.desc())
                .offset((pagina - 1) * POR_PAGINA)
                .limit(POR_PAGINA)
            )
        )
        .scalars()
        .all()
    )
    return await _pintar_negocios(sesion, negocios)


@router.get("/negocios/{negocio_id}", summary="Ver un negocio (ADM-2)")
async def ver_negocio(negocio_id: uuid.UUID, sesion_consola: SesionConsola) -> NegocioEnConsola:
    sesion, _ = sesion_consola
    negocio = await sesion.get(Business, negocio_id)
    if negocio is None:
        raise NoExiste("Ese negocio no existe.")
    return (await _pintar_negocios(sesion, [negocio]))[0]


@router.post("/negocios/{negocio_id}/suspender", summary="Suspender un negocio (ADM-2, ONB-6)")
async def suspender(
    negocio_id: uuid.UUID,
    suspension: Suspension,
    sesion_consola: SesionConsola,
    user_agent: Annotated[str | None, Header()] = None,
) -> NegocioEnConsola:
    """Lo saca del marketplace. **No borra datos ni cancela citas.**

    Es un cambio de estado y solo eso (ADR-0010): el salón deja de aparecer y de recibir
    reservas nuevas, pero su agenda, sus clientes y sus citas siguen intactos, porque
    regularizar y volver tiene que ser inmediato. Suspender no puede parecerse a borrar.

    El motivo es obligatorio y se guarda: una suspensión que nadie sabe explicar es una llamada
    de teléfono muy larga.
    """
    sesion, identidad = sesion_consola
    negocio = await sesion.get(Business, negocio_id)
    if negocio is None:
        raise NoExiste("Ese negocio no existe.")
    if negocio.status == "suspendido":
        raise DatoInvalido("Ese negocio ya está suspendido.")

    antes = {"status": negocio.status}
    negocio.status = "suspendido"
    negocio.suspended_at = datetime.now(UTC)
    negocio.suspension_reason = suspension.motivo

    await _auditar(
        sesion,
        identidad,
        accion="negocio.suspender",
        entidad="business",
        entidad_id=negocio.id,
        negocio_id=negocio.id,
        antes=antes,
        despues={"status": "suspendido", "motivo": suspension.motivo},
        agente=user_agent,
    )
    await sesion.flush()
    return (await _pintar_negocios(sesion, [negocio]))[0]


@router.post("/negocios/{negocio_id}/reactivar", summary="Levantar la suspensión (ADM-2)")
async def reactivar(
    negocio_id: uuid.UUID,
    sesion_consola: SesionConsola,
    user_agent: Annotated[str | None, Header()] = None,
) -> NegocioEnConsola:
    """Vuelve a `publicado` si ya lo estaba, o a `borrador` si nunca llegó a publicarse.

    Lo segundo importa: reactivar no puede publicar un negocio que no cumplía el mínimo de
    D11, porque entonces la consola sería una puerta trasera para saltarse el checklist.
    """
    sesion, identidad = sesion_consola
    negocio = await sesion.get(Business, negocio_id)
    if negocio is None:
        raise NoExiste("Ese negocio no existe.")
    if negocio.status != "suspendido":
        raise DatoInvalido("Ese negocio no está suspendido.")

    negocio.status = "publicado" if negocio.published_at is not None else "borrador"
    negocio.suspended_at = None
    negocio.suspension_reason = None

    await _auditar(
        sesion,
        identidad,
        accion="negocio.reactivar",
        entidad="business",
        entidad_id=negocio.id,
        negocio_id=negocio.id,
        antes={"status": "suspendido"},
        despues={"status": negocio.status},
        agente=user_agent,
    )
    await sesion.flush()
    return (await _pintar_negocios(sesion, [negocio]))[0]


# ── Moderación (ADM-3, REV-4) ─────────────────────────────────────────────────────────────


@router.get("/moderacion/resenas", summary="Cola de reseñas reportadas (ADM-3, REV-4)")
async def cola_de_moderacion(
    sesion_consola: SesionConsola,
    abiertos: Annotated[bool, Query(description="Solo lo que sigue sin decidir")] = True,
    pagina: Annotated[int, Query(ge=1)] = 1,
) -> list[ReporteEnCola]:
    """Los reportes pendientes, con la reseña delante para poder decidir sin salir de aquí."""
    sesion, _ = sesion_consola

    consulta = (
        select(ReviewReport, Review, Business)
        .join(Review, Review.id == ReviewReport.review_id)
        .join(Business, Business.id == Review.business_id)
        .order_by(ReviewReport.created_at)
        .offset((pagina - 1) * POR_PAGINA)
        .limit(POR_PAGINA)
    )
    if abiertos:
        consulta = consulta.where(ReviewReport.status.in_(("abierto", "en_revision")))

    return [
        ReporteEnCola(
            reporte_id=reporte.id,
            resena_id=resena.id,
            negocio=negocio.display_name,
            negocio_slug=negocio.slug,
            nota=resena.rating,
            texto=resena.body,
            motivo=reporte.reason,
            reportado_por=reporte.reporter_kind,
            estado_resena=resena.status,
            estado_reporte=reporte.status,
            fecha=reporte.created_at,
        )
        for reporte, resena, negocio in (await sesion.execute(consulta)).all()
    ]


@router.post("/moderacion/resenas/{reporte_id}", summary="Resolver un reporte (ADM-3, REV-4)")
async def resolver_reporte(
    reporte_id: uuid.UUID,
    decision: DecisionDeModeracion,
    sesion_consola: SesionConsola,
    user_agent: Annotated[str | None, Header()] = None,
) -> ReporteEnCola:
    """Ocultar la reseña o descartar el reporte. **Ocultar recalcula el rating del negocio.**

    Es lo que hace que ocultar signifique algo: si la reseña desapareciera del perfil pero
    siguiera pesando en la media, el número que ve todo el mundo mentiría sin que nada fallara.
    """
    sesion, identidad = sesion_consola

    reporte = await sesion.get(ReviewReport, reporte_id)
    if reporte is None:
        raise NoExiste("Ese reporte no existe.")
    resena = await sesion.get(Review, reporte.review_id)
    if resena is None:
        raise NoExiste("Esa reseña ya no existe.")

    antes = {"resena": resena.status, "reporte": reporte.status}
    ahora = datetime.now(UTC)

    if decision.accion == "ocultar":
        resena.status = "oculta"
        resena.hidden_reason = decision.nota or reporte.reason
        resena.hidden_by_admin_id = identidad.admin_id
        reporte.status = "resuelto"
    else:
        reporte.status = "descartado"

    reporte.resolved_by_admin_id = identidad.admin_id
    reporte.resolution_note = decision.nota
    await sesion.flush()

    # El agregado se rehace **siempre**, también al mantener: si el reporte anterior la había
    # ocultado y ahora se mantiene, hay que devolverla a la media.
    await servicio_resenas.recalcular_agregado(sesion, resena.business_id, ahora=ahora)

    await _auditar(
        sesion,
        identidad,
        accion=f"resena.{decision.accion}",
        entidad="review",
        entidad_id=resena.id,
        negocio_id=resena.business_id,
        antes=antes,
        despues={"resena": resena.status, "reporte": reporte.status},
        agente=user_agent,
    )

    negocio = await sesion.get(Business, resena.business_id)
    return ReporteEnCola(
        reporte_id=reporte.id,
        resena_id=resena.id,
        negocio=negocio.display_name if negocio else "",
        negocio_slug=negocio.slug if negocio else "",
        nota=resena.rating,
        texto=resena.body,
        motivo=reporte.reason,
        reportado_por=reporte.reporter_kind,
        estado_resena=resena.status,
        estado_reporte=reporte.status,
        fecha=reporte.created_at,
    )


# ── Configuración sin desplegar (ADM-4) ───────────────────────────────────────────────────


@router.get("/ranking", summary="Pesos vigentes del ranking (ADM-4, ADR-0009)")
async def ver_pesos(sesion_consola: SesionConsola) -> PesosDelRanking:
    sesion, _ = sesion_consola
    fila = await _pesos_vigentes(sesion)
    return _pintar_pesos(fila)


@router.put("/ranking", summary="Cambiar los pesos sin desplegar (ADM-4, ADR-0009)")
async def cambiar_pesos(
    nuevos: NuevosPesos,
    sesion_consola: SesionConsola,
    user_agent: Annotated[str | None, Header()] = None,
) -> PesosDelRanking:
    """**Inserta una versión nueva y cierra la anterior.** No es un `UPDATE`, y da igual que lo
    parezca.

    Hay que poder responder a «¿con qué pesos salía este negocio el noveno la semana pasada?»,
    y un `UPDATE` borra esa respuesta para siempre. Además, el índice único de la migración
    garantiza que hay **exactamente una** versión vigente: si dos peticiones intentaran cerrar
    y abrir a la vez, una de las dos falla en vez de dejar dos verdades.
    """
    sesion, identidad = sesion_consola
    vigente = await _pesos_vigentes(sesion)
    ahora = datetime.now(UTC)

    def valor(campo: str, columna: str):
        enviado = getattr(nuevos, campo)
        return enviado if enviado is not None else getattr(vigente, columna)

    vigente.effective_to = ahora
    fila = RankingWeights(
        version=vigente.version + 1,
        effective_from=ahora,
        w_distancia=Decimal(str(valor("distancia", "w_distancia"))),
        w_rating=Decimal(str(valor("rating", "w_rating"))),
        w_reservas_recientes=Decimal(str(valor("reservas_recientes", "w_reservas_recientes"))),
        w_tasa_completado=Decimal(str(valor("tasa_completado", "w_tasa_completado"))),
        w_completitud=Decimal(str(valor("completitud", "w_completitud"))),
        w_actividad=Decimal(str(valor("actividad", "w_actividad"))),
        w_boost_nuevo=Decimal(str(valor("boost_nuevo", "w_boost_nuevo"))),
        radius_km=Decimal(str(valor("radio_km", "radius_km"))),
        decay_km=Decimal(str(valor("decaimiento_km", "decay_km"))),
        recent_days=int(valor("dias_recientes", "recent_days")),
        recent_cap=int(valor("techo_reservas", "recent_cap")),
        activity_days=int(valor("dias_actividad", "activity_days")),
        boost_days=int(valor("dias_boost", "boost_days")),
        bayes_m=Decimal(str(valor("bayes_m", "bayes_m"))),
        bayes_c=int(valor("bayes_c", "bayes_c")),
        sponsored_per_page=int(valor("patrocinados_por_pagina", "sponsored_per_page")),
        page_size=int(valor("tamano_pagina", "page_size")),
        notes=nuevos.notas,
        created_by_admin_id=identidad.admin_id,
    )
    sesion.add(fila)
    await sesion.flush()

    await _auditar(
        sesion,
        identidad,
        accion="ranking.pesos",
        entidad="ranking_weights",
        entidad_id=fila.id,
        antes={"version": vigente.version},
        despues={"version": fila.version},
        agente=user_agent,
    )
    return _pintar_pesos(fila)


@router.get("/planes", summary="Planes y precios (ADM-4, ADR-0010)")
async def listar_planes(sesion_consola: SesionConsola) -> list[PlanEnConsola]:
    sesion, _ = sesion_consola
    filas = (
        (await sesion.execute(select(Plan).order_by(Plan.code, Plan.version.desc())))
        .scalars()
        .all()
    )
    return [_pintar_plan(f) for f in filas]


@router.post("/planes", status_code=201, summary="Publicar una versión de plan (ADM-4)")
async def crear_plan(
    nuevo: NuevoPlan,
    sesion_consola: SesionConsola,
    user_agent: Annotated[str | None, Header()] = None,
) -> PlanEnConsola:
    """Cambiar el precio de un plan es **crear una versión**, no editar la que hay (ADR-0010).

    Hay que poder decir qué precio tenía cada negocio en cada momento —eso es lo que sostiene
    el *grandfathering*, que las suscripciones apuntan a una versión concreta— y un `UPDATE`
    reescribiría el pasado de todas ellas a la vez.
    """
    sesion, identidad = sesion_consola
    ahora = datetime.now(UTC)

    anterior = (
        await sesion.execute(
            select(Plan)
            .where(Plan.code == nuevo.codigo, Plan.effective_to.is_(None))
            .order_by(Plan.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if anterior is not None:
        anterior.effective_to = ahora

    fila = Plan(
        code=nuevo.codigo,
        version=(anterior.version + 1) if anterior else 1,
        name=nuevo.nombre,
        price_minor=nuevo.precio_centavos,
        period=nuevo.periodo,
        trial_days=nuevo.dias_prueba,
        limits=nuevo.limites,
        features=nuevo.caracteristicas,
        effective_from=ahora,
        created_by_admin_id=identidad.admin_id,
    )
    sesion.add(fila)
    await sesion.flush()

    await _auditar(
        sesion,
        identidad,
        accion="plan.version",
        entidad="plan",
        entidad_id=fila.id,
        antes={"version": anterior.version, "precio": anterior.price_minor} if anterior else None,
        despues={"version": fila.version, "precio": fila.price_minor},
        agente=user_agent,
    )
    return _pintar_plan(fila)


# ── Métricas y exportación (ADM-1, ADM-6) ─────────────────────────────────────────────────


@router.get("/metricas", summary="Panel de la plataforma (ADM-1)")
async def metricas(
    sesion_consola: SesionConsola,
    dias: Annotated[int, Query(ge=1, le=365)] = DIAS_DE_SERIE,
) -> Metricas:
    """Lo básico y explicable: cuántos negocios hay, qué se reserva y qué se mira.

    Las impresiones y los clics salen **ya agregados por día** (MKT-8): son las tablas de
    contadores, no un recuento de eventos. Se puede pintar la serie de un año sin recorrer
    millones de filas.
    """
    sesion, _ = sesion_consola
    desde = datetime.now(UTC).date() - timedelta(days=dias)

    por_estado = dict(
        (
            await sesion.execute(
                select(Business.status, func.count())
                .where(Business.deleted_at.is_(None))
                .group_by(Business.status)
            )
        ).all()
    )

    reservas = [
        PuntoDeSerie(dia=dia, valor=total)
        for dia, total in (
            await sesion.execute(
                select(func.date(Booking.created_at), func.count())
                .where(func.date(Booking.created_at) >= desde)
                .group_by(func.date(Booking.created_at))
                .order_by(func.date(Booking.created_at))
            )
        ).all()
    ]

    reportes = (
        await sesion.execute(
            select(func.count())
            .select_from(ReviewReport)
            .where(ReviewReport.status.in_(("abierto", "en_revision")))
        )
    ).scalar_one()

    return Metricas(
        negocios_totales=sum(por_estado.values()),
        negocios_publicados=por_estado.get("publicado", 0),
        negocios_suspendidos=por_estado.get("suspendido", 0),
        reservas_por_dia=reservas,
        impresiones_por_dia=await _serie_diaria(sesion, ListingImpressionDaily, desde),
        clics_por_dia=await _serie_diaria(sesion, ListingClickDaily, desde),
        reportes_abiertos=reportes,
    )


@router.get("/exportar/{que}", summary="Exportación CSV (ADM-6)")
async def exportar(
    que: str,
    sesion_consola: SesionConsola,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
) -> StreamingResponse:
    """CSV de negocios o de reservas. **Sin teléfonos ni nombres de clientes.**

    Una exportación es la forma más fácil de sacar datos personales de un sistema sin que nadie
    se entere, así que aquí salen identificadores y agregados: quién reservó no se exporta. Si
    algún día hace falta, será con su base legal escrita, no como efecto colateral de un botón.
    """
    sesion, identidad = sesion_consola

    hoy = datetime.now(UTC).date()
    desde = desde or hoy - timedelta(days=DIAS_DE_SERIE)
    hasta = hasta or hoy

    match que:
        case "negocios":
            cabecera = ["id", "slug", "nombre", "estado", "creado", "publicado", "reservas"]
            filas = await _csv_negocios(sesion)
        case "reservas":
            cabecera = ["id", "negocio_id", "inicio", "estado", "duracion_min", "total_centavos"]
            filas = await _csv_reservas(sesion, desde, hasta)
        case _:
            raise NoExiste("Solo se pueden exportar «negocios» o «reservas».")

    await _auditar(
        sesion,
        identidad,
        accion=f"exportar.{que}",
        entidad="export",
        entidad_id=None,
        despues={"desde": desde.isoformat(), "hasta": hasta.isoformat(), "filas": len(filas)},
    )

    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(cabecera)
    escritor.writerows(filas)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{que}-{hoy.isoformat()}.csv"'},
    )


# ── Piezas internas ───────────────────────────────────────────────────────────────────────


async def _pesos_vigentes(sesion: AsyncSession) -> RankingWeights:
    fila = (
        await sesion.execute(
            select(RankingWeights)
            .where(RankingWeights.effective_to.is_(None))
            .order_by(RankingWeights.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if fila is None:
        raise NoExiste(
            "No hay una versión de pesos vigente. Cárgala en el seed antes de tocar el ranking."
        )
    return fila


def _pintar_pesos(fila: RankingWeights) -> PesosDelRanking:
    return PesosDelRanking(
        version=fila.version,
        vigente_desde=fila.effective_from,
        distancia=float(fila.w_distancia),
        rating=float(fila.w_rating),
        reservas_recientes=float(fila.w_reservas_recientes),
        tasa_completado=float(fila.w_tasa_completado),
        completitud=float(fila.w_completitud),
        actividad=float(fila.w_actividad),
        boost_nuevo=float(fila.w_boost_nuevo),
        radio_km=float(fila.radius_km),
        decaimiento_km=float(fila.decay_km),
        dias_recientes=fila.recent_days,
        techo_reservas=fila.recent_cap,
        dias_actividad=fila.activity_days,
        dias_boost=fila.boost_days,
        bayes_m=float(fila.bayes_m),
        bayes_c=fila.bayes_c,
        patrocinados_por_pagina=fila.sponsored_per_page,
        tamano_pagina=fila.page_size,
        notas=fila.notes,
    )


def _pintar_plan(fila: Plan) -> PlanEnConsola:
    return PlanEnConsola(
        id=fila.id,
        codigo=fila.code,
        version=fila.version,
        nombre=fila.name,
        precio_centavos=fila.price_minor,
        moneda=fila.currency,
        periodo=fila.period,
        dias_prueba=fila.trial_days,
        limites=fila.limits,
        caracteristicas=fila.features,
        vigente_desde=fila.effective_from,
        vigente_hasta=fila.effective_to,
        activo=fila.active,
    )


async def _pintar_negocios(
    sesion: AsyncSession, negocios: list[Business]
) -> list[NegocioEnConsola]:
    """Serializador **de consola**: cuenta lo que hay dentro sin enseñar a nadie de dentro."""
    if not negocios:
        return []
    ids = [n.id for n in negocios]

    async def contar(modelo) -> dict[uuid.UUID, int]:
        filas = await sesion.execute(
            select(modelo.business_id, func.count())
            .where(modelo.business_id.in_(ids))
            .group_by(modelo.business_id)
        )
        return dict(filas.all())

    reservas = await contar(Booking)
    clientes = await contar(BusinessClient)

    ratings = {
        fila.business_id: fila
        for fila in (
            (
                await sesion.execute(
                    select(BusinessRatingStats).where(BusinessRatingStats.business_id.in_(ids))
                )
            )
            .scalars()
            .all()
        )
    }
    direcciones = dict(
        (
            await sesion.execute(
                select(Location.business_id, Location.address_line).where(
                    Location.business_id.in_(ids)
                )
            )
        ).all()
    )

    return [
        NegocioEnConsola(
            id=n.id,
            slug=n.slug,
            nombre=n.display_name,
            estado=n.status,
            zona_horaria=n.timezone,
            direccion=direcciones.get(n.id),
            creado=n.created_at,
            publicado=n.published_at,
            suspendido=n.suspended_at,
            motivo_suspension=n.suspension_reason,
            reservas=reservas.get(n.id, 0),
            clientes=clientes.get(n.id, 0),
            reviews=ratings[n.id].reviews_count if n.id in ratings else 0,
            rating=(
                float(ratings[n.id].rating_bayesian)
                if n.id in ratings and ratings[n.id].rating_bayesian is not None
                else None
            ),
        )
        for n in negocios
    ]


async def _serie_diaria(sesion: AsyncSession, modelo, desde: date) -> list[PuntoDeSerie]:
    """Suma el contador agregado por día. Vale igual para impresiones y para clics."""
    filas = (
        await sesion.execute(
            select(modelo.day, func.sum(modelo.count))
            .where(modelo.day >= desde)
            .group_by(modelo.day)
            .order_by(modelo.day)
        )
    ).all()
    return [PuntoDeSerie(dia=dia, valor=int(total or 0)) for dia, total in filas]


async def _csv_negocios(sesion: AsyncSession) -> list[list[Any]]:
    reservas = dict(
        (
            await sesion.execute(
                select(Booking.business_id, func.count()).group_by(Booking.business_id)
            )
        ).all()
    )
    filas = (
        (
            await sesion.execute(
                select(Business)
                .where(Business.deleted_at.is_(None))
                .order_by(Business.created_at)
                .limit(MAXIMO_EXPORTACION)
            )
        )
        .scalars()
        .all()
    )
    return [
        [
            str(n.id),
            n.slug,
            n.display_name,
            n.status,
            n.created_at.isoformat(),
            n.published_at.isoformat() if n.published_at else "",
            reservas.get(n.id, 0),
        ]
        for n in filas
    ]


async def _csv_reservas(sesion: AsyncSession, desde: date, hasta: date) -> list[list[Any]]:
    """Reservas del rango. **Ni el cliente ni el profesional**: identificador, hora y estado.

    Es lo que hace falta para cuadrar volumen y facturación, y nada más. Quién fue a cortarse
    el pelo el martes no es un dato que tenga que salir en un CSV descargable.
    """
    filas = (
        (
            await sesion.execute(
                select(Booking)
                .where(
                    func.date(Booking.starts_at) >= desde,
                    func.date(Booking.starts_at) <= hasta,
                )
                .order_by(Booking.starts_at)
                .limit(MAXIMO_EXPORTACION)
            )
        )
        .scalars()
        .all()
    )
    return [
        [
            str(b.id),
            str(b.business_id),
            b.starts_at.isoformat(),
            b.status,
            b.total_duration_min,
            b.total_amount_minor,
        ]
        for b in filas
    ]


async def _auditar(
    sesion: AsyncSession,
    identidad,
    *,
    accion: str,
    entidad: str,
    entidad_id: uuid.UUID | None,
    negocio_id: uuid.UUID | None = None,
    antes: dict[str, Any] | None = None,
    despues: dict[str, Any] | None = None,
    agente: str | None = None,
) -> None:
    """Deja el rastro. **Append-only y sin excepciones.**

    Una de las funciones de la auditoría es registrar lo que hace el equipo interno; si esto se
    pudiera saltar «solo para esta acción», dejaría de servir para lo único que sirve.
    """
    sesion.add(
        AuditLog(
            actor_kind="admin",
            actor_admin_id=identidad.admin_id,
            business_id=negocio_id,
            action=accion,
            entity_type=entidad,
            entity_id=entidad_id,
            before=antes,
            after=despues,
            user_agent=agente,
        )
    )
    await sesion.flush()
