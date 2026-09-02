"""Códigos de un solo uso basados en el tiempo (RFC 6238), para el 2FA de la consola.

Está escrito a mano y con la biblioteca estándar, y conviene decir por qué antes de que
alguien lo tome por atrevimiento: **aquí no se inventa criptografía**. TOTP es HMAC-SHA1 sobre
el número de ventana, con el truncamiento dinámico que el RFC especifica byte a byte; los
primitivos son los de `hmac` y `hashlib`, que son los mismos que usaría cualquier biblioteca.
Lo que se evita es añadir una dependencia más al despliegue para veinte líneas que el propio
RFC publica con **vectores de prueba**, y esos vectores están en las pruebas: si esto se
desviara del estándar, ninguna aplicación de autenticación del mundo funcionaría y la prueba
lo diría antes de salir.

Dos detalles que no son opcionales:

* **La comparación es en tiempo constante** (`hmac.compare_digest`). Comparar con `==` filtra
  por el tiempo de respuesta cuántos dígitos iniciales acertaste.
* **Se acepta una ventana de margen** hacia atrás y hacia delante. El reloj del teléfono de
  quien entra no está sincronizado con el del servidor, y sin margen el 2FA falla de forma
  intermitente y aleatoria, que es la peor manera de fallar que existe.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time

#: Cada cuántos segundos cambia el código. Treinta es lo que asume toda aplicación de
#: autenticación; cambiarlo obliga a que la gente reconfigure su móvil.
PASO_SEGUNDOS = 30

#: Cuántos pasos de margen se aceptan a cada lado. Uno = ±30 s de desfase de reloj tolerado.
VENTANAS_DE_MARGEN = 1

DIGITOS = 6


def secreto_nuevo() -> bytes:
    """Veinte bytes al azar de un generador criptográfico, que es lo que pide el RFC."""
    return secrets.token_bytes(20)


def como_base32(secreto: bytes) -> str:
    """El secreto tal como se teclea o se mete en un QR, sin el relleno `=`.

    Las aplicaciones de autenticación esperan base32 sin relleno; con los `=` dentro, algunas
    lo aceptan y otras no, y descubrir cuál es cuál es una tarde perdida.
    """
    return base64.b32encode(secreto).decode().rstrip("=")


def desde_base32(texto: str) -> bytes:
    relleno = "=" * (-len(texto) % 8)
    return base64.b32decode(texto.upper() + relleno)


def uri_de_provisionamiento(secreto: bytes, *, cuenta: str, emisor: str) -> str:
    """La URI `otpauth://` que se convierte en QR. **Lleva el secreto dentro.**

    No se guarda, no se registra y no se devuelve dos veces: se enseña una vez, en el momento
    de dar de alta la cuenta, y quien la reciba tiene el segundo factor entero.
    """
    return (
        f"otpauth://totp/{emisor}:{cuenta}"
        f"?secret={como_base32(secreto)}&issuer={emisor}&algorithm=SHA1"
        f"&digits={DIGITOS}&period={PASO_SEGUNDOS}"
    )


def codigo(secreto: bytes, *, momento: float | None = None, paso: int = PASO_SEGUNDOS) -> str:
    """El código de la ventana en la que cae `momento`. Es HOTP sobre el contador de tiempo."""
    contador = int((momento if momento is not None else time.time()) // paso)
    return _hotp(secreto, contador)


def verificar(
    secreto: bytes,
    entregado: str,
    *,
    momento: float | None = None,
    margen: int = VENTANAS_DE_MARGEN,
) -> bool:
    """Comprueba el código aceptando el desfase de reloj razonable, en tiempo constante."""
    limpio = (entregado or "").strip().replace(" ", "")
    if not limpio.isdigit() or len(limpio) != DIGITOS:
        return False

    ahora = momento if momento is not None else time.time()
    contador = int(ahora // PASO_SEGUNDOS)
    # Se recorren **todas** las ventanas sin cortocircuito: salir en cuanto una acierta haría
    # que el tiempo de respuesta contara cuál acertó, que es una fuga pequeña pero gratuita de
    # evitar.
    valido = False
    for desplazamiento in range(-margen, margen + 1):
        if hmac.compare_digest(_hotp(secreto, contador + desplazamiento), limpio):
            valido = True
    return valido


def _hotp(secreto: bytes, contador: int) -> str:
    """HOTP (RFC 4226): HMAC-SHA1 del contador en ocho bytes, y truncamiento dinámico.

    El truncamiento es la parte que parece magia y no lo es: el último medio byte del HMAC dice
    **desde dónde** leer cuatro bytes; de esos cuatro se quita el bit de signo y el resto entre
    un millón son los seis dígitos. Está así en el RFC para que el resultado no dependa de si
    la máquina interpreta el entero con signo o sin él.
    """
    digest = hmac.new(secreto, struct.pack(">Q", contador), hashlib.sha1).digest()
    desplazamiento = digest[-1] & 0x0F
    (troceado,) = struct.unpack(">I", digest[desplazamiento : desplazamiento + 4])
    return f"{(troceado & 0x7FFFFFFF) % (10**DIGITOS):0{DIGITOS}d}"
