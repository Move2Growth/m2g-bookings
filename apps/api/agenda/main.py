"""Punto de entrada de la API.

Una sola API sirve a las tres superficies (web pública, back-office y app), y las rutas se
agrupan por audiencia, no por módulo: `/publico`, `/mi` y `/negocio`. De esa separación
depende que un serializador público no acabe compartido con uno de negocio, que es como se
escapan los teléfonos (ADR-0012).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm.exc import StaleDataError

from agenda.ajustes import obtener_ajustes
from agenda.api import (
    acceso,
    cliente,
    consola,
    favoritos,
    invitaciones,
    mi_telefono,
    negocio,
    negocio_agenda,
    negocio_catalogo,
    negocio_clientes,
    negocio_dueno,
    negocio_equipo,
    negocio_ficha,
    negocio_miembros,
    onboarding,
    perfil_profesional,
    profesional,
    publico,
    publico_mapa,
    publico_profesionales,
    resenas,
)
from agenda.errores import CarreraEnLaBase, ErrorDeDominio, NoAutorizado

ajustes = obtener_ajustes()

app = FastAPI(
    # El nombre comercial está sin decidir (D1): sale de configuración, no va a fuego.
    title="API de Bukeo",
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


#: Cómo se llama en castellano cada tipo de fallo de validación de Pydantic. No están todos: los
#: que faltan caen en un mensaje genérico, que es mejor que enseñar el nombre inglés del tipo.
_MOTIVOS = {
    "missing": "falta",
    "string_too_short": "es demasiado corto",
    "string_too_long": "es demasiado largo",
    "string_pattern_mismatch": "no tiene el formato esperado",
    "greater_than": "es demasiado pequeño",
    "greater_than_equal": "es demasiado pequeño",
    "less_than": "es demasiado grande",
    "less_than_equal": "es demasiado grande",
    "int_parsing": "tiene que ser un número entero",
    "float_parsing": "tiene que ser un número",
    "bool_parsing": "tiene que ser sí o no",
    "datetime_parsing": "no es una fecha válida",
    "datetime_from_date_parsing": "no es una fecha válida",
    "uuid_parsing": "no es un identificador válido",
    "value_error": "no es válido",
    "enum": "no es uno de los valores admitidos",
    "extra_forbidden": "sobra",
}


@app.exception_handler(RequestValidationError)
async def manejar_cuerpo_invalido(_: Request, error: RequestValidationError) -> JSONResponse:
    """Un cuerpo que no cumple el esquema **también** sale con la forma única del error.

    FastAPI responde a esto con `{"detail": [ … ]}`, que no se parece en nada al
    `{"error": {"codigo", "mensaje"}}` del resto de la API. La consecuencia no es estética: cada
    pantalla acaba escribiendo `datos?.error?.mensaje ?? datos?.detail?.[0]?.msg ?? '…'`, y la que
    se olvida de la segunda mitad enseña «undefined» o un mensaje genérico donde había uno bueno.

    El mensaje se compone en castellano y nombrando el campo, porque el `msg` de Pydantic viene en
    inglés y con el nombre técnico dentro: «String should have at least 10 characters» no es algo
    que se le pueda enseñar a nadie.
    """
    fallos = error.errors()
    campos = []
    campos_afectados = []
    for fallo in fallos:
        # `loc` es ('body', 'contrasena') o ('query', 'desde'); interesa el último tramo.
        nombre = next((str(t) for t in reversed(fallo.get("loc", ())) if isinstance(t, str)), "")
        if nombre in {"body", "query", "path", "header"}:
            nombre = ""
        motivo = _MOTIVOS.get(str(fallo.get("type", "")), "no es válido")
        campos.append(f"«{nombre}» {motivo}" if nombre else motivo)
        if nombre:
            campos_afectados.append(nombre)

    mensaje = "Revisa los datos: " + ", ".join(campos) + "." if campos else "Revisa los datos."
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "codigo": "CUERPO_INVALIDO",
                "mensaje": mensaje,
                # Los nombres de los campos, para poder marcarlos en el formulario. Se dan como
                # lista de nombres y no como la tupla cruda de Pydantic: `"('body', 'contrasena')"`
                # obliga a quien lo recibe a partir una cadena para volver a tener lo que ya
                # teníamos aquí.
                "detalles": {"campos": campos_afectados},
            }
        },
    )


#: `SQLSTATE 42501` — «permiso insuficiente». Es lo que devuelve PostgreSQL cuando una fila
#: no pasa el `WITH CHECK` de una política de seguridad por fila.
PERMISO_INSUFICIENTE = "42501"

#: `SQLSTATE 40P01` — abrazo mortal. Con diez intentos simultáneos por la misma hora la base
#: detecta el bloqueo mutuo y mata a una transacción; medido, no supuesto.
ABRAZO_MORTAL = "40P01"


@app.exception_handler(DBAPIError)
async def manejar_rechazo_de_la_base(_: Request, error: DBAPIError) -> JSONResponse:
    """Traduce el «no puedes» de PostgreSQL a la forma única del error.

    Cuando un profesional intenta escribir donde no le toca, quien lo impide es una política
    restrictiva de la base (migración 0006), no un `if`. Eso es exactamente lo que se quiere
    —el olvido de un endpoint nuevo no tiene consecuencias— pero el error que sale es un
    `ProgrammingError` de asyncpg, que ni el cliente entiende ni se debe enseñar.

    Se traduce **solo** el `42501`. Cualquier otro error de base sube tal cual: significa algo
    que no habíamos previsto, y convertirlo en un 403 educado lo escondería durante meses.
    """
    codigo = getattr(getattr(error, "orig", None), "sqlstate", None)

    # El abrazo mortal se traduce a «vuelve a intentarlo» y **no** a «esa hora está ocupada»:
    # que dos escrituras se crucen no demuestra que el hueco esté cogido. Antes subía tal cual y
    # salía un 500 en la pantalla desde la que se reserva.
    if codigo == ABRAZO_MORTAL or ABRAZO_MORTAL in str(error):
        carrera = CarreraEnLaBase(
            "Alguien más estaba reservando en ese mismo instante. Vuelve a intentarlo."
        )
        return JSONResponse(status_code=carrera.estado_http, content=carrera.como_respuesta())

    if codigo != PERMISO_INSUFICIENTE and PERMISO_INSUFICIENTE not in str(error):
        raise error

    negado = NoAutorizado("No tienes permiso para hacer eso en este negocio.")
    return JSONResponse(status_code=negado.estado_http, content=negado.como_respuesta())


@app.exception_handler(StaleDataError)
async def manejar_escritura_sin_efecto(_: Request, error: StaleDataError) -> JSONResponse:
    """El `UPDATE` que no tocó ninguna fila porque la política de la base lo escondió.

    Es el fallo más traicionero de la seguridad por fila y merece explicarse: cuando una
    política deja **leer** pero no **escribir**, el `UPDATE` no da error — sencillamente no
    encuentra la fila—. El ORM, que sí esperaba tocar una, revienta con `StaleDataError`, y sin
    esto el usuario ve un 500 en vez de un «no tienes permiso».

    Los endpoints que lo pueden provocar comprueban además el rol antes de escribir, así que a
    esto se llega solo cuando alguien añade uno nuevo y se olvida. Que entonces salga un 403
    claro en vez de un 500 es la diferencia entre un fallo que se entiende y uno que se
    investiga.
    """
    del error
    negado = NoAutorizado("No tienes permiso para cambiar eso en este negocio.")
    return JSONResponse(status_code=negado.estado_http, content=negado.como_respuesta())


# El panel del negocio corre en el navegador y habla con esta API desde otro origen. La lista
# es **explícita y sale de configuración**: un `*` aquí, combinado con credenciales, es la
# forma más rápida de regalar las sesiones de todo el mundo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ajustes.origenes_permitidos.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    # `Idempotency-Key` tiene que estar o el reintento de la app se convierte en una petición
    # sin clave, que es exactamente la que crea la segunda cita.
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

# El orden es el de las audiencias del contrato (ADR-0012): primero entrar, después lo
# público, después el negocio y por último la persona. La consola va **la última y aparte**:
# no comparte prefijo, ni dependencia de sesión, ni rol de base de datos con ninguna de ellas.
app.include_router(acceso.router)
# Aceptar una invitación se hace **antes** de estar dentro de ningún negocio, así que va
# con las de entrar y no con las del panel (punto 4 del encargo).
app.include_router(invitaciones.router)
app.include_router(publico.router)
app.include_router(publico_profesionales.router)
app.include_router(publico_mapa.router)
app.include_router(onboarding.router)
app.include_router(negocio.router)
app.include_router(negocio_catalogo.router)
app.include_router(negocio_equipo.router)
app.include_router(negocio_agenda.router)
app.include_router(negocio_ficha.router)
app.include_router(negocio_clientes.router)
app.include_router(negocio_dueno.router)
app.include_router(negocio_miembros.router)
app.include_router(mi_telefono.router)
app.include_router(cliente.router)
app.include_router(profesional.router)
app.include_router(perfil_profesional.router)
app.include_router(favoritos.router)
app.include_router(resenas.router)
app.include_router(consola.router)


@app.get("/salud", tags=["operación"], summary="Comprueba que el proceso responde")
async def salud() -> JSONResponse:
    return JSONResponse({"estado": "ok", "entorno": ajustes.entorno})
