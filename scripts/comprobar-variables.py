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
MARCA = RAIZ / "apps/web/lib/marca.ts"
CODIGO_WEB = (RAIZ / "apps/web/app", RAIZ / "apps/web/componentes", RAIZ / "apps/web/lib")


def variables() -> set[str]:
    """Los campos de la clase de ajustes. `model_config` no es una variable de entorno."""
    texto = AJUSTES.read_text()
    return {
        nombre
        for nombre in re.findall(r"^\s{4}(\w+):\s", texto, re.M)
        if not nombre.startswith("_") and nombre != "model_config"
    }


def nombre_comercial() -> str:
    """El codename que hay hoy en `lib/marca.ts`, sacado de su valor por defecto."""
    encontrado = re.search(r"\?\?\s*['\"](\w+)['\"]", MARCA.read_text())
    return encontrado.group(1) if encontrado else ""


def nombre_a_fuego() -> list[str]:
    """Dónde está escrito el nombre comercial en vez de salir de la configuración.

    El nombre está **sin decidir** (D1): «Bukeo» es codename y las tres direcciones de marca
    traen el suyo. La regla escrita es que salga de configuración y que cambiarlo no toque ni
    una pantalla; lo que había era la regla en un documento y el nombre repetido en dieciséis
    sitios —el pie, los términos, la privacidad, «cómo funciona»—, que es exactamente el fallo
    que el propio tablero de deuda anunciaba: «si aparece escrito a fuego en algún sitio, es un
    fallo de QA». Esto lo vuelve comprobable.
    """
    nombre = nombre_comercial()
    if not nombre:
        return ["apps/web/lib/marca.ts ya no declara un nombre por defecto"]
    culpables = []
    for carpeta in CODIGO_WEB:
        for archivo in sorted(carpeta.rglob("*.ts*")):
            if archivo == MARCA:
                continue
            for numero, linea in enumerate(archivo.read_text().splitlines(), 1):
                # Sin distinguir mayúsculas: el codename se coló en minúscula dentro de
                # `bukeo.com` —el enlace que el panel le daba al salón para su Instagram— y una
                # comparación exacta lo dejaba pasar.
                if nombre.lower() in linea.lower():
                    culpables.append(f"{archivo.relative_to(RAIZ)}:{numero}")
    return culpables


def main() -> int:
    declaradas = variables()
    fallos = []

    for archivo in (EJEMPLO, INVENTARIO):
        contenido = archivo.read_text().upper()
        ausentes = sorted(v for v in declaradas if v.upper() not in contenido)
        if ausentes:
            fallos.append(f"{archivo.relative_to(RAIZ)}: faltan {', '.join(ausentes)}")

    a_fuego = nombre_a_fuego()
    if a_fuego:
        fallos.append(
            f"el nombre comercial «{nombre_comercial()}» está escrito a fuego en "
            + ", ".join(a_fuego)
        )

    print(f"{len(declaradas)} variables declaradas en ajustes.py")
    if fallos:
        print("\nHAY QUE ARREGLAR:")
        for fallo in fallos:
            print(f" · {fallo}")
        print("\nLas variables se documentan en los dos sitios: nombre y para qué sirve,")
        print("nunca el valor. El nombre comercial sale de `lib/marca.ts`, de ningún sitio más.")
        return 1

    print("Todas están en .env.example y en el inventario de secretos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
