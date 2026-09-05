"""O rastro do ato administrativo, lido (SPEC painel/002): o recorte no banco e a materialização da
linha da tabela do registro. Ao lado de `registro_execucao.py` — um grava o ato, o outro o lê.
"""

from django.db.models import QuerySet
from django.utils.timezone import localtime

from apps.competencias.models import ExecucaoAcao
from apps.unidades.paleta import hex_da_cor
from services.domain.listagem_gestao import (
    SEM_AUTOR,
    SEM_CARGO_COMISSAO,
    BuscaExecucoes,
    LinhaExecucao,
)

FORMATO_MOMENTO = "%d/%m/%Y %H:%M"


def linhas_de_execucoes(busca: BuscaExecucoes) -> list[LinhaExecucao]:
    return [_linha(execucao) for execucao in _recortadas(busca)]


def _recortadas(busca: BuscaExecucoes) -> QuerySet[ExecucaoAcao]:
    """As unidades lidas PRIMEIRO e incondicionalmente; os critérios do usuário depois, cada um só
    se veio.

    Esta ordem é a regra: o conjunto de unidades não é um filtro entre outros que o usuário poderia
    relaxar — ele delimita o universo, e é por isso que `unidade` forjada fora do alcance devolve
    vazio em vez de linha alheia. Critério em branco não estreita nada; a ordem é sempre a
    cronológica reversa, que é a que o registro tem sentido de ser lido.
    """
    consulta = (
        ExecucaoAcao.objects.select_related(
            "acao",
            "perfil",
            "unidade",
            "cargo_base",
            "cargo_comissao",
            "substituindo",
        )
        .filter(unidade_id__in=busca.unidades_lidas)
        .filter(momento__date__gte=busca.inicio, momento__date__lte=busca.fim)
    )
    if busca.perfil_id is not None:
        consulta = consulta.filter(perfil_id=busca.perfil_id)
    if busca.cargo_base_id is not None:
        consulta = consulta.filter(cargo_base_id=busca.cargo_base_id)
    if busca.cargo_comissao_id is not None:
        consulta = consulta.filter(cargo_comissao_id=busca.cargo_comissao_id)
    # Sem fatia aqui: quem fatia é a paginação, depois do filtro do cabeçalho. Cortar no banco faria
    # o número de páginas mentir sobre quantos atos existem no período.
    return consulta.order_by("-momento")


def _linha(execucao: ExecucaoAcao) -> LinhaExecucao:
    # Nada aqui vem do cadastro de hoje: unidade e cargos saem das colunas que a SPEC
    # autorizacao/004 copiou para a linha no dia do ato.
    autor = execucao.perfil
    coberto = execucao.substituindo
    return LinhaExecucao(
        pk=execucao.pk,
        momento=localtime(execucao.momento).strftime(FORMATO_MOMENTO),
        servidor=f"{autor.nome} {autor.sobrenome}" if autor else SEM_AUTOR,
        servidor_pk=execucao.perfil_id,
        unidade=execucao.unidade.sigla,
        unidade_pk=execucao.unidade_id,
        cor_unidade=hex_da_cor(execucao.unidade.cor),
        cargo=execucao.cargo_base.nome,
        comissao=execucao.cargo_comissao.nome if execucao.cargo_comissao else SEM_CARGO_COMISSAO,
        acao=execucao.acao.nome,
        operacao=execucao.operacao,
        # O par vira um campo só: é assim que a coluna se lê e é assim que o cabeçalho a filtra.
        alvo=f"{execucao.alvo_tipo}: {execucao.alvo_identificador}" if execucao.alvo_tipo else "",
        autorizado=execucao.autorizado,
        substituindo=f"{coberto.nome} {coberto.sobrenome}" if coberto else "",
    )
