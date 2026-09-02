"""Un salón con dos profesionales, sus clientes y sus citas, para las pruebas del panel.

Se monta con el rol **dueño**, que se salta la seguridad por fila, y ese es el único sitio
donde eso es correcto: preparar el escenario exige crear filas que después, desde el rol de la
aplicación, no se van a poder ver. Si el montaje usara el rol de la aplicación, la propia
prueba de aislamiento no podría prepararse.

Los nombres son de un salón de Ciudad de Panamá y no «Profesional A» y «Profesional B»: cuando
una prueba falla, leer el error con nombres reales ahorra un minuto cada vez.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from pruebas.bd.escenario import URL_DUENO_ASYNC


@dataclass(frozen=True)
class Profesional:
    id: uuid.UUID
    nombre: str
    user_id: uuid.UUID


@dataclass(frozen=True)
class SalonConEquipo:
    """Una barbería con dos profesionales, cada uno con su clienta y su cita."""

    negocio_id: uuid.UUID
    #: El nombre lleva un sufijo irrepetible. Sirve para acotar una búsqueda a **este** salón:
    #: la base de pruebas acumula los de ejecuciones anteriores y sin acotar, el que se busca
    #: se queda fuera de la primera página.
    nombre: str
    slug: str
    dueno_user_id: uuid.UUID
    kevin: Profesional
    marielys: Profesional
    servicio_id: uuid.UUID
    cliente_de_kevin: uuid.UUID
    cliente_de_marielys: uuid.UUID
    cita_de_kevin: uuid.UUID
    cita_de_marielys: uuid.UUID


@asynccontextmanager
async def conexion_de_dueno() -> AsyncIterator[AsyncSession]:
    """Sesión con el rol dueño. Solo para montar escenarios y para comprobar el resultado."""
    motor = create_async_engine(URL_DUENO_ASYNC, poolclass=None)
    crear = async_sessionmaker(motor, class_=AsyncSession, expire_on_commit=False)
    try:
        async with crear() as sesion, sesion.begin():
            yield sesion
    finally:
        await motor.dispose()


def manana_a_las(hora: int, minuto: int = 0) -> datetime:
    """Un instante de mañana en UTC. Mañana, para no chocar con la antelación mínima."""
    base = datetime.now(UTC) + timedelta(days=1)
    return base.replace(hour=hora, minute=minuto, second=0, microsecond=0)


def ayer_a_las(hora: int, minuto: int = 0) -> datetime:
    """Un instante de ayer, para las citas ya completadas de las pruebas de reseñas."""
    base = datetime.now(UTC) - timedelta(days=1)
    return base.replace(hour=hora, minute=minuto, second=0, microsecond=0)


async def montar_salon(sufijo: str | None = None) -> SalonConEquipo:
    """Crea el salón entero. Cada llamada crea uno nuevo: las pruebas no se pisan entre sí."""
    marca = sufijo or uuid.uuid4().hex[:8]

    async with conexion_de_dueno() as sesion:
        # Cada teléfono lleva su propio azar: `users.phone_e164` es único en toda la
        # plataforma, y derivar los tres del mismo sufijo hacía que dos pruebas seguidas
        # chocaran de vez en cuando. Un fallo intermitente en el escenario es peor que
        # cualquier fallo de la prueba.
        dueno = await _usuario(sesion, f"Dueño {marca}", _telefono())
        kevin_user = await _usuario(sesion, "Kevin Ortega", _telefono())
        marielys_user = await _usuario(sesion, "Marielys Ruiz", _telefono())

        nombre = f"Barbería El Cangrejo {marca}"
        slug = f"barberia-{marca}"
        negocio_id = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO businesses (slug, display_name, owner_user_id, timezone, status,
                                            published_at)
                    VALUES (:slug, :nombre, :dueno, 'America/Panama', 'publicado', now())
                    RETURNING id
                    """
                ),
                {"slug": slug, "nombre": nombre, "dueno": dueno},
            )
        ).scalar_one()

        await sesion.execute(
            text("INSERT INTO business_settings (business_id) VALUES (:negocio)"),
            {"negocio": negocio_id},
        )
        papeles = (
            (dueno, "dueno"),
            (kevin_user, "profesional"),
            (marielys_user, "profesional"),
        )
        for usuario, rol in papeles:
            await sesion.execute(
                text(
                    """
                    INSERT INTO memberships (business_id, user_id, role, status, accepted_at)
                    VALUES (:negocio, :usuario, :rol, 'activa', now())
                    """
                ),
                {"negocio": negocio_id, "usuario": usuario, "rol": rol},
            )

        kevin = await _profesional(sesion, negocio_id, "Kevin Ortega", kevin_user)
        marielys = await _profesional(sesion, negocio_id, "Marielys Ruiz", marielys_user)

        servicio_id = await _servicio(sesion, negocio_id)
        for profesional in (kevin, marielys):
            await sesion.execute(
                text(
                    """
                    INSERT INTO staff_services (business_id, staff_id, service_id)
                    VALUES (:negocio, :staff, :servicio)
                    """
                ),
                {"negocio": negocio_id, "staff": profesional.id, "servicio": servicio_id},
            )

        cliente_kevin = await _cliente(sesion, negocio_id, "Yaritza Beitía", "+50761110001")
        cliente_marielys = await _cliente(sesion, negocio_id, "Abdiel Him", "+50761110002")

        cita_kevin = await _cita(
            sesion, negocio_id, kevin.id, cliente_kevin, servicio_id, manana_a_las(10)
        )
        cita_marielys = await _cita(
            sesion, negocio_id, marielys.id, cliente_marielys, servicio_id, manana_a_las(11)
        )

    return SalonConEquipo(
        negocio_id=negocio_id,
        nombre=nombre,
        slug=slug,
        dueno_user_id=dueno,
        kevin=kevin,
        marielys=marielys,
        servicio_id=servicio_id,
        cliente_de_kevin=cliente_kevin,
        cliente_de_marielys=cliente_marielys,
        cita_de_kevin=cita_kevin,
        cita_de_marielys=cita_marielys,
    )


