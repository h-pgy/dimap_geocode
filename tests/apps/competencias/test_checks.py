"""Testes de apps/competencias/checks.py (SPEC autorizacao/001; url_name, SPEC criacao_usuarios/005).

Cobre: validar_registro detecta slug duplicado, prefixo de app inexistente, variante de ícone sem
arquivo e url_name que não resolve. `_rota_existe` (SPEC 005) confere o NOME da rota contra o
resolver de verdade — não monta URL —, então os testes de url_name usam nomes reais do projeto em
vez de mockar `reverse`. O patch em django.contrib.staticfiles.finders.find permite rodar sem
staticfiles real.
"""

from unittest.mock import patch

from services.domain.autorizacao.contratos import VarianteIcone
from apps.competencias.schemas import AcaoImplementada, RegistroAcoes
from apps.competencias.utils import instanciar_acao
from apps.competencias.checks import validar_registro

# "search:rotear_busca" existe de verdade e não recebe argumento — âncora neutra para os testes
# que não são sobre resolução de rota.
URL_NAME_REAL = "search:rotear_busca"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def _acao_implementada(
    slug: str = "search.exportar_csv",
    nome: str = "Exportar CSV",
    tooltip: str = "Exporta os resultados em CSV",
    url_name: str = URL_NAME_REAL,
    variantes_icone: frozenset[VarianteIcone] = frozenset(),
) -> AcaoImplementada:
    return instanciar_acao(
        slug=slug,
        nome=nome,
        tooltip=tooltip,
        url_name=url_name,
        variantes_icone=variantes_icone,
    )


# ---------------------------------------------------------------------------
# Validação de slug duplicado
# ---------------------------------------------------------------------------


def test_check_acusa_slug_duplicado() -> None:
    registro = RegistroAcoes(
        acoes=(
            _acao_implementada(),
            _acao_implementada(nome="Exportar CSV (cópia)", url_name="search:exportar_csv_v2"),
        )
    )

    with patch("django.contrib.staticfiles.finders.find", return_value="/fake/path.svg"):
        erros = validar_registro(registro)

    assert any(
        "search.exportar_csv" in e.msg and "duplicad" in e.msg.lower()
        for e in erros
    )


def test_check_slugs_distintos_nao_geram_erro_de_duplicidade() -> None:
    registro = RegistroAcoes(
        acoes=(
            _acao_implementada(),
            _acao_implementada(slug="search.outro", url_name="search:outro"),
        )
    )

    with patch("django.contrib.staticfiles.finders.find", return_value="/fake/path.svg"):
        erros = validar_registro(registro)

    assert not any("duplicad" in e.msg.lower() for e in erros)


# ---------------------------------------------------------------------------
# Validação de prefixo de app (INSTALLED_APPS)
# ---------------------------------------------------------------------------


def test_check_acusa_prefixo_de_app_inexistente() -> None:
    registro = RegistroAcoes(
        acoes=(_acao_implementada(slug="appfantasma.acao", url_name="appfantasma:acao"),)
    )

    with patch("django.contrib.staticfiles.finders.find", return_value="/fake/path.svg"):
        erros = validar_registro(registro)

    assert any(
        "appfantasma" in e.msg and ("instalad" in e.msg.lower() or "app" in e.msg.lower())
        for e in erros
    )


def test_check_prefixo_instalado_nao_gera_erro_de_app() -> None:
    # 'search' está em INSTALLED_APPS como 'apps.search'.
    registro = RegistroAcoes(acoes=(_acao_implementada(),))

    with patch("django.contrib.staticfiles.finders.find", return_value="/fake/path.svg"):
        erros = validar_registro(registro)

    assert not any("app" in e.msg.lower() and "instalad" in e.msg.lower() for e in erros)


# ---------------------------------------------------------------------------
# Validação de arquivos SVG para variantes de ícone
# ---------------------------------------------------------------------------


def test_check_acusa_variante_de_icone_sem_arquivo() -> None:
    registro = RegistroAcoes(
        acoes=(_acao_implementada(variantes_icone=frozenset({VarianteIcone.PEQUENO})),)
    )

    # finders.find devolve None → SVG não encontrado.
    with patch("django.contrib.staticfiles.finders.find", return_value=None):
        erros = validar_registro(registro)

    assert any(
        "search.exportar_csv" in e.msg
        and "pequeno" in e.msg.lower()
        and ("icone" in e.msg.lower() or "svg" in e.msg.lower() or "arquivo" in e.msg.lower() or "encontrad" in e.msg.lower())
        for e in erros
    )


