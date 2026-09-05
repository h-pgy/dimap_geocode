"""
Os quatro atos que mantêm o catálogo de cargos em comissão (SPEC user_admin/029): criar, editar,
extinguir e reativar são exclusivos do administrador do sistema, sem alcance — o catálogo é global
e não incide sobre unidade alguma.
"""

from apps.competencias.utils import instanciar_acao
from services.domain.autorizacao import VarianteIcone

# Quatro ações para um catálogo só: é a `operacao` do registro que precisa distinguir os atos, e
# quatro contratos é o que dá a cada um card, ícone e rastro próprios (SPEC, §7).
ACAO_CRIAR_CARGO = instanciar_acao(
    slug="cargos.criar_cargo_comissao",
    nome="Cadastrar cargo em comissão",
    nome_curto="Novo cargo",
    tooltip="Cria um cargo em comissão no catálogo da DIMAP.",
    url_name="cargos:modal_criar_cargo",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Mesmo regime de "criar unidade raiz" e "tornar administrador": dirigir unidade não dá esta
    # caneta, e conceder também não.
    estrutural=False,
    exclusiva_superusuario=True,
    # O catálogo é global: não incide sobre unidade alguma, e não há alvo a conferir.
    alcance=None,
)

ACAO_EDITAR_CARGO = instanciar_acao(
    slug="cargos.editar_cargo_comissao",
    nome="Editar cargo em comissão",
    nome_curto="Editar cargo",
    tooltip="Altera nome, sigla, nível e natureza de um cargo em comissão.",
    url_name="cargos:modal_editar_cargo",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)

ACAO_EXTINGUIR_CARGO = instanciar_acao(
    slug="cargos.extinguir_cargo_comissao",
    nome="Extinguir cargo em comissão",
    nome_curto="Extinguir cargo",
    tooltip="Retira um cargo em comissão da nomeação — e a reverte.",
    # Precisa reverter sem argumento (`competencias.E004`): é a rota que abre o modal, e não as de
    # gravação, que recebem o cargo no caminho.
    url_name="cargos:modal_extinguir_cargo",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)

ACAO_REATIVAR_CARGO = instanciar_acao(
    slug="cargos.reativar_cargo_comissao",
    nome="Reativar cargo em comissão",
    nome_curto="Reativar cargo",
    tooltip="Devolve um cargo em comissão extinto à nomeação.",
    url_name="cargos:modal_reativar_cargo",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)
