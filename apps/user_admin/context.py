"""
Contexto das páginas administrativas de servidor (SPEC user_admin/007) e de unidade
(SPEC user_admin/012). Orquestração: traduz o model para o que o template consome — o hex da cor,
a imagem já resolvida pelo domínio e os catálogos dos selects. Nenhuma regra de negócio.
"""

from typing import Any

from apps.mapping.context import contexto_fundo_admin
from apps.user_admin.models import (
    CargoBase,
    CargoComissao,
    Perfil,
    TipoUnidade,
    Unidade,
)
from apps.user_admin.paleta import TINTA_AVATAR, hex_da_cor, tons_da_paleta
from services.domain.avatar import resolver_imagem_perfil


def contexto_criar_perfil() -> dict[str, Any]:
    return (
        contexto_fundo_admin()
        | _catalogos_de_lotacao()
        | _contexto_do_modal_de_unidade()
    )


def contexto_editar_perfil(perfil: Perfil) -> dict[str, Any]:
    cor_unidade_hex = hex_da_cor(perfil.cor_unidade)
    imagem = resolver_imagem_perfil(
        nome=perfil.nome,
        sobrenome=perfil.sobrenome,
        cor_fundo=cor_unidade_hex,
        cor_tinta=TINTA_AVATAR,
        foto_url=_foto_url(perfil),
    )
    return (
        contexto_fundo_admin()
        | _catalogos_de_lotacao()
        | _contexto_do_modal_de_unidade()
        | {
            "perfil": perfil,
            "imagem": imagem,
            "cor_unidade_hex": cor_unidade_hex,
        }
    )


def contexto_criar_unidade() -> dict[str, Any]:
    return (
        contexto_fundo_admin() | _catalogos_de_unidade() | contexto_cor_sugerida(None)
    )


def contexto_cor_sugerida(pai_pk: int | None) -> dict[str, Any]:
    pai = Unidade.objects.filter(pk=pai_pk).first() if pai_pk else None
    # Instância não gravada só para não repetir aqui o default que o model já decide.
    cor = Unidade(pai=pai).cor_sugerida
    return {
        "tons": tons_da_paleta(cor),
        "cor_hex": hex_da_cor(cor),
    }


def _contexto_do_modal_de_unidade() -> dict[str, Any]:
    # O modal de nova unidade é renderizado com a página, em criar e em editar (SPEC 012): os
    # catálogos dele custam uma consulta e dispensam rota e hx-get de abertura. Sem isto o disco de
    # paleta nasce sem tons e o select de tipo, vazio.
    return _catalogos_de_unidade() | contexto_cor_sugerida(None)


def _catalogos_de_lotacao() -> dict[str, Any]:
    return _catalogo_de_unidades() | {
        "cargos_base": CargoBase.objects.order_by("nome"),
        "cargos_comissao": CargoComissao.objects.order_by("nome"),
    }


def _catalogos_de_unidade() -> dict[str, Any]:
    # Nível decrescente: a lista de tipos desce da mais abrangente para a mais específica.
    return _catalogo_de_unidades() | {
        "tipos_unidade": TipoUnidade.objects.order_by("-nivel", "nome"),
    }


def _catalogo_de_unidades() -> dict[str, Any]:
    # A mesma lista serve à lotação do servidor e à unidade superior do formulário de unidade.
    return {"unidades": Unidade.objects.select_related("tipo").order_by("sigla")}


def _foto_url(perfil: Perfil) -> str | None:
    # Registro órfão (arquivo apagado do storage) viraria <img> quebrado: sem arquivo em disco, o
    # avatar de iniciais assume. A checagem é daqui, não do resolver — ele é domínio puro e não
    # conhece Django nem I/O (SPEC user_admin/006).
    nome_arquivo = perfil.foto.name
    if not nome_arquivo:
        return None
    if not perfil.foto.storage.exists(nome_arquivo):
        return None
    return perfil.foto.url
