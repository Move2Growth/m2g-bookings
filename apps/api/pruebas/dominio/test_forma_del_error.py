"""Todos los errores de la API salen con la misma forma, también los de validación.

FastAPI responde a un cuerpo que no cumple el esquema con `{"detail": [ … ]}`, que no se parece
en nada al `{"error": {"codigo", "mensaje"}}` del resto. La consecuencia no es estética: cada
pantalla acababa escribiendo `datos?.error?.mensaje ?? datos?.detail?.[0]?.msg ?? '…'`, y la que
se olvidaba de la segunda mitad enseñaba «undefined» donde había un mensaje bueno.

Se prueba con el cliente de FastAPI y no contra la base, porque lo que se comprueba es el
manejador de excepciones y no ninguna consulta.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from agenda.main import app

cliente = TestClient(app, raise_server_exceptions=False)


def test_un_cuerpo_invalido_sale_con_la_forma_unica():
    respuesta = cliente.post("/api/v1/auth/registrar", json={"correo": "x", "contrasena": "corta"})

    assert respuesta.status_code == 422
    cuerpo = respuesta.json()
    assert "detail" not in cuerpo, (
        "El formato de FastAPI no puede salir a la calle: obliga a cada pantalla a sostener dos "
        "formatos de error a la vez."
    )
    assert cuerpo["error"]["codigo"] == "CUERPO_INVALIDO"


def test_el_mensaje_va_en_castellano_y_nombra_el_campo():
    """«String should have at least 10 characters» no se le puede enseñar a nadie."""
    respuesta = cliente.post("/api/v1/auth/registrar", json={"correo": "x", "contrasena": "corta"})
    mensaje = respuesta.json()["error"]["mensaje"]

    assert "contrasena" in mensaje
    assert "demasiado corto" in mensaje
    assert "String should" not in mensaje


def test_los_campos_vienen_como_nombres_y_no_como_tuplas():
    """Para poder marcar el campo en el formulario sin partir una cadena."""
    respuesta = cliente.post("/api/v1/auth/registrar", json={"correo": "x", "contrasena": "corta"})
    campos = respuesta.json()["error"]["detalles"]["campos"]

    assert campos == ["nombre", "contrasena"]


def test_un_error_de_dominio_sigue_saliendo_igual_que_antes():
    """El manejador nuevo no puede haberse comido el que ya había."""
    respuesta = cliente.post(
        "/api/v1/auth/entrar",
        json={"correo": "no-existe@demo.pa", "contrasena": "una contrasena larga"},
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["codigo"] == "CREDENCIALES_INVALIDAS"
