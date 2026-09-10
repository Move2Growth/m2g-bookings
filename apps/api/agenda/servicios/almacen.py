"""Dónde viven las fotos, y cómo llegan hasta ahí (ADR-0023).

Un salón no puede publicarse sin una foto (D11), y hasta ahora `POST /negocio/fotos` recibía
**una clave** que nadie sabía cómo conseguir: el registro existía y el sitio donde guardar el
archivo, no.

## Las tres decisiones que hay aquí

**El archivo no pasa por la API.** El navegador sube **directo** al almacén con un permiso
firmado y de vida corta. Es el patrón normal de S3 y no es comodidad: una foto de cinco megas
subiendo por una conexión de Panamá ocuparía un trabajador de la API durante un minuto, y con
diez salones a la vez la agenda deja de responder por culpa de unas fotos.

**El permiso lo firma el servidor y lleva sus límites dentro.** Se usa una política de subida
—`POST` firmado— y no una URL de `PUT`, porque la política es lo único que puede **imponer el
tamaño y el tipo antes de que los bytes lleguen**. Con un `PUT` firmado, el tope de cinco megas
sería una promesa del navegador, y el navegador es de quien sube.

**Se guarda la clave, nunca la URL.** Las URL firmadas caducan; guardarlas obligaría a
reescribir filas. La URL se compone al servir, y el día que el cubo cambie de dirección se
cambia una variable.

## La clave lleva el negocio delante

`negocios/{negocio}/{identificador}.{extensión}`. Dos motivos: se puede borrar todo lo de un
salón de una pasada —lo va a pedir la Ley 81— y un listado accidental del cubo no mezcla los
archivos de dos salones. El identificador es un UUID v7, así que **el nombre que trae el
archivo del teléfono no llega nunca al almacén**: ni sus espacios, ni sus tildes, ni el
`../` de alguien con ganas.
"""

from __future__ import annotations

import contextlib
import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import boto3
from botocore.client import Config
from uuid_utils import uuid7

from agenda.ajustes import obtener_ajustes
from agenda.errores import DatoInvalido

_ajustes = obtener_ajustes()

#: Lo que se acepta como foto y con qué extensión se guarda.
#:
#: Es una lista corta a propósito. `image/*` dejaría entrar SVG, que **es un documento con
#: JavaScript dentro**: servido desde el mismo dominio que las fotos, es una puerta abierta.
#: HEIC se queda fuera porque no lo pinta ningún navegador; quien suba desde un iPhone manda
#: JPEG, que es lo que hace el propio iPhone al compartir.
TIPOS: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/avif": "avif",
}


@dataclass(frozen=True)
class PermisoDeSubida:
    """Lo que el navegador necesita para subir, y la clave con la que después se registra."""

    url: str
    campos: dict[str, str]
    clave: str
    caduca_en_segundos: int
    tamano_maximo_bytes: int


@lru_cache(maxsize=1)
def _cliente(publico: bool = False):
    """El cliente de S3. Uno para firmar de cara al navegador y otro para operar desde dentro.

    `signature_version="s3v4"` no es un adorno: sin él, boto firma con la versión antigua y
    los almacenes de hoy —MinIO incluido, según cómo se levante— la rechazan con un error que
    habla de credenciales y no de firmas, que es de los que se buscan una hora en el sitio
    equivocado.
    """
    return boto3.client(
        "s3",
        endpoint_url=_ajustes.s3_endpoint_publico if publico else _ajustes.s3_endpoint,
        region_name=_ajustes.s3_region,
        aws_access_key_id=_ajustes.s3_access_key_id,
        aws_secret_access_key=_ajustes.s3_secret_access_key,
        config=Config(signature_version="s3v4"),
    )


def permiso_de_subida(*, negocio_id: uuid.UUID, tipo: str) -> PermisoDeSubida:
    """Firma un permiso para subir **una** foto de ese negocio.

    El permiso vale para una sola clave, un solo tipo y un solo rango de tamaño. No sirve para
    subir otra cosa después ni para sobrescribir lo de otro salón.
    """
    extension = TIPOS.get(tipo)
    if extension is None:
        raise DatoInvalido(
            "Esa foto no es de un tipo que podamos publicar. Manda un JPG, un PNG o un WebP.",
            tipos=sorted(TIPOS),
        )

    clave = f"negocios/{negocio_id}/{uuid7()}.{extension}"

    firmado: dict[str, Any] = _cliente(publico=True).generate_presigned_post(
        Bucket=_ajustes.s3_bucket,
        Key=clave,
        # `Fields` son los valores que el navegador tiene que reenviar tal cual; `Conditions`
        # es lo que el almacén **comprueba** antes de aceptar un solo byte.
        Fields={"Content-Type": tipo},
        Conditions=[
            {"Content-Type": tipo},
            ["content-length-range", 1, _ajustes.s3_tamano_maximo_bytes],
        ],
        ExpiresIn=_ajustes.s3_permiso_minutos * 60,
    )

    return PermisoDeSubida(
        url=firmado["url"],
        campos=firmado["fields"],
        clave=clave,
        caduca_en_segundos=_ajustes.s3_permiso_minutos * 60,
        tamano_maximo_bytes=_ajustes.s3_tamano_maximo_bytes,
    )


def es_nuestra(clave: str, *, negocio_id: uuid.UUID) -> bool:
    """Si esa clave pertenece a ese negocio.

    Se comprueba al registrar la foto. Sin esto, quien llama a la API podría registrar como
    suya la clave de otro salón —o cualquier cadena— y la ficha enseñaría la foto de otro. La
    clave la da el permiso, pero el que llega por la API es un dato del cliente como cualquier
    otro y se trata igual: sin fiarse.
    """
    return clave.startswith(f"negocios/{negocio_id}/")


def existe(clave: str) -> bool:
    """Si el archivo llegó de verdad al almacén.

    Se pregunta antes de registrar la foto para no dejar una fila apuntando a nada. Una foto
    que existe en la base y no en el almacén es un hueco roto en la ficha de un salón, y nadie
    se entera hasta que un cliente la mira.
    """
    try:
        _cliente().head_object(Bucket=_ajustes.s3_bucket, Key=clave)
        return True
    except Exception:
        return False


def borrar(clave: str) -> None:
    """Quita el archivo. Que falle **no puede** impedir borrar la fila.

    El orden importa y es este a propósito: primero se intenta el archivo, luego se borra la
    fila pase lo que pase. Al revés, un almacén caído dejaría al salón sin poder quitar una
    foto de su ficha, que es exactamente lo que alguien hace con prisa cuando sube la que no
    era. Un archivo huérfano no lo ve nadie; una foto que no se puede quitar, sí.
    """
    # Da igual por qué falle: la fila se borra igual, que es lo que le importa al salón.
    with contextlib.suppress(Exception):
        _cliente().delete_object(Bucket=_ajustes.s3_bucket, Key=clave)
