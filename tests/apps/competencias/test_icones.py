"""Testes de apps/competencias/icones.py (SPEC autorizacao/006): localizar o SVG de uma ação por
convenção de caminho (o mesmo gabarito do system check da SPEC 001), com fallback silencioso
quando o arquivo falta e cache em memória por processo.
"""

from pathlib import Path
from unittest.mock import patch

from services.domain.autorizacao.contratos import VarianteIcone
from apps.competencias.icones import ResolvedorIcones


# ---------------------------------------------------------------------------
# Localização por convenção
# ---------------------------------------------------------------------------


def test_resolvedor_localiza_icone_por_convencao(tmp_path: Path) -> None:
    conteudo_svg = "<svg viewBox='0 0 24 24'><path d='M0 0 L1 1'/></svg>"
    arquivo = tmp_path / "pequeno.svg"
    arquivo.write_text(conteudo_svg)
    caminhos_consultados: list[str] = []

    def finder_espiao(caminho: str) -> str:
        caminhos_consultados.append(caminho)
        return str(arquivo)

    with patch("django.contrib.staticfiles.finders.find", side_effect=finder_espiao):
        markup = ResolvedorIcones()("competencias.acao_teste", VarianteIcone.PEQUENO)

    assert conteudo_svg in markup
    # Mesmo gabarito do checks.py (SPEC 001): sem segunda cópia da convenção de caminho.
    assert any(
        "acoes/competencias/acao_teste/icones/pequeno.svg" in caminho
        for caminho in caminhos_consultados
    ), f"Gabarito de caminho não seguido. Consultados: {caminhos_consultados}"


# ---------------------------------------------------------------------------
# Fallback silencioso
# ---------------------------------------------------------------------------


def test_resolvedor_cai_no_glifo_generico_sem_arquivo() -> None:
    with patch("django.contrib.staticfiles.finders.find", return_value=None):
        markup_a = ResolvedorIcones()("competencias.sem_icone_a", VarianteIcone.PEQUENO)
        markup_b = ResolvedorIcones()("competencias.sem_icone_b", VarianteIcone.GRANDE)

    assert "<svg" in markup_a
    # O fallback é uma peça só do design system, não uma cópia por ação ausente.
    assert markup_a == markup_b


# ---------------------------------------------------------------------------
# Cache em memória por processo
# ---------------------------------------------------------------------------


def test_resolvedor_le_o_disco_uma_vez_por_icone(tmp_path: Path) -> None:
    arquivo = tmp_path / "grande.svg"
    conteudo_svg = "<svg viewBox='0 0 24 24'><path d='M2 2 L3 3'/></svg>"
    arquivo.write_text(conteudo_svg)
    resolvedor = ResolvedorIcones()

    with patch("django.contrib.staticfiles.finders.find", return_value=str(arquivo)):
        primeira_leitura = resolvedor("competencias.acao_cacheada", VarianteIcone.GRANDE)

    # O arquivo some do disco: se a segunda chamada relesse, ela quebraria ou viria vazia.
    arquivo.unlink()

    with patch("django.contrib.staticfiles.finders.find", return_value=str(arquivo)):
        segunda_leitura = resolvedor("competencias.acao_cacheada", VarianteIcone.GRANDE)

    assert segunda_leitura == primeira_leitura
    assert conteudo_svg in segunda_leitura
