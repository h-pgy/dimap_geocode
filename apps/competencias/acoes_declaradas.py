"""
As ações inscritas no registro (SPEC autorizacao/007 e seguintes). Ponto único de declaração:
inscrever uma ação nova é acrescentar uma constante aqui e listá-la em `registro.py`.
"""

from services.domain.autorizacao import UnidadesSubordinadas, VarianteIcone

from .utils import instanciar_acao

ACAO_DEFINIR_ATRIBUICAO = instanciar_acao(
    slug="competencias.definir_atribuicao",
    nome="Definir atribuições da unidade",
    nome_curto="Atribuições",
    tooltip="Define quais ações a unidade exerce.",
    url_name="competencias:definir_atribuicao",
    # O item genérico da SPEC 006, não um partial desta ação: a linha do menu é a mesma para todas.
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Quem a exerce é quem dirige a unidade: não passa por atribuição nem concessão, e é isso que
    # dispensa qualquer seed de bootstrap.
    estrutural=True,
    # Onde ela pode incidir, e não só quem a exerce: o dirigente age sobre a própria unidade e sobre
    # as de baixo. Declarado aqui, a proteção (SPEC 004) o cumpre sozinha — a view não repete a
    # conferência, e a ação seguinte que precisar de alcance também não a reescreve. O nome do
    # parâmetro que carrega a unidade-alvo já é o default do alcance.
    alcance=UnidadesSubordinadas(),
)
