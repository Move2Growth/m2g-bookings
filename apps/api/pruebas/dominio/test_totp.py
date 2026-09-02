"""El segundo factor de la consola, contra los **vectores de prueba del RFC 6238**.

Esta es la prueba que justifica que TOTP esté escrito a mano en vez de traído en una
dependencia: los vectores son públicos y están en el apéndice B del RFC, así que si la
implementación se desviara del estándar —y por tanto ninguna aplicación de autenticación del
mundo funcionaría con ella— esto lo diría antes de salir del portátil.

Los vectores del RFC son de ocho dígitos y aquí se generan de seis. No es una adaptación
libre: el truncamiento produce un entero de 31 bits y los dígitos salen de `% 10**n`, así que
los seis dígitos son literalmente los seis últimos del vector de ocho.
"""

from __future__ import annotations

from agenda.dominio import totp

#: El secreto del apéndice B del RFC 6238 para SHA-1: los veinte bytes ASCII «1234567890»
#: repetidos hasta llenar.
SECRETO_DEL_RFC = b"12345678901234567890"

#: Instante → código de ocho dígitos publicado en el RFC. Se compara con los seis últimos.
VECTORES_DEL_RFC = {
    59: "94287082",
    1111111109: "07081804",
    1111111111: "14050471",
    1234567890: "89005924",
    2000000000: "69279037",
    20000000000: "65353130",
}


def test_los_codigos_coinciden_con_los_vectores_del_rfc():
    """Si esto falla, ningún autenticador del mundo podría entrar en la consola."""
    for momento, esperado in VECTORES_DEL_RFC.items():
        assert totp.codigo(SECRETO_DEL_RFC, momento=momento) == esperado[-6:], (
            f"En t={momento} el RFC dice {esperado[-6:]} y salió "
            f"{totp.codigo(SECRETO_DEL_RFC, momento=momento)}."
        )


def test_el_codigo_de_la_ventana_actual_vale():
    assert totp.verificar(SECRETO_DEL_RFC, "287082", momento=59)


def test_se_acepta_el_desfase_de_reloj_de_una_ventana():
    """El teléfono de quien entra no está sincronizado con el servidor.

    Sin margen, el 2FA falla de forma intermitente y aleatoria, que es la peor manera de fallar
    que existe: nadie sabe si escribió mal el código o si el sistema está roto.
    """
    codigo = totp.codigo(SECRETO_DEL_RFC, momento=1111111109)
    assert totp.verificar(SECRETO_DEL_RFC, codigo, momento=1111111109 + totp.PASO_SEGUNDOS)
    assert totp.verificar(SECRETO_DEL_RFC, codigo, momento=1111111109 - totp.PASO_SEGUNDOS)


def test_fuera_del_margen_ya_no_vale():
    """Un código de hace dos minutos **no entra**: si entrara, no sería de un solo uso."""
    codigo = totp.codigo(SECRETO_DEL_RFC, momento=1111111109)
    assert not totp.verificar(SECRETO_DEL_RFC, codigo, momento=1111111109 + 120)


def test_lo_que_no_es_seis_digitos_se_rechaza_sin_calcular_nada():
    for basura in ("", "abcdef", "12345", "1234567", "12 34 56 78"):
        assert not totp.verificar(SECRETO_DEL_RFC, basura, momento=59)


def test_el_secreto_se_puede_meter_en_un_autenticador():
    """Base32 **sin relleno**: con los `=` dentro, algunas aplicaciones lo rechazan."""
    secreto = totp.secreto_nuevo()
    en_base32 = totp.como_base32(secreto)

    assert "=" not in en_base32
    assert totp.desde_base32(en_base32) == secreto

    uri = totp.uri_de_provisionamiento(secreto, cuenta="admin@m2g.dev", emisor="Bukeo")
    assert uri.startswith("otpauth://totp/Bukeo:admin@m2g.dev?")
    assert f"secret={en_base32}" in uri


def test_cada_secreto_nuevo_es_distinto():
    """Veinte bytes de un generador criptográfico, no de `random`."""
    secretos = {totp.secreto_nuevo() for _ in range(50)}
    assert len(secretos) == 50
    assert all(len(s) == 20 for s in secretos)
