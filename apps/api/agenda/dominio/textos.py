"""Texto que acaba en una URL pública o en un perfil: slugs y usuarios de red social.

Es dominio puro —ni base de datos ni FastAPI— porque lo usan tres sitios que no se conocen
entre sí: el alta del negocio, el alta del profesional y la edición de su perfil. Tenerlo
duplicado sería la forma más silenciosa de que el slug del negocio transliterara las tildes y
el del profesional no.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urlparse

#: Cómo se llama cada red por dentro. La clave es el nombre de la columna en `staff_profiles`.
#:
#: **Se guarda el usuario, nunca la URL.** Una URL entera en un perfil público es un enlace
#: libre a cualquier sitio metido desde un formulario, y no hay forma de comprobar «que sea de
#: Instagram» mirando una cadena arbitraria. Guardando el usuario, la URL la compone quien
#: pinta y siempre apunta al dominio correcto.
REDES: dict[str, dict[str, object]] = {
    "instagram": {
        # Instagram: letras, números, punto y guion bajo, hasta 30.
        "patron": re.compile(r"^[A-Za-z0-9._]{1,30}$"),
        "hosts": ("instagram.com", "www.instagram.com", "m.instagram.com"),
        "url": "https://instagram.com/{usuario}",
    },
    "facebook": {
        # Facebook permite punto en el nombre de página y nombres largos.
        "patron": re.compile(r"^[A-Za-z0-9.]{1,50}$"),
        "hosts": (
            "facebook.com",
            "www.facebook.com",
            "m.facebook.com",
            "web.facebook.com",
            "fb.com",
            "www.fb.com",
        ),
        "url": "https://facebook.com/{usuario}",
    },
    "x": {
        # X (antes Twitter): solo letras, números y guion bajo, hasta 15. Sin punto.
        "patron": re.compile(r"^[A-Za-z0-9_]{1,15}$"),
        "hosts": (
            "x.com",
            "www.x.com",
            "twitter.com",
            "www.twitter.com",
            "mobile.twitter.com",
        ),
        "url": "https://x.com/{usuario}",
    },
}


class TextoInvalido(ValueError):
    """El valor no sirve para lo que se pidió. Quien llama lo traduce a error de la API."""


def slug_desde(nombre: str, *, por_defecto: str = "profesional") -> str:
    """URL amigable a partir de un nombre propio.

    Las tildes y la eñe **se transliteran, no se tiran**: «Marielys Ruiz Peña» tiene que dar
    `marielys-ruiz-pena` y no `marielys-ruiz-pe-a`. Es una URL que se comparte por WhatsApp y
    se pega en la bio de Instagram; que salga rota es una primera impresión mala y permanente.
    """
    sin_tildes = (
        unicodedata.normalize("NFKD", nombre.replace("ñ", "n").replace("Ñ", "N"))
        .encode("ascii", "ignore")
        .decode()
    )
    limpio = re.sub(r"[^a-z0-9]+", "-", sin_tildes.lower().strip())
    return re.sub(r"-+", "-", limpio).strip("-") or por_defecto


def usuario_de_red(red: str, valor: str | None) -> str | None:
    """Normaliza lo que alguien escribió en el campo de una red social **a su usuario**.

    Se aceptan las tres formas en que la gente rellena de verdad ese campo —`yaris.nails`,
    `@yaris.nails` y la URL copiada del navegador— y de las tres sale lo mismo. Lo que no se
    acepta es una URL de **otro** dominio: ahí es donde un perfil público se convierte en un
    tablón de anuncios ajeno.

    Devuelve `None` cuando el campo se manda vacío, que es como se borra un enlace.
    """
    if red not in REDES:
        raise TextoInvalido(f"«{red}» no es una red social conocida.")
    if valor is None:
        return None

    limpio = valor.strip()
    if not limpio:
        return None

    if "://" in limpio or limpio.lower().startswith("www."):
        limpio = _usuario_desde_url(red, limpio)

    limpio = limpio.lstrip("@").strip("/")
    # Un usuario no lleva parámetros: si quedaron, lo que pegaron no era un perfil.
    if any(caracter in limpio for caracter in "?#/ "):
        raise TextoInvalido(f"«{valor}» no parece un usuario de {red}.")

    patron: re.Pattern[str] = REDES[red]["patron"]  # type: ignore[assignment]
    if not patron.match(limpio):
        raise TextoInvalido(
            f"«{valor}» no parece un usuario de {red}. Escribe solo el usuario, sin la dirección."
        )
    return limpio


def _usuario_desde_url(red: str, valor: str) -> str:
    """Saca el usuario de una URL, **comprobando antes que el dominio sea el de esa red**."""
    crudo = valor if "://" in valor else f"https://{valor}"
    partes = urlparse(crudo)
    hosts: tuple[str, ...] = REDES[red]["hosts"]  # type: ignore[assignment]
    if (partes.hostname or "").lower() not in hosts:
        raise TextoInvalido(
            f"Esa dirección no es de {red}. Escribe solo el usuario, sin la dirección."
        )
    # `/yaris.nails/` → `yaris.nails`; una ruta con más de un tramo no es un perfil.
    tramos = [tramo for tramo in partes.path.split("/") if tramo]
    if len(tramos) != 1:
        raise TextoInvalido(f"Esa dirección no apunta a un perfil de {red}.")
    return tramos[0]


def url_de_red(red: str, usuario: str | None) -> str | None:
    """La dirección que se pinta, compuesta al servir. Nunca se guarda."""
    if not usuario or red not in REDES:
        return None
    plantilla: str = REDES[red]["url"]  # type: ignore[assignment]
    return plantilla.format(usuario=usuario)
