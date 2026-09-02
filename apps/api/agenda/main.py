"""Punto de entrada de la API.

Una sola API sirve a las tres superficies (web pública, back-office y app), y las rutas se
agrupan por audiencia, no por módulo: `/publico`, `/mi` y `/negocio`. De esa separación
depende que un serializador público no acabe compartido con uno de negocio, que es como se
escapan los teléfonos (ADR-0012).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agenda.ajustes import obtener_ajustes
from agenda.errores import ErrorDeDominio

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


@app.exception_handler(ErrorDeDominio)
async def manejar_error_de_dominio(_: Request, error: ErrorDeDominio) -> JSONResponse:
    """Un solo sitio traduce los errores de dominio a HTTP.

    Sin esto, cada endpoint acabaría inventándose su propio formato y el cliente tendría que
    saber cuál es cuál. El código viaja estable; el mensaje se puede reescribir cuando haga
    falta sin romper a nadie.
    """
    return JSONResponse(status_code=error.estado_http, content=error.como_respuesta())


@app.get("/salud", tags=["operación"], summary="Comprueba que el proceso responde")
async def salud() -> JSONResponse:
    return JSONResponse({"estado": "ok", "entorno": ajustes.entorno})
