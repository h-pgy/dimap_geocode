"""Testes de apps/mapping/views.py (SPEC design/010, design/011): a rota aberta que sorteia o
fundo de ortofoto da área administrativa — sem ato administrativo, sem login exigido (§3.5 do
CLAUDE.md).
"""

from pathlib import Path

from django.test import Client
from django.urls import reverse

import pytest

from apps.mapping import context as mapping_context
from config.pontos_fundo import PontoFundo


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _instalar_catalogo_no_disco(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    chaves: tuple[str, ...],
) -> None:
    pontos = {
        chave: PontoFundo(descricao=chave, lat=-23.5505, lng=-46.6333) for chave in chaves
    }
    for chave in chaves:
        (tmp_path / f"{chave}.png").write_bytes(b"conteudo-fake-do-png")
    monkeypatch.setattr(mapping_context, "MAP_FUNDO_DIR", tmp_path)
    monkeypatch.setattr(mapping_context, "MAP_FUNDO_PONTOS", pontos)
    mapping_context.ortofotos_disponiveis.cache_clear()


# ---------------------------------------------------------------------------
# Rota do fundo
# ---------------------------------------------------------------------------


def test_rota_do_fundo_devolve_ortofoto_diferente(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_catalogo_no_disco(tmp_path, monkeypatch, ("anhangabau", "ibirapuera"))
    cliente = Client()

    resposta = cliente.get(reverse("mapping:fundo_ortofoto"), {"atual": "anhangabau"})

    assert resposta.status_code == 200
    assert resposta.context["ortofoto_fundo"] == "ibirapuera"


def test_rota_do_fundo_devolve_apenas_a_camada(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_catalogo_no_disco(tmp_path, monkeypatch, ("anhangabau", "ibirapuera"))
    cliente = Client()

    resposta = cliente.get(reverse("mapping:fundo_ortofoto"))

    conteudo = resposta.content.decode()
    assert "fundo-ortofoto__camada" in conteudo
    assert 'id="fundo-ortofoto"' not in conteudo


def test_camada_do_rodizio_chega_transparente(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_catalogo_no_disco(tmp_path, monkeypatch, ("anhangabau",))
    cliente = Client()

    do_rodizio = cliente.get(reverse("mapping:fundo_ortofoto"))
    da_pagina = cliente.get(reverse("autenticacao:login"))

    assert "fundo-ortofoto__camada--visivel" not in do_rodizio.content.decode()
    assert "fundo-ortofoto__camada--visivel" in da_pagina.content.decode()


def test_camada_declara_a_ortofoto_que_mostra(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_catalogo_no_disco(tmp_path, monkeypatch, ("anhangabau", "ibirapuera"))
    cliente = Client()

    resposta = cliente.get(reverse("mapping:fundo_ortofoto"), {"atual": "anhangabau"})

    assert f'data-ortofoto="{resposta.context["ortofoto_fundo"]}"' in resposta.content.decode()


@pytest.mark.banco
def test_pagina_administrativa_sem_ortofoto_disponivel(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar_catalogo_no_disco(tmp_path, monkeypatch, ())
    cliente = Client()

    resposta = cliente.get(reverse("autenticacao:login"))

    assert resposta.status_code == 200
    assert '<img class="fundo-ortofoto__imagem"' not in resposta.content.decode()


def test_ortofotos_disponiveis_nao_congela_cache_quando_disco_estiver_vazio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pontos = {"anhangabau": PontoFundo(descricao="anhangabau", lat=-23.55, lng=-46.63)}
    monkeypatch.setattr(mapping_context, "MAP_FUNDO_DIR", tmp_path)
    monkeypatch.setattr(mapping_context, "MAP_FUNDO_PONTOS", pontos)
    mapping_context.ortofotos_disponiveis.cache_clear()

    assert mapping_context.ortofotos_disponiveis() == ()

    (tmp_path / "anhangabau.png").write_bytes(b"png-fake")

    # Detecta automaticamente no próximo acesso sem precisar de restart ou cache_clear
    assert mapping_context.ortofotos_disponiveis() == ("anhangabau",)

