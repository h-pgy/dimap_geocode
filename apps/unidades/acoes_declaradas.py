"""
As ações que mantêm o organograma (SPEC user_admin/020): criar e editar unidade são estruturais,
alcance de quem dirige; criar unidade raiz é exclusiva do superusuário, sem alcance — a raiz não
pende de unidade alguma.
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

