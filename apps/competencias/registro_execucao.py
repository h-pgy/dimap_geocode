"""
O rastro do ato administrativo (SPEC autorizacao/004): quem gravou, com qual lotação no momento e
por quem respondia, se o ato foi praticado em substituição. Chamado só pelo decorator de
`apps/competencias/protecao.py` — a view nunca grava execução diretamente.
"""

from apps.competencias.models import Acao, ExecucaoAcao
from apps.competencias.schemas import AcaoImplementada
from apps.user_admin.exercicio import substituicao_que_exerce
from apps.user_admin.models import Perfil


def gravar_execucao(
    perfil: Perfil,
    acao: AcaoImplementada,
    autorizado: bool,
    operacao: str = "",
    alvo_tipo: str = "",
    alvo_identificador: str = "",
) -> ExecucaoAcao:
    # A competência que abriu a rota pode ser a de outra pessoa: sem isto a linha descreveria o ato
    # pelo cargo errado, e um subordinado sem chefia figuraria distribuindo competência.
    substituicao = substituicao_que_exerce(perfil)
    return ExecucaoAcao.objects.create(
        acao=_acao_projetada(acao),
        perfil=perfil,
        # Lotação e cargos do AUTOR, sempre — não os de quem ele cobre (Caveats, SPEC 004).
        unidade=perfil.unidade,
        cargo_base=perfil.cargo_base,
        cargo_comissao=perfil.cargo_comissao,
        substituindo=substituicao.impedimento.perfil if substituicao else None,
        autorizado=autorizado,
        operacao=operacao,
        alvo_tipo=alvo_tipo,
        alvo_identificador=alvo_identificador,
    )


def _acao_projetada(acao: AcaoImplementada) -> Acao:
    # A negativa é registrável mesmo sem `sincronizar_acoes` já ter passado por esta ação —
    # negar quem não pode nunca pode depender de um comando manual já ter rodado.
    contrato = acao.acao
    projetada, _ = Acao.objects.get_or_create(
        slug=contrato.slug,
        defaults={
            "nome": contrato.nome,
            "nome_curto": contrato.nome_curto or "",
            "tooltip": contrato.tooltip,
            "estrutural": contrato.estrutural,
        },
    )
    return projetada
