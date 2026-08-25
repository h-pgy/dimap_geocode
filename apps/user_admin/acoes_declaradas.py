"""
As ações inscritas no registro que moram em `user_admin` (SPEC criacao_usuarios/004) — exceção
declarada ao §3.5 (SPEC, Caveats): administrar o próprio cadastro de servidores não é processo, e
opera sobre os models deste app.
"""

from apps.competencias.utils import instanciar_acao
from services.domain.autorizacao import (
    LotacaoAtualEDestino,
    LotacaoDoServidor,
    UnidadesSubordinadas,
    VarianteIcone,
)

ACAO_CRIAR_SERVIDOR = instanciar_acao(
    slug="user_admin.criar_servidor",
    nome="Cadastrar servidor",
    nome_curto="Novo servidor",
    tooltip="Cadastra um servidor e entrega a ele a senha de primeiro acesso.",
    url_name="user_admin:criar_perfil",
    # O item genérico da SPEC autorizacao/006: a linha do menu é a mesma para todas as ações.
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Quem a exerce é quem dirige a unidade: não passa por atribuição nem concessão.
    estrutural=True,
    # A unidade-alvo é a que o formulário escolhe, e o parâmetro já é o default do alcance.
    alcance=UnidadesSubordinadas(),
)

ACAO_EDITAR_SERVIDOR = instanciar_acao(
    slug="user_admin.editar_servidor",
    nome="Editar cadastro de servidor",
    nome_curto="Editar servidor",
    tooltip="Altera identificação, lotação, cargos e foto de um servidor.",
    url_name="user_admin:editar_perfil",
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    estrutural=True,
    # Duas incidências, não uma: o ato tira alguém de uma unidade e o põe em outra, e as duas
    # precisam estar no alcance de quem assina. Os nomes dos parâmetros já são o default do alcance
    # — `servidor` vem do caminho da rota, `unidade` vem do formulário (SPEC criacao_usuarios/005).
    alcance=LotacaoAtualEDestino(),
)

ACAO_TORNAR_ADMINISTRADOR = instanciar_acao(
    slug="user_admin.tornar_administrador",
    nome="Tornar administrador",
    nome_curto="Administrador",
    tooltip="Torna um servidor administrador do sistema — e desfaz.",
    # Precisa reverter sem argumento (`competencias.E004`): é a rota do modal direto, e não a de
    # gravação, que recebe o servidor no caminho.
    url_name="user_admin:modal_administrador",
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Mesmo regime de criar unidade raiz: dirigir unidade não dá esta caneta, e conceder também
    # não. Só quem já a tem a passa adiante.
    estrutural=False,
    exclusiva_superusuario=True,
    # Sem alcance: o ato não incide sobre unidade, e o superusuário alcança o organograma inteiro.
    alcance=None,
)

ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR = instanciar_acao(
    slug="user_admin.registrar_impedimento_servidor",
    nome="Registrar impedimento de servidor",
    nome_curto="Impedimento",
    tooltip="Registra o impedimento que tira um servidor do exercício — e o devolve antes do prazo.",
    # Precisa reverter sem argumento (`competencias.E004`): é a rota do modal direto, e não as de
    # gravação, que recebem o servidor no caminho.
    url_name="user_admin:modal_registrar_impedimento",
    partial="competencias/partials/_item_menu.html",
    variantes_icone=frozenset({VarianteIcone.PEQUENO, VarianteIcone.GRANDE}),
    # Titular da área a exerce por dirigir, sem concessão gravada — e é por ser estrutural que ela é
    # delegável (SPEC autorizacao/009).
    estrutural=True,
    # Um alvo só, e ele é uma PESSOA: a unidade sai da lotação dela, lida no banco.
    alcance=LotacaoDoServidor(),
)
