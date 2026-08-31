"""O painel inteiro, lido daqui (SPEC painel/001): é aqui que ato e view livre convivem no mesmo
poço, e é aqui que toda ação inscrita no registro precisa ter o seu card — sem ele, o check
`painel.E004` derruba a subida.
"""

from apps.competencias.acoes_declaradas import ACAO_CONCEDER, ACAO_DEFINIR_ATRIBUICAO
from apps.unidades.acoes_declaradas import (
    ACAO_CRIAR_UNIDADE,
    ACAO_CRIAR_UNIDADE_RAIZ,
    ACAO_EXTINGUIR_UNIDADE,
)
from apps.user_admin.acoes_declaradas import (
    ACAO_CRIAR_SERVIDOR,
    ACAO_DESIGNAR_SUBSTITUTO,
    ACAO_EXONERAR_SERVIDOR,
    ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR,
    ACAO_TORNAR_ADMINISTRADOR,
)

from .estrutura import Aba, ContratoPainel, Grupo, ItemAcao, ItemLivre

# O `url_name` destas quatro ações abre um MODAL (fragmento sem `{% extends "base.html" %}`),
# nunca uma tela — navegar por `<a href>` chegaria no fragmento cru, sem CSS nem HTMX. O card usa
# `_card_item_modal.html`, que dispara `hx-get` para `#poco-modal` em vez de navegar.
PARTIAL_CARTAO_MODAL = "painel/partials/_card_item_modal.html"

ITEM_SENHA = ItemLivre(
    slug="painel.senha",
    nome="Alterar senha",
    tooltip="Troca a senha de acesso, informando a atual.",
    url_name="autenticacao:redefinir_senha",
)

ABA_MINHA_CONTA = Aba(
    slug="painel.minha_conta",
    rotulo="Minha conta",
    titulo="Minha conta",
    descricao=(
        "Seus dados de acesso e identificação no sistema. Não são atos administrativos: estão "
        "disponíveis para todo servidor autenticado, qualquer que seja o cargo ou a unidade."
    ),
    basica=True,
    grupos=(
        Grupo(
            rotulo="Meus dados",
            itens=(
                ItemLivre(
                    slug="painel.meus_dados",
                    nome="Meus dados",
                    tooltip="Sua identificação, lotação e cargos, como o sistema os registra.",
                    url_name="user_admin:pagina_perfil",
                    # A rota do próprio perfil pede o pk: quem o fecha é a sessão, não a declaração.
                    argumento_perfil="pk",
                ),
            ),
        ),
        Grupo(rotulo="Senha", itens=(ITEM_SENHA,)),
    ),
    # Fora de poço e depois dos grupos: sair não é um assunto ao lado dos outros, é o último gesto
    # da página. Único item com template próprio — a rota só encerra a sessão por POST com o token
    # CSRF dela, e nenhum <a href> faz isso.
    itens_abaixo=(
        ItemLivre(
            slug="painel.sair",
            nome="Encerrar sessão",
            tooltip="Sai do sistema neste navegador.",
            url_name="autenticacao:logout",
            partial="painel/partials/_botao_sair.html",
        ),
    ),
)

ABA_RECURSOS_HUMANOS = Aba(
    slug="painel.recursos_humanos",
    rotulo="Recursos Humanos",
    titulo="Recursos Humanos",
    descricao=(
        "O quadro de pessoal da DIMAP: quem está cadastrado, onde está lotado e quais cargos ocupa "
        "— e quem está afastado ou respondendo pelo cargo de outro. Alcança as unidades que você "
        "dirige e as subordinadas a elas."
    ),
    grupos=(
        Grupo(
            rotulo="Servidores",
            itens=(
                # Consultar o quadro é leitura aberta: some para ninguém.
                ItemLivre(
                    slug="painel.lista_servidores",
                    nome="Lista de servidores",
                    tooltip="Todo o quadro, filtrável por unidade, cargo e situação.",
                    url_name="user_admin:listar_servidores",
                ),
                ItemAcao(acao=ACAO_CRIAR_SERVIDOR),
                # Consultar, cadastrar, exonerar (SPEC user_admin/027): a ordem declarada é a
                # ordem exibida, e é a ordem em que o ciclo acontece. Sem esta linha,
                # `painel.E004` derruba a subida.
                ItemAcao(acao=ACAO_EXONERAR_SERVIDOR, partial=PARTIAL_CARTAO_MODAL),
            ),
        ),
        Grupo(
            rotulo="Impedimentos e Substituições",
            itens=(
                ItemAcao(acao=ACAO_REGISTRAR_IMPEDIMENTO_SERVIDOR, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_DESIGNAR_SUBSTITUTO, partial=PARTIAL_CARTAO_MODAL),
            ),
        ),
    ),
)

ABA_ESTRUTURA = Aba(
    slug="painel.estrutura_administrativa",
    rotulo="Estrutura Administrativa",
    titulo="Estrutura Administrativa",
    descricao=(
        "A forma da DIMAP: as unidades que a compõem, como se subordinam, os cargos em comissão que "
        "existem e quem responde pela direção de cada uma."
    ),
    grupos=(
        Grupo(
            rotulo="Organograma",
            itens=(
                ItemLivre(
                    slug="painel.lista_unidades",
                    nome="Ver o organograma",
                    tooltip="A árvore de unidades e a tabela filtrável que a acompanha.",
                    url_name="unidades:listar_unidades",
                ),
                ItemAcao(acao=ACAO_CRIAR_UNIDADE),
                ItemAcao(acao=ACAO_CRIAR_UNIDADE_RAIZ),
                # Fora do snippet ilustrativo da SPEC (implementada depois dele): sem card aqui, o
                # check `painel.E004` recusaria a subida.
                ItemAcao(acao=ACAO_EXTINGUIR_UNIDADE, partial=PARTIAL_CARTAO_MODAL),
            ),
        ),
        # Nasce sem item nenhum (SPEC §4) e, pela cascata, não renderiza. Declarado porque o lugar
        # dele na estrutura já está decidido.
        Grupo(rotulo="Cargos em Comissão", itens=()),
    ),
)

ABA_ATRIBUICOES = Aba(
    slug="painel.atribuicoes",
    rotulo="Atribuições",
    titulo="Atribuições e Competências",
    descricao=(
        "Quem pode praticar cada ato administrativo. Primeiro a unidade recebe a atribuição da ação; "
        "depois a competência é distribuída entre os cargos que a exercem, e pode ser delegada "
        "nominalmente a um servidor."
    ),
    grupos=(
        Grupo(rotulo="Atribuições das unidades", itens=(ItemAcao(acao=ACAO_DEFINIR_ATRIBUICAO),)),
        Grupo(rotulo="Competências e Delegações", itens=(ItemAcao(acao=ACAO_CONCEDER),)),
        # Plenos poderes não é competência de unidade nem delegação: grupo próprio, que some inteiro
        # para quem não é superusuário.
        Grupo(
            rotulo="Administração do Sistema",
            itens=(ItemAcao(acao=ACAO_TORNAR_ADMINISTRADOR, partial=PARTIAL_CARTAO_MODAL),),
        ),
    ),
)

PAINEL = ContratoPainel(
    abas=(ABA_MINHA_CONTA, ABA_RECURSOS_HUMANOS, ABA_ESTRUTURA, ABA_ATRIBUICOES),
)
