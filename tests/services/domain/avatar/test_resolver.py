"""
Testes de resolver_imagem_perfil (SPEC user_admin/006): a escolha entre foto e avatar gerado,
domínio puro que compõe o AvatarIniciaisSvg sem depender de Django nem instanciar DTO à parte.
"""

from xml.etree import ElementTree

from services.domain.avatar import resolver_imagem_perfil

_SVG_NS = {"svg": "http://www.w3.org/2000/svg"}


def test_resolver_devolve_a_foto_quando_ha_foto_url() -> None:
    resultado = resolver_imagem_perfil(
        nome="João",
        sobrenome="Silva",
        cor_fundo="#123456",
        cor_tinta="#ffffff",
        foto_url="/media/perfis/fotos/joao.jpg",
    )

    assert resultado.tipo == "foto"
    assert resultado.valor == "/media/perfis/fotos/joao.jpg"


def test_resolver_gera_avatar_quando_nao_ha_foto() -> None:
    resultado = resolver_imagem_perfil(
        nome="João",
        sobrenome="Silva",
        cor_fundo="#123456",
        cor_tinta="#ffffff",
        foto_url=None,
    )

    assert resultado.tipo == "avatar"
    raiz = ElementTree.fromstring(resultado.valor)
    assert raiz.find("svg:text", _SVG_NS).text == "JS"  # type: ignore[union-attr]
