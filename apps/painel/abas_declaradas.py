"""O painel inteiro, lido daqui (SPEC painel/001): é aqui que ato e view livre convivem no mesmo
poço, e é aqui que toda ação inscrita no registro precisa ter o seu card — sem ele, o check
`painel.E004` derruba a subida.
"""

from apps.cargos.acoes_declaradas import (
    ACAO_CRIAR_CARGO,
    ACAO_CRIAR_CARGO_BASE,
    ACAO_EDITAR_CARGO,
    ACAO_EDITAR_CARGO_BASE,
    ACAO_EXTINGUIR_CARGO,
    ACAO_EXTINGUIR_CARGO_BASE,
    ACAO_REATIVAR_CARGO,
    ACAO_REATIVAR_CARGO_BASE,
)
from apps.competencias.acoes_declaradas import ACAO_CONCEDER, ACAO_DEFINIR_ATRIBUICAO
from apps.unidades.acoes_declaradas import (
    ACAO_CRIAR_UNIDADE,
    ACAO_CRIAR_UNIDADE_RAIZ,
    ACAO_DEFINIR_TITULAR,
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
                ItemAcao(acao=ACAO_DEFINIR_TITULAR, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_EXTINGUIR_UNIDADE, partial=PARTIAL_CARTAO_MODAL),
            ),
        ),
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
    ),
)

ABA_ADMINISTRACAO = Aba(
    slug="painel.administracao_sistema",
    rotulo="Administração do Sistema",
    titulo="Administração do Sistema",
    descricao=(
        "Quem tem plenos poderes sobre o sistema e o catálogo de cargos em comissão sobre o qual "
        "toda nomeação se apoia. Consultar o catálogo é aberto a todo servidor; alterá-lo, não."
    ),
    grupos=(
        # Primeiro grupo da aba (SPEC painel/002): o histórico não é um assunto ao lado dos cargos,
        # é o que atravessa todos eles. Item livre — ler o registro não é ato administrativo — e
        # por isso é ele quem mantém a aba de pé para quem não administra o sistema.
        Grupo(
            rotulo="Registro de Ações",
            itens=(
                ItemLivre(
                    slug="painel.lista_registro_acoes",
                    nome="Registro de Ações",
                    tooltip="Os atos praticados no seu alcance: quem, com qual cargo, sobre o quê e se podia.",
                    url_name="competencias:listar_registro_acoes",
                ),
            ),
        ),
        # Sai de ABA_ATRIBUICOES, onde o grupo se chamava "Administração do Sistema" — o nome agora
        # é o da aba, e o grupo passa a nomear o que reúne.
        Grupo(
            rotulo="Administradores",
            itens=(ItemAcao(acao=ACAO_TORNAR_ADMINISTRADOR, partial=PARTIAL_CARTAO_MODAL),),
        ),
        # Um grupo só: consultar e alterar o mesmo catálogo é o mesmo assunto, e a cascata já
        # separa os dois — `ItemLivre` não passa por caneta (`resolucao.py`, `_visivel`), os quatro
        # `ItemAcao` passam. É por isso que a lista vem primeiro: é ela quem sobra, e é ela quem
        # mantém a aba de pé para quem não administra o sistema.
        Grupo(
            rotulo="Cargos em Comissão",
            itens=(
                ItemLivre(
                    slug="painel.lista_cargos",
                    nome="Cargos em comissão",
                    tooltip="O catálogo de cargos da DIMAP, com nível, natureza e quem os ocupa.",
                    url_name="cargos:listar_cargos",
                ),
                ItemAcao(acao=ACAO_CRIAR_CARGO, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_EDITAR_CARGO, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_EXTINGUIR_CARGO, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_REATIVAR_CARGO, partial=PARTIAL_CARTAO_MODAL),
            ),
        ),
        # Ao lado, o outro catálogo (SPEC user_admin/030): mesmo molde, sem natureza nem nível.
        Grupo(
            rotulo="Cargos Base",
            itens=(
                ItemLivre(
                    slug="painel.lista_cargos_base",
                    nome="Cargos base",
                    tooltip="O catálogo de cargos base da DIMAP e quem os ocupa.",
                    url_name="cargos:listar_cargos_base",
                ),
                ItemAcao(acao=ACAO_CRIAR_CARGO_BASE, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_EDITAR_CARGO_BASE, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_EXTINGUIR_CARGO_BASE, partial=PARTIAL_CARTAO_MODAL),
                ItemAcao(acao=ACAO_REATIVAR_CARGO_BASE, partial=PARTIAL_CARTAO_MODAL),
            ),
        ),
    ),
)

PAINEL = ContratoPainel(
    abas=(ABA_MINHA_CONTA, ABA_RECURSOS_HUMANOS, ABA_ESTRUTURA, ABA_ATRIBUICOES, ABA_ADMINISTRACAO),
)
