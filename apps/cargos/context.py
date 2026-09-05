"""
Contexto das telas do catálogo de cargos em comissão (SPEC user_admin/029): a listagem — sempre com
os extintos, que o toggle "Mostrar cargos extintos" filtra no cliente, nunca aqui — e os quatro atos
que a mantêm. Orquestração: traduz o model para o que o template consome. Nenhuma regra de negócio.
"""

from collections.abc import Mapping
from typing import Any

from apps.cargos.consulta import cargos_nomeaveis, ocupantes_no_quadro
from apps.cargos.extincao import previa_da_extincao, previa_da_reativacao
from apps.cargos.models import ALGARISMOS_ROMANOS, CargoComissao
from apps.core.tabela import colunas_da_tabela, marca_descendente
from apps.mapping.context import contexto_fundo_admin
from services.domain.listagem_gestao import ColunaCargo, ConsultaCargos, LinhaCargo, listar_cargos
from services.utils.erros_formulario import RecusaDeFormulario

ROTULO_COLUNAS_CARGO = {
    ColunaCargo.NOME: "Nome",
    ColunaCargo.PADRAO: "Padrão",
    ColunaCargo.NATUREZA: "Natureza",
}
# O select de nível é o mesmo algarismo romano do padrão — uma tabela em vez de repetir a conversão.
NIVEL_OPCOES = tuple(sorted(ALGARISMOS_ROMANOS.items(), key=lambda item: item[0]))


def contexto_listagem_cargos(consulta: ConsultaCargos) -> dict[str, Any]:
    return (
        contexto_fundo_admin()
        | contexto_corpo_cargos(consulta)
        | {
            "colunas": colunas_da_tabela(consulta, ColunaCargo, ROTULO_COLUNAS_CARGO),
            "ordenar_por": consulta.ordenar_por or "",
            "descendente": marca_descendente(consulta),
        }
    )


def contexto_corpo_cargos(consulta: ConsultaCargos, *, oob: bool = False) -> dict[str, Any]:
    """O servidor manda SEMPRE todos os cargos, extintos inclusive — quem mostra ou esconde é o
    toggle "Mostrar cargos extintos", em `filtro_linha_extinta.js`. Fazer o servidor saber do
    estado do toggle a cada requisição (filtro de coluna, ordenação, ou o swap fora de banda dos
    quatro atos) já quebrou duas vezes (SPEC, Caveats) — o filtro é 100% client-side."""
    linhas = _linhas_de_cargos()
    return {
        "linhas": listar_cargos(linhas, consulta),
        "total_cargos": len(linhas),
        "oob": oob,
    }


def contexto_modal_criar_cargo() -> dict[str, Any]:
    return {"valores": {}, "realce": {}, "erros": (), "nivel_opcoes": NIVEL_OPCOES}


def contexto_criacao_recusada(
    valores: Mapping[str, Any],
    recusa: RecusaDeFormulario,
) -> dict[str, Any]:
    return {
        # `nivel` volta como texto do POST cru; o `selected` do select compara com o número.
        "valores": dict(valores) | {"nivel": _nivel_do_post(valores.get("nivel"))},
        "realce": recusa.realce,
        "erros": recusa.mensagens,
        "nivel_opcoes": NIVEL_OPCOES,
    }


def contexto_modal_editar_cargo(cargo: CargoComissao) -> dict[str, Any]:
    return {
        "cargo": cargo,
        "valores": _valores_de(cargo),
        "realce": {},
        "erros": (),
        "nivel_opcoes": NIVEL_OPCOES,
    } | _travas_de(cargo)


def contexto_edicao_recusada(
    cargo: CargoComissao,
    valores: Mapping[str, Any],
    recusa: RecusaDeFormulario,
) -> dict[str, Any]:
    return {
        "cargo": cargo,
        # `nivel` volta como texto do POST cru; o `selected` do select compara com o número.
        "valores": dict(valores) | {"nivel": _nivel_do_post(valores.get("nivel"))},
        "realce": recusa.realce,
        "erros": recusa.mensagens,
        "nivel_opcoes": NIVEL_OPCOES,
    } | _travas_de(cargo)


def _nivel_do_post(bruto: Any) -> int | None:
    return int(bruto) if isinstance(bruto, str) and bruto.isdigit() else None


def contexto_modal_extinguir(cargo: CargoComissao | None) -> dict[str, Any]:
    """Sem cargo escolhido — aberto pelo card, sem linha em foco —, ainda não há prévia: o select
    espera a escolha. O catálogo é global, e não há alcance a recortar."""
    return {
        "cargo": cargo,
        "previa": previa_da_extincao(cargo) if cargo is not None else None,
        "cargos": cargos_nomeaveis().exclude(pk=cargo.pk) if cargo else cargos_nomeaveis(),
    }


def contexto_ato_extincao_recusado(
    valores: Mapping[str, Any],
    recusa: RecusaDeFormulario,
) -> dict[str, Any]:
    cargo_id = valores.get("cargo")
    cargo = CargoComissao.objects.filter(pk=cargo_id).first() if cargo_id else None
    return contexto_modal_extinguir(cargo) | {
        "valores": valores,
        "erros": recusa.mensagens,
        "realce": recusa.realce,
    }


def contexto_modal_reativar(cargo: CargoComissao | None) -> dict[str, Any]:
    return {
        "cargo": cargo,
        "previa": previa_da_reativacao(cargo) if cargo is not None else None,
        "cargos": _cargos_extintos().exclude(pk=cargo.pk) if cargo else _cargos_extintos(),
    }


def contexto_ato_reativacao_recusado(
    valores: Mapping[str, Any],
    recusa: RecusaDeFormulario,
) -> dict[str, Any]:
    cargo_id = valores.get("cargo")
    cargo = CargoComissao.objects.filter(pk=cargo_id).first() if cargo_id else None
    return contexto_modal_reativar(cargo) | {
        "valores": valores,
        "erros": recusa.mensagens,
        "realce": recusa.realce,
    }


def _cargos_extintos() -> Any:
    return CargoComissao.objects.filter(extinto_em__isnull=False).order_by("nome")


def _linhas_de_cargos() -> list[LinhaCargo]:
    return [_linha_do_cargo(cargo) for cargo in CargoComissao.objects.order_by("nome")]


def _linha_do_cargo(cargo: CargoComissao) -> LinhaCargo:
    return LinhaCargo(
        pk=cargo.pk,
        nome=cargo.nome,
        padrao=cargo.padrao,
        natureza=cargo.natureza,
        extinto=cargo.extinto,
    )


def _travas_de(cargo: CargoComissao) -> dict[str, Any]:
    ocupantes = ocupantes_no_quadro(cargo)
    return {"ocupantes": ocupantes, "natureza_travada": ocupantes > 0}


def _valores_de(cargo: CargoComissao) -> dict[str, Any]:
    return {
        "nome": cargo.nome,
        "sigla": cargo.sigla,
        "nivel": cargo.nivel,
        "e_chefia": cargo.e_chefia,
        "alta_administracao": cargo.alta_administracao,
    }
