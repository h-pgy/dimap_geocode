"""Testes de apps/mapping/views.py (SPEC design/010): a rota aberta que sorteia o fundo de
ortofoto da área administrativa — sem ato administrativo, sem login exigido (§3.5 do CLAUDE.md).
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
