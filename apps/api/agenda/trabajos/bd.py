"""De dónde saca la base de datos un trabajador, que no es de donde la saca la API.

Un trabajo periódico tiene un problema que un endpoint no tiene: **no sabe de qué negocio es**.
La petición HTTP llega con su sesión y de ahí sale el tenant; el planificador se despierta a las
tres de la mañana sin nada. Y las políticas de seguridad por fila no hacen excepciones: con el
rol de la API y sin `app.current_business_id` fijado, un `SELECT` sobre `bookings` devuelve cero
filas. No falla —devuelve cero—, que es precisamente la forma de fallo que ADR-0002 quiere.

De ahí la forma de este módulo, que es la del propio ADR-0008:

1. Una sesión **de sistema** (rol `agenda_admin`, el del back-office) sirve para una sola cosa:
   **enumerar identificadores**. Qué negocios hay. Nada más.
2. Para cada identificador se abre una sesión **con el tenant fijado**, y ahí dentro pasa todo
   el trabajo de verdad.

El rol de sistema no es un `BYPASSRLS`: tiene sus propias políticas, es el mismo que usa el
back-office y está auditado. Conectarse como dueño de las tablas sí desactivaría el aislamiento
entero, y por eso no se hace ni aquí.

Las fábricas se pueden **inyectar por el contexto** del trabajador. Es lo que permite que las
pruebas ejerzan los trabajos contra la base de pruebas llamando a la función directamente, sin
Redis y sin variables de entorno globales.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from agenda.bd import sesion_de_negocio
from agenda.modelos.negocio import Business

#: Conexión del rol de sistema. Se lee del entorno y **hay que documentarla** en `.env.example`
#: y en `docs/operacion/SECRETOS-Y-VARIABLES.md` como el resto: nombre y para qué, nunca el
#: valor.
VARIABLE_DSN_SISTEMA = "DATABASE_URL_TRABAJOS"
DSN_SISTEMA_POR_DEFECTO = "postgresql+asyncpg://agenda_admin:agenda@localhost:5433/agenda"

FabricaDeNegocio = Callable[[uuid.UUID], AbstractAsyncContextManager[AsyncSession]]
FabricaDeSistema = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@lru_cache
def motor_de_sistema() -> AsyncEngine:
    """El pool del trabajador, aparte del de la API: sus picos no se pisan."""
    return create_async_engine(
        os.environ.get(VARIABLE_DSN_SISTEMA, DSN_SISTEMA_POR_DEFECTO),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )


@asynccontextmanager
async def sesion_de_sistema() -> AsyncIterator[AsyncSession]:
    """Sesión sin tenant con el rol del back-office. **Solo para enumerar y para plataforma.**

    Dos usos legítimos y ninguno más: saber qué negocios hay que recorrer, y tocar las
    notificaciones que no son de ningún negocio (los OTP y los avisos de plataforma llevan
    `business_id` nulo). Todo lo que sea leer o escribir datos de un salón se hace con el
    tenant fijado, aunque desde aquí «funcionaría».
    """
    crear = async_sessionmaker(motor_de_sistema(), class_=AsyncSession, expire_on_commit=False)
    async with crear() as sesion, sesion.begin():
        yield sesion


def fabrica_de_negocio(ctx: dict[str, Any]) -> FabricaDeNegocio:
    """La fábrica de sesiones con tenant del trabajador, o la de producción si no inyectó una."""
    return ctx.get("sesion_de_negocio", sesion_de_negocio)


def fabrica_de_sistema(ctx: dict[str, Any]) -> FabricaDeSistema:
    return ctx.get("sesion_de_sistema", sesion_de_sistema)


async def negocios_vivos(sesion: AsyncSession) -> list[uuid.UUID]:
    """Los negocios que hay que recorrer: todos menos los borrados.

    Incluye los borradores a propósito. Un salón sin publicar puede tener citas creadas desde
    el mostrador, y su cliente merece el recordatorio igual que el de un salón publicado.
    """
    filas = await sesion.execute(select(Business.id).where(Business.deleted_at.is_(None)))
    return list(filas.scalars().all())
