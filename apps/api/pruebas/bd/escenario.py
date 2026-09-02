"""Datos mínimos para las pruebas contra base de datos.

Se insertan con el rol **dueño**, que se salta la seguridad por fila. Es el único sitio donde
eso es correcto: montar el escenario necesita crear filas de **dos negocios distintos**, y
precisamente lo que se va a probar es que desde uno no se ve el otro. Si el montaje usara el
rol de la aplicación, la propia prueba de aislamiento no podría prepararse.

Los datos son de dos salones de Ciudad de Panamá, no «Negocio A» y «Negocio B»: cuando una
prueba falla, leer el error con nombres reales ahorra un minuto cada vez.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

URL_DUENO_ASYNC = os.environ.get(
    "DATABASE_URL_DUENO_ASYNC",
    "postgresql+asyncpg://agenda_owner:agenda@localhost:5433/agenda",
)


@dataclass(frozen=True)
class Negocio:
    """Lo que una prueba necesita para hablar de un negocio y sus citas."""

    id: uuid.UUID
    nombre: str
    staff_id: uuid.UUID
    cliente_id: uuid.UUID


@dataclass(frozen=True)
class Escenario:
    """Dos barberías vecinas que no tienen nada que ver la una con la otra."""

    cangrejo: Negocio
    obarrio: Negocio


async def montar_escenario() -> Escenario:
    """Crea dos negocios con un profesional y un cliente cada uno. Idempotente por ejecución."""
    motor = create_async_engine(URL_DUENO_ASYNC, poolclass=None)
    try:
        async with motor.begin() as conexion:
            cangrejo = await _crear_negocio(
                conexion,
                nombre="Barbería El Cangrejo",
                profesional="Kevin Ortega",
                cliente="Yaritza Beitía",
            )
            obarrio = await _crear_negocio(
                conexion,
                nombre="Estudio Obarrio",
                profesional="Marielys Ruiz",
                cliente="Abdiel Him",
            )
        return Escenario(cangrejo=cangrejo, obarrio=obarrio)
    finally:
        await motor.dispose()


async def _crear_negocio(conexion, *, nombre: str, profesional: str, cliente: str) -> Negocio:
    sufijo = uuid.uuid4().hex[:8]

    dueno_id = (
        await conexion.execute(
            text(
                """
                INSERT INTO users (phone_e164, full_name)
                VALUES (:telefono, :nombre)
                RETURNING id
                """
            ),
            {"telefono": f"+5076{sufijo[:7]}", "nombre": f"Dueño de {nombre}"},
        )
    ).scalar_one()

    negocio_id = (
        await conexion.execute(
            text(
                """
                INSERT INTO businesses (slug, display_name, owner_user_id, timezone, status)
                VALUES (:slug, :nombre, :dueno, 'America/Panama', 'publicado')
                RETURNING id
                """
            ),
            {
                "slug": f"{nombre.lower().replace(' ', '-')}-{sufijo}",
                "nombre": nombre,
                "dueno": dueno_id,
            },
        )
    ).scalar_one()

    staff_id = (
        await conexion.execute(
            text(
                """
                INSERT INTO staff_profiles (business_id, display_name)
                VALUES (:negocio, :profesional)
                RETURNING id
                """
            ),
            {"negocio": negocio_id, "profesional": profesional},
        )
    ).scalar_one()

    cliente_id = (
        await conexion.execute(
            text(
                """
                INSERT INTO business_clients (business_id, display_name)
                VALUES (:negocio, :cliente)
                RETURNING id
                """
            ),
            {"negocio": negocio_id, "cliente": cliente},
        )
    ).scalar_one()

    return Negocio(id=negocio_id, nombre=nombre, staff_id=staff_id, cliente_id=cliente_id)


def manana_a_las(hora: int, minuto: int = 0) -> datetime:
    """Un instante de mañana en UTC. Mañana, para no chocar con la antelación mínima."""
    base = datetime.now(UTC) + timedelta(days=1)
    return base.replace(hour=hora, minute=minuto, second=0, microsecond=0)


SQL_CITA = text(
    """
    WITH nueva AS (
        INSERT INTO bookings (
            business_id, staff_id, business_client_id, status,
            starts_at, ends_at, total_duration_min, source
        )
        VALUES (
            :negocio, :staff, :cliente, :estado,
            :inicio, :fin, :duracion, 'negocio_manual'
        )
        RETURNING id
    )
    INSERT INTO staff_occupancy (
        business_id, staff_id, kind, status, booking_id,
        starts_at, ends_at, buffer_before_min, buffer_after_min
    )
    SELECT :negocio, :staff, 'reserva', :estado, nueva.id,
           :inicio, :fin, :buffer_antes, :buffer_despues
    FROM nueva
    RETURNING id
    """
)


async def crear_cita(
    conexion,
    negocio: Negocio,
    *,
    inicio: datetime,
    minutos: int = 45,
    estado: str = "confirmada",
    buffer_antes: int = 0,
    buffer_despues: int = 0,
) -> uuid.UUID:
    """Inserta reserva y ocupación **en la misma sentencia**, como hace la API.

    Es importante que la prueba lo haga igual que producción: si insertara la ocupación en otra
    transacción, la carrera que se quiere provocar no sería la misma carrera.
    """
    resultado = await conexion.execute(
        SQL_CITA,
        {
            "negocio": negocio.id,
            "staff": negocio.staff_id,
            "cliente": negocio.cliente_id,
            "estado": estado,
            "inicio": inicio,
            "fin": inicio + timedelta(minutes=minutos),
            "duracion": minutos,
            "buffer_antes": buffer_antes,
            "buffer_despues": buffer_despues,
        },
    )
    return resultado.scalar_one()
