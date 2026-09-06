from collections import Counter

from django.apps import apps
from django.contrib.staticfiles import finders
from django.core.checks import Error
from django.urls import get_resolver

from .schemas import RegistroAcoes

# Os dois segmentos do slug viram dois níveis de pasta: ponto em nome de diretório é ruim de viver.
GABARITO_CAMINHO_ICONE = "acoes/{app}/{nome}/icones/{variante}.svg"


def validar_registro(registro: RegistroAcoes) -> list[Error]:
    """Recebe o registro por argumento — o check registrado só injeta o global."""
    erros: list[Error] = []
    contagem_slugs = Counter(item.acao.slug for item in registro.todas())

    for item in registro.todas():
        acao = item.acao
        prefixo, nome = acao.slug.split(".")

        if contagem_slugs[acao.slug] > 1:
            erros.append(Error(f"Slug de ação duplicado: '{acao.slug}'.", id="competencias.E001"))

        try:
            apps.get_app_config(prefixo)
        except LookupError:
            erros.append(
                Error(
                    f"Prefixo de slug '{prefixo}' (ação '{acao.slug}') não corresponde a um "
                    "app instalado.",
                    id="competencias.E002",
                )
            )

        for variante in acao.variantes_icone:
            caminho = GABARITO_CAMINHO_ICONE.format(
                app=prefixo,
                nome=nome,
                variante=variante.value,
            )
            if finders.find(caminho) is None:
                erros.append(
                    Error(
                        f"Ícone '{variante.value}' da ação '{acao.slug}' não encontrado em "
                        f"'{caminho}'.",
                        id="competencias.E003",
                    )
                )

        if not _rota_existe(item.url_name):
            erros.append(
                Error(
                    f"url_name '{item.url_name}' da ação '{acao.slug}' não resolve.",
                    id="competencias.E004",
                )
            )

    return erros


def _rota_existe(url_name: str) -> bool:
    """`reverse` cru só resolve rota SEM parâmetro, e ação que incide sobre um objeto tem o id no
    caminho. O que o check precisa provar é que o nome existe — montar a URL é da view, que tem o
    argumento em mãos."""
    namespace, _, nome = url_name.rpartition(":")
    resolver = get_resolver()
    if namespace:
        try:
            resolver = resolver.namespace_dict[namespace][1]
        except KeyError:
            return False
    return nome in resolver.reverse_dict


def checar_registro_de_acoes(app_configs: object, **kwargs: object) -> list[Error]:
    """Check registrado no `AppConfig.ready()` — injeta o registro global."""
    from .registro import REGISTRO

    return validar_registro(REGISTRO)
