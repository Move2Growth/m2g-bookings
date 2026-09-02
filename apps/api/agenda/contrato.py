"""Vuelca el contrato de la API a la salida estándar. `python -m agenda.contrato`.

Es lo que consume `make contrato` para escribir `packages/api-types/openapi.json` y, de ahí,
generar los tipos TypeScript de la web, del back-office y de la app.

**Se genera sin levantar el servidor a propósito.** La alternativa —arrancar la API y hacerle
un `curl` a `/api/v1/openapi.json`— obliga a tener la base de datos en pie para regenerar un
fichero de texto, y eso convierte «actualizar los tipos» en un trámite que la gente se salta.
Aquí solo se importa la aplicación y se le pide su esquema.

El fichero se commitea (ver `packages/api-types/README.md`): tenerlo en el repositorio hace que
un cambio de contrato **se vea en el diff** de la revisión. Si un campo desaparece o cambia de
tipo, aparece en el commit y alguien lo mira, en vez de enterarse en producción.
"""

from __future__ import annotations

import json
import sys

from agenda.main import app


def contrato() -> dict:
    """El OpenAPI de la aplicación, tal cual lo publica FastAPI."""
    return app.openapi()


def principal() -> None:
    # `ensure_ascii=False` porque las descripciones están en español y llevan tildes: con el
    # escapado por defecto el fichero se llena de `ó` y el diff deja de poder leerse.
    # `sort_keys=True` para que dos generaciones seguidas den byte a byte lo mismo y el diff
    # solo enseñe lo que de verdad cambió.
    json.dump(contrato(), sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    principal()
