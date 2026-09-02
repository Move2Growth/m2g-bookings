"""Datos mínimos para las pruebas de notificaciones: un salón, un profesional y una clienta.

Se monta con el rol **dueño**, igual que `pruebas/bd/escenario.py` y por el mismo motivo: crear
el escenario necesita escribir en varios negocios y lo que se prueba después es justamente lo
que se ve desde dentro de uno.

Cada llamada crea un negocio **nuevo**. Es más lento que reutilizar uno y es lo correcto: la
base de pruebas conserva lo que las pruebas escriben —las carreras no se pueden probar
deshaciendo al final—, y una prueba que contara filas sobre un negocio compartido empezaría a
fallar sola a la tercera ejecución.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from pruebas.bd.escenario import URL_DUENO_ASYNC


@dataclass(frozen=True)
class NegocioDePrueba:
    """Un salón con una clienta a la que se puede escribir."""

    id: uuid.UUID
    staff_id: uuid.UUID
    cliente_id: uuid.UUID
    telefono_de_la_clienta: str | None


async def montar_negocio(*, telefono: bool = True, correo: bool = False) -> NegocioDePrueba:
    """Crea el salón. `telefono=False` sirve para probar el caso de «no hay por dónde avisar»."""
    sufijo = uuid.uuid4().hex[:8]
    telefono_clienta = f"+5076{sufijo[:7]}" if telefono else None

    motor = create_async_engine(URL_DUENO_ASYNC, poolclass=None)
    try:
        async with motor.begin() as conexion:
            dueno_id = (
                await conexion.execute(
                    text(
                        "INSERT INTO users (phone_e164, full_name, email)"
                        " VALUES (:telefono, :nombre, :correo) RETURNING id"
                    ),
                    {
                        "telefono": f"+5075{sufijo[:7]}",
                        "nombre": "Dueña de Salón Vía Argentina",
                        "correo": f"duena-{sufijo}@ejemplo.pa",
                    },
                )
            ).scalar_one()

            negocio_id = (
                await conexion.execute(
                    text(
                        """
                        INSERT INTO businesses
                          (slug, display_name, owner_user_id, timezone, status,
                           whatsapp_phone_e164)
                        VALUES (:slug, :nombre, :dueno, 'America/Panama', 'publicado', :whatsapp)
                        RETURNING id
                        """
                    ),
                    {
                        "slug": f"salon-via-argentina-{sufijo}",
                        "nombre": "Salón Vía Argentina",
                        "dueno": dueno_id,
                        "whatsapp": f"+5072{sufijo[:7]}",
                    },
                )
            ).scalar_one()

            staff_id = (
                await conexion.execute(
                    text(
                        "INSERT INTO staff_profiles (business_id, display_name)"
                        " VALUES (:negocio, 'Marielys Ruiz') RETURNING id"
                    ),
                    {"negocio": negocio_id},
                )
            ).scalar_one()

            # La clienta tiene cuenta: el «¿cómo te fue?» solo se le pide a quien puede dejar
            # la reseña, y el cliente rápido del mostrador no puede.
            clienta_user_id = (
                await conexion.execute(
                    text(
                        "INSERT INTO users (phone_e164, full_name) VALUES (:telefono, :nombre)"
                        " RETURNING id"
                    ),
                    {"telefono": f"+5077{sufijo[:7]}", "nombre": "Yaritza Beitía"},
                )
            ).scalar_one()

            cliente_id = (
                await conexion.execute(
                    text(
                        """
                        INSERT INTO business_clients
                          (business_id, user_id, display_name, phone_e164, email)
                        VALUES (:negocio, :usuario, 'Yaritza Beitía', :telefono, :correo)
                        RETURNING id
                        """
                    ),
                    {
                        "negocio": negocio_id,
                        "usuario": clienta_user_id,
                        "telefono": telefono_clienta,
                        "correo": f"yaritza-{sufijo}@ejemplo.pa" if correo else None,
                    },
                )
            ).scalar_one()

        return NegocioDePrueba(
            id=negocio_id,
            staff_id=staff_id,
            cliente_id=cliente_id,
            telefono_de_la_clienta=telefono_clienta,
        )
    finally:
        await motor.dispose()


async def crear_cita(
    negocio: NegocioDePrueba,
    *,
    inicio: datetime,
    minutos: int = 45,
    estado: str = "confirmada",
    completada_en: datetime | None = None,
) -> uuid.UUID:
    """Reserva y ocupación en la misma sentencia, como en producción. Devuelve la reserva."""
    motor = create_async_engine(URL_DUENO_ASYNC, poolclass=None)
    try:
        async with motor.begin() as conexion:
            reserva_id = (
                await conexion.execute(
                    text(
                        """
                        WITH nueva AS (
                            INSERT INTO bookings (
                                business_id, staff_id, business_client_id, client_user_id,
                                status, starts_at, ends_at, total_duration_min, source,
                                completed_at
                            )
                            SELECT :negocio, :staff, :cliente, bc.user_id,
                                   :estado, :inicio, :fin, :duracion, 'negocio_manual',
                                   :completada
                              FROM business_clients bc WHERE bc.id = :cliente
                            RETURNING id
                        ), ocupacion AS (
                            INSERT INTO staff_occupancy (
                                business_id, staff_id, kind, status, booking_id,
                                starts_at, ends_at, buffer_before_min, buffer_after_min
                            )
                            SELECT :negocio, :staff, 'reserva', :estado, nueva.id,
                                   :inicio, :fin, 0, 0
                            FROM nueva
                            RETURNING booking_id
                        )
                        SELECT booking_id FROM ocupacion
                        """
                    ),
                    {
                        "negocio": negocio.id,
                        "staff": negocio.staff_id,
                        "cliente": negocio.cliente_id,
                        "estado": estado,
                        "inicio": inicio,
                        "fin": inicio + timedelta(minutes=minutos),
                        "duracion": minutos,
                        "completada": completada_en,
                    },
                )
            ).scalar_one()
        return reserva_id
    finally:
        await motor.dispose()


async def apagar_canal(
    negocio: NegocioDePrueba, *, usuario_id: uuid.UUID, canal: str, categoria: str
) -> None:
    """Deja escrito que esa persona no quiere ese canal para esa categoría (NTF-3)."""
    motor = create_async_engine(URL_DUENO_ASYNC, poolclass=None)
    try:
        async with motor.begin() as conexion:
            await conexion.execute(
                text(
                    "INSERT INTO notification_preferences (user_id, channel, category, enabled)"
                    " VALUES (:usuario, :canal, :categoria, false)"
                ),
                {"usuario": usuario_id, "canal": canal, "categoria": categoria},
            )
    finally:
        await motor.dispose()
