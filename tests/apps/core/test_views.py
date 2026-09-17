"""Testes de apps/core/views.py: a home."""

from django.test import Client
from django.urls import reverse


# ---------------------------------------------------------------------------
# A home oferece o atalho para a tela de conferência de documentos
# ---------------------------------------------------------------------------


def test_home_oferece_atalho_para_a_conferencia(client: Client) -> None:
    resposta = client.get(reverse("core:home"))

    assert resposta.status_code == 200
    assert reverse("documentos:pagina") in resposta.content.decode()


# ---------------------------------------------------------------------------
# Sem entidade buscada, a gaveta não existe (SPEC localizacao_lote/001)
# ---------------------------------------------------------------------------


def test_home_sem_entidade_nao_traz_gaveta(client: Client) -> None:
    resposta = client.get(reverse("core:home"))
    conteudo = resposta.content.decode()

    assert resposta.status_code == 200
    assert '<div id="gaveta-entidade"></div>' in conteudo
    assert "gaveta-lateral" not in conteudo
    assert "paleta-gaveta" not in conteudo
    assert 'id="bancada-conjunto"' in conteudo
