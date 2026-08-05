"""
Contexto das páginas administrativas de servidor (SPEC user_admin/007). Orquestração: traduz o
model para o que o template consome — o hex da cor, a imagem já resolvida pelo domínio e os
catálogos dos selects. Nenhuma regra de negócio.
"""

from typing import Any

from apps.mapping.context import contexto_fundo_admin
from apps.user_admin.models import CargoBase, CargoComissao, Perfil, Unidade
from apps.user_admin.paleta import TINTA_AVATAR, hex_da_cor
from services.domain.avatar import resolver_imagem_perfil


def contexto_criar_perfil() -> dict[str, Any]:
    return contexto_fundo_admin() | _catalogos_de_lotacao()


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
        | {
            "perfil": perfil,
            "imagem": imagem,
            "cor_unidade_hex": cor_unidade_hex,
        }
    )


def _catalogos_de_lotacao() -> dict[str, Any]:
    return {
        "unidades": Unidade.objects.select_related("tipo").order_by("sigla"),
        "cargos_base": CargoBase.objects.order_by("nome"),
        "cargos_comissao": CargoComissao.objects.order_by("nome"),
    }


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
