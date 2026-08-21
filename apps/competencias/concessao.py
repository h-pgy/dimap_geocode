"""Os dois atos da tela de conceder competência (SPEC autorizacao/008): dar e tirar de um cargo a
competência sobre uma atribuição da unidade."""

from .comandos import ComandoConcessao, ComandoRevogacao
from .models import Concessao


def conceder(comando: ComandoConcessao, concedida_por_id: int) -> Concessao:
    """`get_or_create`, não `create`: o duplo clique no botão do modal não pode virar
    `IntegrityError` na tela — a unicidade quem garante é a constraint da SPEC 002."""
    concessao, _ = Concessao.objects.get_or_create(
        atribuicao_id=comando.atribuicao_id,
        cargo_base_id=comando.cargo_base_id,
        cargo_comissao_id=comando.cargo_comissao_id,
        defaults={"concedida_por_id": concedida_por_id},
    )
    return concessao


def revogar(comando: ComandoRevogacao) -> None:
    """Filtrada pela unidade-alvo: a view já conferiu a concessão contra ela (Caveats da SPEC
    008), e repetir o filtro aqui é o que torna a exclusão segura mesmo se essa barreira mudar."""
    Concessao.objects.filter(
        pk=comando.concessao_id,
        atribuicao__unidade_id=comando.unidade_alvo_id,
    ).delete()


def identificador_cargo(concessao: Concessao) -> str:
    """O texto que o registro do ato (SPEC 004) guarda como alvo. Cargo em comissão se identifica
    pelo padrão remuneratório (sigla + nível); cargo base não tem nível, e a sigla já é única."""
    if concessao.cargo_comissao is not None:
        return concessao.cargo_comissao.padrao
    return concessao.cargo_base.sigla if concessao.cargo_base is not None else ""
