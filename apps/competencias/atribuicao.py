"""Os dois atos da tela de atribuições (SPEC autorizacao/007): dar e tirar da unidade a competência
sobre uma ação, e a leitura que a confirmação da remoção precisa antes de apagar."""

from .comandos import ComandoAtribuicao
from .models import Acao, AtribuicaoUnidade, Concessao


def atribuir(comando: ComandoAtribuicao) -> AtribuicaoUnidade:
    """`get_or_create`, não `create`: o duplo clique no cartão do catálogo não pode virar
    `IntegrityError` na tela — a unicidade quem garante é a constraint da SPEC 002."""
    atribuicao, _ = AtribuicaoUnidade.objects.get_or_create(
        unidade_id=comando.unidade_alvo_id,
        acao=Acao.objects.get(slug=comando.acao_slug),
    )
    return atribuicao


def remover(comando: ComandoAtribuicao) -> None:
    """Uma exclusão só: as concessões caem pelo CASCADE da FK (SPEC 002). Varrer e apagar aqui
    duplicaria em Python a regra que já é do schema."""
    AtribuicaoUnidade.objects.filter(
        unidade_id=comando.unidade_alvo_id,
        acao__slug=comando.acao_slug,
    ).delete()


def cargos_que_perdem(comando: ComandoAtribuicao) -> list[str]:
    """Os nomes que a confirmação mostra. Lidos no momento em que o modal é montado (Caveats): entre
    a pergunta e o "sim" outra concessão pode entrar, e o número visto não é mais o que cai."""
    concessoes = Concessao.objects.filter(
        atribuicao__unidade_id=comando.unidade_alvo_id,
        atribuicao__acao__slug=comando.acao_slug,
    ).select_related("cargo_base", "cargo_comissao")
    return [
        (concessao.cargo_base or concessao.cargo_comissao).nome  # type: ignore[union-attr]
        for concessao in concessoes
    ]
