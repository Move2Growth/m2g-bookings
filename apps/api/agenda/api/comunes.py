"""Piezas que comparten varios routers y que no son de ninguno en particular.

Aquí **no** va nada que decida qué se puede ver: eso vive en las dependencias de sesión y en
las políticas de la base. Lo que hay aquí es de pintar.
"""

from __future__ import annotations

from agenda.ajustes import obtener_ajustes

ajustes = obtener_ajustes()


def url_de_media(clave: str | None) -> str | None:
    """Convierte la clave guardada en una URL que el navegador puede pedir.

    `business_media.storage_key` guarda **una clave**, no una URL firmada, y el motivo está en
    el modelo de datos: las URL firmadas caducan, y guardarlas obligaría a reescribir filas
    cada vez. La URL se compone al servir.

    Tres casos y en este orden:

    * Ya es absoluta (`https://…`) → se devuelve tal cual. Es lo que pasa cuando el salón pega
      el enlace de una foto que ya tiene publicada en otro sitio.
    * Empieza por `/` → también tal cual. Hoy es el caso normal en local: las fotos las sirve
      la propia web desde `public/`, así que `/fotos/spa.webp` funciona sin almacenamiento de
      objetos y sin inventarse un servidor de imágenes que todavía no hace falta.
    * Cualquier otra cosa → se le antepone `URL_BASE_MEDIA`. El día que entre el almacenamiento
      de objetos se rellena esa variable y **no se toca ni una fila ni una pantalla**.
    """
    if not clave:
        return None
    if clave.startswith(("http://", "https://", "/")):
        return clave
    base = ajustes.url_base_media.rstrip("/")
    return f"{base}/{clave}" if base else f"/{clave}"