def _telefono() -> str:
    """Un E.164 panameño irrepetible. Doce dígitos: +507 y ocho más, como los de verdad."""
    return f"+507{uuid.uuid4().int % 100_000_000:08d}"


async def _usuario(sesion: AsyncSession, nombre: str, telefono: str) -> uuid.UUID:
    return (
        await sesion.execute(
            text(
                """
                INSERT INTO users (phone_e164, full_name, phone_verified_at)
                VALUES (:telefono, :nombre, now())
                RETURNING id
                """
            ),
            {"telefono": telefono, "nombre": nombre},
        )
    ).scalar_one()


async def _profesional(
    sesion: AsyncSession, negocio_id: uuid.UUID, nombre: str, user_id: uuid.UUID
) -> Profesional:
    staff_id = (
        await sesion.execute(
            text(
                """
                INSERT INTO staff_profiles (business_id, user_id, display_name)
                VALUES (:negocio, :usuario, :nombre)
                RETURNING id
                """
            ),
            {"negocio": negocio_id, "usuario": user_id, "nombre": nombre},
        )
    ).scalar_one()
    return Profesional(id=staff_id, nombre=nombre, user_id=user_id)


async def _servicio(sesion: AsyncSession, negocio_id: uuid.UUID) -> uuid.UUID:
    categoria = (
        await sesion.execute(
            text("SELECT id FROM service_categories ORDER BY position, name LIMIT 1")
        )
    ).scalar_one_or_none()
    if categoria is None:
        categoria = (
            await sesion.execute(
                text(
                    """
                    INSERT INTO service_categories (slug, name)
                    VALUES ('barberia', 'Barbería')
                    RETURNING id
                    """
                )
            )
        ).scalar_one()

    return (
        await sesion.execute(
            text(
                """
                INSERT INTO services (business_id, service_category_id, name, duration_min,
                                      price_kind, price_minor)
                VALUES (:negocio, :categoria, 'Corte + barba', 45, 'fijo', 1800)
                RETURNING id
                """
            ),
            {"negocio": negocio_id, "categoria": categoria},
        )
    ).scalar_one()


