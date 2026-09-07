"""Comprueba que **toda** variable de configuración está documentada en los dos sitios.

    python3 scripts/comprobar-variables.py

La regla de la casa es que un secreto o una variable nueva se documenta **en la misma sesión**
en `.env.example` y en `docs/operacion/SECRETOS-Y-VARIABLES.md`. Una regla que solo vive en un
documento se rompe sin que nadie se entere; esto la vuelve comprobable.

Se descubrió que hacía falta contando: había **siete** variables en `ajustes.py` que no estaban
en el inventario y **cinco** que no estaban en el ejemplo, y ninguna era reciente.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
AJUSTES = RAIZ / "apps/api/agenda/ajustes.py"
EJEMPLO = RAIZ / ".env.example"
INVENTARIO = RAIZ / "docs/operacion/SECRETOS-Y-VARIABLES.md"


def variables() -> set[str]:
    """Los campos de la clase de ajustes. `model_config` no es una variable de entorno."""
    texto = AJUSTES.read_text()
    return {
        nombre
        for nombre in re.findall(r"^\s{4}(\w+):\s", texto, re.M)
        if not nombre.startswith("_") and nombre != "model_config"
    }


def main() -> int:
    declaradas = variables()
    fallos = []

    for archivo in (EJEMPLO, INVENTARIO):
        contenido = archivo.read_text().upper()
        ausentes = sorted(v for v in declaradas if v.upper() not in contenido)
        if ausentes:
            fallos.append(f"{archivo.relative_to(RAIZ)}: faltan {', '.join(ausentes)}")

    print(f"{len(declaradas)} variables declaradas en ajustes.py")
    if fallos:
        print("\nSIN DOCUMENTAR:")
        for fallo in fallos:
            print(f" · {fallo}")
        print("\nSe documentan en los dos sitios: nombre y para qué sirve, nunca el valor.")
        return 1

    print("Todas están en .env.example y en el inventario de secretos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
