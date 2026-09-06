"""O que o registro de ações já cobra das ações (`apps/competencias/checks.py`), cobrado agora dos
itens livres do painel; e, no sentido inverso, o painel cobrado de dar destino a toda ação inscrita
no registro (SPEC painel/001).
"""

from django.contrib.staticfiles import finders
from django.core.checks import Error
from django.urls import get_resolver

from apps.competencias.checks import GABARITO_CAMINHO_ICONE
from apps.competencias.schemas import RegistroAcoes

from .estrutura import ContratoPainel, ItemAcao, ItemLivre

# Ação que deliberadamente não tem card no painel — a que só existe dentro de outra tela, ou a que
# opera sobre entidade territorial. Uma linha por exceção.
ACOES_SEM_CARD: frozenset[str] = frozenset(
    {
        # `url_name` recebe o id do alvo no caminho (SPEC criacao_usuarios/005): sem alvo
        # escolhido, não há URL sem argumento para um card. Só existem dentro da página do
        # servidor/unidade específico, alcançada pela "Lista de servidores"/"Ver o organograma".
        "user_admin.editar_servidor",
        "unidades.editar_unidade",
    }
)


def validar_painel(painel: ContratoPainel, registro: RegistroAcoes) -> list[Error]:
    """Recebe painel e registro por argumento — o check registrado injeta os globais."""
    erros: list[Error] = []
    if not any(aba.basica for aba in painel.abas):
        # Sem ela, o servidor sem caneta alguma cai numa página sem nada — e o login o manda
        # para lá.
        erros.append(Error("Painel sem nenhuma aba básica.", id="painel.E001"))

    for item in _itens_livres(painel):
        prefixo, nome = item.slug.split(".")
        caminho = GABARITO_CAMINHO_ICONE.format(
            app=prefixo,
            nome=nome,
            variante=item.variante_icone.value,
        )
        if finders.find(caminho) is None:
            erros.append(
                Error(f"Ícone de '{item.slug}' não encontrado em '{caminho}'.", id="painel.E002")
            )
        if not _rota_existe(item.url_name):
            erros.append(
                Error(f"url_name '{item.url_name}' de '{item.slug}' não resolve.", id="painel.E003")
            )

    return erros + _acoes_orfas(painel, registro)


def _itens_livres(painel: ContratoPainel) -> list[ItemLivre]:
    return [item for item in _todos_itens(painel) if isinstance(item, ItemLivre)]


def _itens_acao(painel: ContratoPainel) -> list[ItemAcao]:
    return [item for item in _todos_itens(painel) if isinstance(item, ItemAcao)]


def _todos_itens(painel: ContratoPainel) -> list[ItemAcao | ItemLivre]:
    itens: list[ItemAcao | ItemLivre] = []
    for aba in painel.abas:
        itens.extend(aba.itens_acima)
        itens.extend(aba.itens_abaixo)
        for grupo in aba.grupos:
            itens.extend(grupo.itens)
    return itens


def _rota_existe(url_name: str) -> bool:
    """`reverse` cru só resolve rota SEM parâmetro; o que o check precisa provar é que o nome
    existe, não montar a URL — a mesma restrição do check de `competencias`."""
    namespace, _, nome = url_name.rpartition(":")
    resolver = get_resolver()
    if namespace:
        try:
            resolver = resolver.namespace_dict[namespace][1]
        except KeyError:
            return False
    return nome in resolver.reverse_dict


def _acoes_orfas(painel: ContratoPainel, registro: RegistroAcoes) -> list[Error]:
    com_card = {item.acao.acao.slug for item in _itens_acao(painel)}
    return [
        # Sem card, o ato segue atribuível e concedível — e sem caminho até a rota que o executa.
        Error(f"Ação '{item.acao.slug}' inscrita no registro e sem card no painel.", id="painel.E004")
        for item in registro.todas()
        if item.acao.slug not in com_card | ACOES_SEM_CARD
    ]


def checar_painel(app_configs: object, **kwargs: object) -> list[Error]:
    """Check registrado no `AppConfig.ready()` — injeta o painel e o registro globais."""
    from apps.competencias.registro import REGISTRO

    from .abas_declaradas import PAINEL

    return validar_painel(PAINEL, REGISTRO)