async def _cliente(
    sesion: AsyncSession, negocio_id: uuid.UUID, nombre: str, telefono: str
) -> uuid.UUID:
    return (
        await sesion.execute(
            text(
                """
                INSERT INTO business_clients (business_id, display_name, phone_e164)
                VALUES (:negocio, :nombre, :telefono)
                RETURNING id
                """
            ),
            {"negocio": negocio_id, "nombre": nombre, "telefono": telefono},
        )
    ).scalar_one()


async def _cita(
    sesion: AsyncSession,
    negocio_id: uuid.UUID,
    staff_id: uuid.UUID,
    cliente_id: uuid.UUID,
    servicio_id: uuid.UUID,
    inicio: datetime,
    *,
    estado: str = "confirmada",
    minutos: int = 45,
    client_user_id: uuid.UUID | None = None,
) -> uuid.UUID:
    """Inserta reserva, ítem y ocupación **en la misma transacción**, como hace la API."""
    fin = inicio + timedelta(minutes=minutos)
    reserva_id = (
        await sesion.execute(
            text(
                """
                INSERT INTO bookings (business_id, staff_id, business_client_id, client_user_id,
                                      status, starts_at, ends_at, total_duration_min,
                                      total_amount_minor, source)
                VALUES (:negocio, :staff, :cliente, :usuario, :estado, :inicio, :fin, :duracion,
                        1800, 'negocio_manual')
                RETURNING id
                """
            ),
            {
                "negocio": negocio_id,
                "staff": staff_id,
                "cliente": cliente_id,
                "usuario": client_user_id,
                "estado": estado,
                "inicio": inicio,
                "fin": fin,
                "duracion": minutos,
            },
        )
    ).scalar_one()

    await sesion.execute(
        text(
            """
            INSERT INTO booking_items (business_id, booking_id, position, service_id,
                                       name_snapshot, duration_min_snapshot, price_kind_snapshot,
                                       price_minor_snapshot, currency,
                                       buffer_before_min_snapshot, buffer_after_min_snapshot)
            VALUES (:negocio, :reserva, 1, :servicio, 'Corte + barba', :duracion, 'fijo', 1800,
                    'USD', 0, 0)
            """
        ),
        {
            "negocio": negocio_id,
            "reserva": reserva_id,
            "servicio": servicio_id,
            "duracion": minutos,
        },
    )
    await sesion.execute(
        text(
            """
            INSERT INTO staff_occupancy (business_id, staff_id, kind, status, booking_id,
                                         starts_at, ends_at, buffer_before_min, buffer_after_min)
            VALUES (:negocio, :staff, 'reserva', :estado, :reserva, :inicio, :fin, 0, 0)
            """
        ),
        {
            "negocio": negocio_id,
            "staff": staff_id,
            "estado": estado,
            "reserva": reserva_id,
            "inicio": inicio,
            "fin": fin,
        },
    )
    return reserva_id


async def crear_cita_completada(
    negocio_id: uuid.UUID,
    staff_id: uuid.UUID,
    cliente_id: uuid.UUID,
    servicio_id: uuid.UUID,
    usuario_id: uuid.UUID,
    *,
    inicio: datetime | None = None,
) -> uuid.UUID:
    """Una cita de ayer ya cerrada: lo mínimo para poder dejar una reseña (REV-1)."""
    async with conexion_de_dueno() as sesion:
        return await _cita(
            sesion,
            negocio_id,
            staff_id,
            cliente_id,
            servicio_id,
            inicio or ayer_a_las(10),
            estado="completada",
            client_user_id=usuario_id,
        )


async def crear_cita(
    negocio_id: uuid.UUID,
    staff_id: uuid.UUID,
    cliente_id: uuid.UUID,
    servicio_id: uuid.UUID,
    *,
    inicio: datetime,
    estado: str = "confirmada",
    usuario_id: uuid.UUID | None = None,
) -> uuid.UUID:
    async with conexion_de_dueno() as sesion:
        return await _cita(
            sesion,
            negocio_id,
            staff_id,
            cliente_id,
            servicio_id,
            inicio,
            estado=estado,
            client_user_id=usuario_id,
        )
