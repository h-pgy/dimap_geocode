"""
Os oito atos que mantêm os dois catálogos de cargo (SPECs user_admin/029 e 030): criar, editar,
extinguir e reativar são exclusivos do administrador do sistema, sem alcance — os catálogos são
globais e não incidem sobre unidade alguma.
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

# As mesmas quatro ações, sobre o catálogo de cargo base (SPEC user_admin/030): oito ações para dois
# catálogos que não compram granularidade de concessão nenhuma — a separação existe só para o rastro
# distinguir os atos (SPEC, §7).
ACAO_CRIAR_CARGO_BASE = instanciar_acao(
    slug="cargos.criar_cargo_base",
    nome="Cadastrar cargo base",
    nome_curto="Novo cargo base",
    tooltip="Cria um cargo base no catálogo da DIMAP.",
    url_name="cargos:modal_criar_cargo_base",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)

ACAO_EDITAR_CARGO_BASE = instanciar_acao(
    slug="cargos.editar_cargo_base",
    nome="Editar cargo base",
    nome_curto="Editar cargo base",
    tooltip="Altera nome e sigla de um cargo do catálogo.",
    url_name="cargos:modal_editar_cargo_base",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)

ACAO_EXTINGUIR_CARGO_BASE = instanciar_acao(
    slug="cargos.extinguir_cargo_base",
    nome="Extinguir cargo base",
    nome_curto="Extinguir cargo base",
    tooltip="Tira um cargo base das opções de nomeação — e a reverte.",
    # Precisa reverter sem argumento (`competencias.E004`): é a rota que abre o modal, e não as de
    # gravação, que recebem o cargo no caminho.
    url_name="cargos:modal_extinguir_cargo_base",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)

ACAO_REATIVAR_CARGO_BASE = instanciar_acao(
    slug="cargos.reativar_cargo_base",
    nome="Reativar cargo base",
    nome_curto="Reativar cargo base",
    tooltip="Devolve um cargo base extinto às opções de nomeação.",
    url_name="cargos:modal_reativar_cargo_base",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)