def test_check_variante_com_svg_presente_nao_gera_erro() -> None:
    registro = RegistroAcoes(
        acoes=(_acao_implementada(variantes_icone=frozenset({VarianteIcone.PEQUENO})),)
    )

    with patch(
        "django.contrib.staticfiles.finders.find",
        return_value="/static/acoes/search/exportar_csv/icones/pequeno.svg",
    ):
        erros = validar_registro(registro)

    assert not any(
        "pequeno" in e.msg.lower() or "icone" in e.msg.lower() or "svg" in e.msg.lower()
        for e in erros
    )


def test_check_variante_nao_declarada_nao_e_cobrada() -> None:
    # Ação sem variantes: o check não deve consultar nenhum SVG.
    registro = RegistroAcoes(acoes=(_acao_implementada(),))

    with patch("django.contrib.staticfiles.finders.find", return_value=None):
        erros = validar_registro(registro)

    assert not any(
        "icone" in e.msg.lower() or "svg" in e.msg.lower()
        for e in erros
    )


def test_check_caminho_do_svg_segue_gabarito() -> None:
    # Os dois segmentos do slug viram dois níveis de pasta (ponto em nome de dir é ruim).
    registro = RegistroAcoes(
        acoes=(_acao_implementada(variantes_icone=frozenset({VarianteIcone.GRANDE})),)
    )

    caminhos_consultados: list[str] = []

    def finder_espiao(caminho: str) -> str | None:
        caminhos_consultados.append(caminho)
        return "/fake/" + caminho

    with patch("django.contrib.staticfiles.finders.find", side_effect=finder_espiao):
        validar_registro(registro)

    assert any(
        "acoes/search/exportar_csv/icones/grande.svg" in c
        for c in caminhos_consultados
    ), f"Gabarito de caminho não seguido. Consultados: {caminhos_consultados}"


# ---------------------------------------------------------------------------
# Validação de resolução de rota (url_name)
# ---------------------------------------------------------------------------


def test_check_acusa_url_name_que_nao_resolve() -> None:
    registro = RegistroAcoes(
        acoes=(_acao_implementada(url_name="search:rota_que_nao_existe"),)
    )

    with patch("django.contrib.staticfiles.finders.find", return_value="/fake/path.svg"):
        erros = validar_registro(registro)

    assert any(
        "search:rota_que_nao_existe" in e.msg
        and ("url" in e.msg.lower() or "rota" in e.msg.lower() or "resolve" in e.msg.lower())
        for e in erros
    )


def test_check_acusa_namespace_inexistente() -> None:
    registro = RegistroAcoes(
        acoes=(_acao_implementada(url_name="namespace_fantasma:rota"),)
    )

    with patch("django.contrib.staticfiles.finders.find", return_value="/fake/path.svg"):
        erros = validar_registro(registro)

    assert any(
        "namespace_fantasma:rota" in e.msg
        and ("url" in e.msg.lower() or "rota" in e.msg.lower() or "resolve" in e.msg.lower())
        for e in erros
    )


def test_check_url_name_valido_nao_gera_erro() -> None:
    registro = RegistroAcoes(acoes=(_acao_implementada(),))

    with patch("django.contrib.staticfiles.finders.find", return_value="/fake/path.svg"):
        erros = validar_registro(registro)

    assert not any(
        "url" in e.msg.lower() or "rota" in e.msg.lower() or "resolve" in e.msg.lower()
        for e in erros
    )


def test_check_aceita_rota_com_argumento() -> None:
    # `reverse` cru não resolve rota que exige id no caminho; o check precisa provar só que o
    # NOME existe — quem monta a URL com o argumento em mãos é a view (SPEC criacao_usuarios/005).
    registro = RegistroAcoes(acoes=(_acao_implementada(url_name="user_admin:editar_perfil"),))

    with patch("django.contrib.staticfiles.finders.find", return_value="/fake/path.svg"):
        erros = validar_registro(registro)

    assert not any(
        "url" in e.msg.lower() or "rota" in e.msg.lower() or "resolve" in e.msg.lower()
        for e in erros
    )
