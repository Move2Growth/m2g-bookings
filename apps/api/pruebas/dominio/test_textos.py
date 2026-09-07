"""Slugs y usuarios de red: lo que acaba en una URL pública.

El caso que justifica este módulo entero es el de la red social. El encargo dice «se guarda el
usuario, no la URL», y la razón no es de estilo: un campo de enlace libre en un perfil público
es un sitio donde cualquiera cuelga lo que quiera. Aquí se comprueba que de las tres formas en
que la gente rellena ese campo sale lo mismo, y que una dirección de otro dominio **no entra**.
"""

from __future__ import annotations

import pytest

from agenda.dominio.textos import TextoInvalido, slug_desde, url_de_red, usuario_de_red


class TestSlug:
    def test_translitera_tildes_y_ene_en_vez_de_tirarlas(self):
        """«Marielys Peña» → `marielys-pena`. Nunca `marielys-pe-a`.

        Es una URL que se comparte por WhatsApp: que salga rota es permanente.
        """
        assert slug_desde("Marielys Peña") == "marielys-pena"
        assert slug_desde("Ana Lucía Ábrego") == "ana-lucia-abrego"
        assert slug_desde("Génesis Batista") == "genesis-batista"

    def test_colapsa_lo_que_no_es_letra_ni_numero(self):
        assert slug_desde("  Dra.  Marisol   Tejeira  ") == "dra-marisol-tejeira"
        assert slug_desde("Nails & Lashes") == "nails-lashes"

    def test_un_nombre_sin_una_sola_letra_no_deja_un_slug_vacio(self):
        """Un slug vacío haría una URL que apunta a la lista, no a la persona."""
        assert slug_desde("???") == "profesional"
        assert slug_desde("???", por_defecto="negocio") == "negocio"


class TestUsuarioDeRed:
    @pytest.mark.parametrize(
        "valor",
        [
            "yaris.nails",
            "@yaris.nails",
            "https://instagram.com/yaris.nails",
            "https://www.instagram.com/yaris.nails/",
            "www.instagram.com/yaris.nails",
        ],
    )
    def test_las_cinco_formas_de_escribirlo_dan_el_mismo_usuario(self, valor):
        """Se acepta lo que la gente pega de verdad, y de todo sale el usuario pelado."""
        assert usuario_de_red("instagram", valor) == "yaris.nails"

    def test_una_direccion_de_otro_dominio_no_entra(self):
        """El motivo de que se guarde el usuario y no la URL, en una prueba.

        Si se guardara la cadena tal cual, este valor acabaría siendo un enlace saliente desde
        un perfil público de Bukeo, y no hay forma de validarlo mirando una cadena arbitraria.
        """
        with pytest.raises(TextoInvalido):
            usuario_de_red("instagram", "https://sitio-cualquiera.com/promo")
        with pytest.raises(TextoInvalido):
            usuario_de_red("x", "https://instagram.com/yaris")

    def test_una_ruta_que_no_es_un_perfil_tampoco(self):
        with pytest.raises(TextoInvalido):
            usuario_de_red("facebook", "https://facebook.com/groups/algo")

    def test_un_usuario_con_caracteres_que_no_caben_se_rechaza(self):
        """X no admite puntos; Instagram no admite barras. El patrón lo corta."""
        with pytest.raises(TextoInvalido):
            usuario_de_red("x", "yaris.nails")
        with pytest.raises(TextoInvalido):
            usuario_de_red("instagram", "yaris/nails")

    def test_vacio_significa_borrar_el_enlace(self):
        assert usuario_de_red("instagram", "") is None
        assert usuario_de_red("instagram", "   ") is None
        assert usuario_de_red("instagram", None) is None

    def test_la_direccion_se_compone_al_servir_y_apunta_al_dominio_correcto(self):
        assert url_de_red("instagram", "yaris.nails") == "https://instagram.com/yaris.nails"
        assert url_de_red("x", "josuecamano") == "https://x.com/josuecamano"
        assert url_de_red("facebook", None) is None
