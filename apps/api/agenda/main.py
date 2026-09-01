"""Punto de entrada de la API.

Una sola API sirve a las tres superficies (web pública, back-office y app), y las rutas se
agrupan por audiencia, no por módulo: `/publico`, `/mi` y `/negocio`. De esa separación
depende que un serializador público no acabe compartido con uno de negocio, que es como se
escapan los teléfonos (ADR-0012).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from agenda.ajustes import obtener_ajustes

ajustes = obtener_ajustes()

app = FastAPI(
    # El nombre comercial está sin decidir (D1): sale de configuración, no va a fuego.
    title="API de M2G Agenda",
    version="0.1.0",
    description=(
        "Reservas y marketplace de belleza y bienestar en Panamá. "
        "Cada endpoint cita el requisito del brief que cubre."
    ),
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
)


@app.get("/salud", tags=["operación"], summary="Comprueba que el proceso responde")
async def salud() -> JSONResponse:
    return JSONResponse({"estado": "ok", "entorno": ajustes.entorno})
