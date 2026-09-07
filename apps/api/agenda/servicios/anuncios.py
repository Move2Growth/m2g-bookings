"""La publicidad flash del salón: un texto suyo, con vigencia, en su propia ficha.

**No es `ad_campaigns`.** Ahí vive el posicionamiento pagado del marketplace —el que sale
etiquetado «Patrocinado», con su inventario, su factura y su tope de 2 de cada 10 (ADR-0009,
ADR-0010)—. Esto es otra cosa: el salón escribiendo «2x1 en color hasta el domingo» en su
propia página. Es gratis, no compite con nadie y no toca el ranking. Mezclarlas habría sido
regalar la portada del marketplace a cualquiera que escriba un banner.

La vigencia se comprueba **en la política de seguridad por fila**, no aquí (migración 0010): un
anuncio caducado deja de ser legible para el rol público aunque el endpoint se distraiga.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agenda.errores import DatoInvalido, NoExiste, YaExiste
from agenda.modelos.dueno import LARGO_MAXIMO_ANUNCIO, BusinessBanner

#: `SQLSTATE 23P01` — violación de restricción de exclusión. La misma que al reservar, y por el
#: mismo motivo: dos anuncios activos que se pisan son dos cosas ocupando el mismo sitio.
EXCLUSION_VIOLADA = "23P01"


@dataclass(frozen=True)
class Anuncio:
    id: uuid.UUID
    texto: str
    activo: bool
    desde: datetime
    hasta: datetime | None
    vigente: bool


def _pintar(fila: BusinessBanner, *, ahora: datetime) -> Anuncio:
    return Anuncio(
        id=fila.id,
        texto=fila.message,
        activo=fila.active,
        desde=fila.starts_at,
        hasta=fila.ends_at,
        vigente=(
            fila.active
            and fila.starts_at <= ahora
            and (fila.ends_at is None or fila.ends_at > ahora)
        ),
    )


async def listar(sesion: AsyncSession, *, negocio_id: uuid.UUID) -> list[Anuncio]:
    """Todos los del salón, vigentes o no. El histórico también es suyo."""
    ahora = datetime.now(UTC)
    filas = (
        (
            await sesion.execute(
                select(BusinessBanner)
                .where(BusinessBanner.business_id == negocio_id)
                .order_by(BusinessBanner.starts_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [_pintar(fila, ahora=ahora) for fila in filas]


def _con_zona(momento: datetime | None) -> datetime | None:
    """Una fecha sin zona se entiende **en UTC**, no se rechaza.

    Quien manda `"2026-09-30"` está diciendo una fecha, no un instante, y Pydantic la convierte
    en un `datetime` sin zona. Compararlo con uno que sí la lleva revienta con un `TypeError`
    que sale por la API como **500**: un error del servidor por un dato perfectamente razonable.
    """
    if momento is None or momento.tzinfo is not None:
        return momento
    return momento.replace(tzinfo=UTC)


async def crear(
    sesion: AsyncSession,
    *,
    negocio_id: uuid.UUID,
    texto: str,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    activo: bool = True,
) -> Anuncio:
    """Escribe el anuncio. **Solo puede haber uno activo a la vez** en cada tramo de fechas."""
    texto = texto.strip()
    if not texto:
        raise DatoInvalido("El anuncio necesita un texto.")
    if len(texto) > LARGO_MAXIMO_ANUNCIO:
        raise DatoInvalido(
            f"El anuncio no puede pasar de {LARGO_MAXIMO_ANUNCIO} caracteres: se lee de un "
            "vistazo en la ficha, no es un folleto."
        )

    desde = _con_zona(desde) or datetime.now(UTC)
    hasta = _con_zona(hasta)
    if hasta is not None and hasta <= desde:
        raise DatoInvalido("El anuncio tiene que terminar después de empezar.")

    fila = BusinessBanner(
        business_id=negocio_id, message=texto, starts_at=desde, ends_at=hasta, active=activo
    )
    sesion.add(fila)
    await _guardar(sesion)
    return _pintar(fila, ahora=datetime.now(UTC))


async def editar(
    sesion: AsyncSession,
    *,
    negocio_id: uuid.UUID,
    anuncio_id: uuid.UUID,
    texto: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    activo: bool | None = None,
    quitar_fin: bool = False,
) -> Anuncio:
    fila = await _del_negocio(sesion, negocio_id, anuncio_id)

    if texto is not None:
        texto = texto.strip()
        if not texto:
            raise DatoInvalido("El anuncio necesita un texto.")
        if len(texto) > LARGO_MAXIMO_ANUNCIO:
            raise DatoInvalido(f"El anuncio no puede pasar de {LARGO_MAXIMO_ANUNCIO} caracteres.")
        fila.message = texto
    if desde is not None:
        fila.starts_at = _con_zona(desde)
    # `hasta` a `None` significa dos cosas —«no lo cambies» y «quítale la fecha de fin»— y se
    # distinguen con una bandera, igual que el precio del servicio en el catálogo.
    if quitar_fin:
        fila.ends_at = None
    elif hasta is not None:
        fila.ends_at = _con_zona(hasta)
    if activo is not None:
        fila.active = activo

    if fila.ends_at is not None and fila.ends_at <= fila.starts_at:
        raise DatoInvalido("El anuncio tiene que terminar después de empezar.")

    await _guardar(sesion)
    return _pintar(fila, ahora=datetime.now(UTC))


async def retirar(sesion: AsyncSession, *, negocio_id: uuid.UUID, anuncio_id: uuid.UUID) -> Anuncio:
    """Lo apaga. **No borra la fila**: el salón puede querer volver a lanzarlo en diciembre."""
    fila = await _del_negocio(sesion, negocio_id, anuncio_id)
    fila.active = False
    await sesion.flush()
    return _pintar(fila, ahora=datetime.now(UTC))


async def vigente(sesion: AsyncSession, *, negocio_id: uuid.UUID) -> Anuncio | None:
    """El que toca enseñar en la ficha pública, o nada.

    Con el rol público **no hace falta filtrar por vigencia**: la política ya solo deja ver los
    activos, dentro de fecha y de un negocio publicado. El filtro se escribe igual porque esta
    misma función se llama también desde el panel, donde el rol es otro (ADR-0002).
    """
    ahora = datetime.now(UTC)
    fila = (
        await sesion.execute(
            select(BusinessBanner)
            .where(
                BusinessBanner.business_id == negocio_id,
                BusinessBanner.active.is_(True),
                BusinessBanner.starts_at <= ahora,
                (BusinessBanner.ends_at.is_(None)) | (BusinessBanner.ends_at > ahora),
            )
            .order_by(BusinessBanner.starts_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return _pintar(fila, ahora=ahora) if fila is not None else None


async def _del_negocio(
    sesion: AsyncSession, negocio_id: uuid.UUID, anuncio_id: uuid.UUID
) -> BusinessBanner:
    fila = (
        await sesion.execute(
            select(BusinessBanner).where(
                BusinessBanner.id == anuncio_id, BusinessBanner.business_id == negocio_id
            )
        )
    ).scalar_one_or_none()
    if fila is None:
        raise NoExiste("Ese anuncio no existe en este negocio.")
    return fila


async def _guardar(sesion: AsyncSession) -> None:
    try:
        await sesion.flush()
    except IntegrityError as error:
        codigo = getattr(getattr(error, "orig", None), "sqlstate", None)
        if codigo == EXCLUSION_VIOLADA or EXCLUSION_VIOLADA in str(error):
            raise YaExiste(
                "Ya tienes un anuncio activo en esas fechas. Retíralo o cambia las fechas."
            ) from error
        raise
