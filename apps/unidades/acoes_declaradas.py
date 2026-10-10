"""
As ações que mantêm o organograma (SPEC user_admin/020): criar e editar unidade são estruturais,
alcance de quem dirige; criar unidade raiz é exclusiva do superusuário, sem alcance — a raiz não
pende de unidade alguma. E os quatro atos que mantêm o catálogo de tipos de unidade (SPEC
user_admin/031), exclusivos do administrador do sistema e sem alcance — o catálogo é global.
"""

from apps.competencias.utils import instanciar_acao
from services.domain.autorizacao import (
    UnidadesEstritamenteSubordinadas,
    UnidadesSubordinadas,
    VarianteIcone,
)

ACAO_CRIAR_UNIDADE = instanciar_acao(
    slug="unidades.criar_unidade",
    nome="Cadastrar unidade",
    nome_curto="Nova unidade",
    tooltip="Cria uma unidade abaixo de outra que você dirige.",
    url_name="unidades:criar_unidade",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=True,
    # A unidade sobre a qual o ato incide é a MÃE, e o parâmetro é o nome do select da tela.
    alcance=UnidadesSubordinadas(parametros_alvo=("pai",)),
)

ACAO_EDITAR_UNIDADE = instanciar_acao(
    slug="unidades.editar_unidade",
    nome="Editar unidade",
    nome_curto="Editar unidade",
    tooltip="Altera nome, sigla, tipo e unidade superior de uma unidade.",
    url_name="unidades:editar_unidade",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=True,
    # Um alvo só: a unidade editada, que vem do caminho da rota. O DESTINO da transferência não é
    # conferido — transferir para fora do próprio ramo é permitido, e é isso que a confirmação
    # protege (SPEC, §7).
    alcance=UnidadesSubordinadas(),
)

ACAO_CRIAR_UNIDADE_RAIZ = instanciar_acao(
    slug="unidades.criar_unidade_raiz",
    nome="Criar unidade raiz",
    nome_curto="Unidade raiz",
    tooltip="Cria a unidade de topo de um organograma, que não responde a nenhuma outra.",
    url_name="unidades:criar_unidade_raiz",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Nem estrutural nem concedida: dirigir unidade não dá esta caneta a ninguém, e conceder também
    # não. Os dois campos são independentes, e este vence — ver o avaliador (SPEC, §3).
    estrutural=False,
    exclusiva_superusuario=True,
    # Sem alcance: a raiz não pende de unidade alguma, e não há alvo a conferir.
    alcance=None,
)

ACAO_EXTINGUIR_UNIDADE = instanciar_acao(
    slug="unidades.extinguir_unidade",
    nome="Extinguir unidade",
    nome_curto="Extinguir",
    tooltip="Retira da estrutura uma unidade subordinada, transferindo servidores e subordinadas para a unidade superior — e a reativa.",
    # Precisa reverter sem argumento (`competencias.E004`): é a rota que abre o modal, e não as de
    # gravação.
    url_name="unidades:extinguir_unidade",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=True,
    alcance=UnidadesEstritamenteSubordinadas(),
)

ACAO_DEFINIR_TITULAR = instanciar_acao(
    slug="unidades.definir_titular",
    nome="Definir titular de unidade",
    nome_curto="Titularidade",
    tooltip="Nomeia, troca ou destitui o titular de uma unidade subordinada.",
    url_name="unidades:modal_definir_titular",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=True,
    alcance=UnidadesEstritamenteSubordinadas(),
)

# Quatro ações para um catálogo só: é a `operacao` do registro que precisa distinguir os atos, e
# quatro contratos é o que dá a cada um card, ícone e rastro próprios (SPEC user_admin/031, §7).
ACAO_CRIAR_TIPO_UNIDADE = instanciar_acao(
    slug="unidades.criar_tipo_unidade",
    nome="Cadastrar tipo de unidade",
    nome_curto="Novo tipo",
    tooltip="Cria um tipo de unidade no catálogo da DIMAP.",
    url_name="unidades:modal_criar_tipo_unidade",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)

ACAO_EDITAR_TIPO_UNIDADE = instanciar_acao(
    slug="unidades.editar_tipo_unidade",
    nome="Editar tipo de unidade",
    nome_curto="Editar tipo",
    tooltip="Altera nome, regras de subordinação e requisitos de titular de um tipo de unidade.",
    url_name="unidades:modal_editar_tipo_unidade",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)

ACAO_EXTINGUIR_TIPO_UNIDADE = instanciar_acao(
    slug="unidades.extinguir_tipo_unidade",
    nome="Extinguir tipo de unidade",
    nome_curto="Extinguir tipo",
    tooltip="Retira um tipo de unidade das opções de novas unidades — e a reverte.",
    # Precisa reverter sem argumento (`competencias.E004`): é a rota que abre o modal, e não as de
    # gravação, que recebem o tipo no caminho.
    url_name="unidades:modal_extinguir_tipo_unidade",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)

ACAO_REATIVAR_TIPO_UNIDADE = instanciar_acao(
    slug="unidades.reativar_tipo_unidade",
    nome="Reativar tipo de unidade",
    nome_curto="Reativar tipo",
    tooltip="Devolve um tipo de unidade extinto às opções de criação de unidades.",
    url_name="unidades:modal_reativar_tipo_unidade",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=False,
    exclusiva_superusuario=True,
    alcance=None,
)
