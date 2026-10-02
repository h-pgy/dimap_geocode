import pytest
from bs4 import BeautifulSoup, Tag
from django.conf import settings
from django.http import HttpRequest
from django.test import Client, RequestFactory
from django.urls import reverse

import apps.street_view.views as views
from apps.unidades.models import CorUnidade, Unidade
from apps.user_admin.models import Perfil

URL_DO_PANORAMA = "https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-23.5614%2C-46.6559"

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _perfil() -> Perfil:
    # Sem banco: o @login_required só pergunta is_authenticated, verdadeiro para qualquer Perfil.
    return Perfil(
        rf="890001",
        nome="Servidor",
        sobrenome="Panorama",
        unidade=Unidade(nome="DIMAP-1", cor=CorUnidade.AGUA_700),
    )


def _get_logado(rota: str, dados: dict[str, str]) -> HttpRequest:
    request = RequestFactory().get(reverse(rota), dados)
    request.user = _perfil()
    return request


def _logar_sem_banco(monkeypatch: pytest.MonkeyPatch) -> None:
    # O 422 nasce no PydanticValidationMiddleware, que só roda pelo Client; trocar quem o
    # AuthenticationMiddleware consulta loga o request sem sessão gravada.
    monkeypatch.setattr("django.contrib.auth.middleware.get_user", lambda _request: _perfil())


# ---------------------------------------------------------------------------
# abrir: o redirecionamento ao panorama
# ---------------------------------------------------------------------------


def test_abrir_logado_redireciona_ao_panorama_do_ponto() -> None:
    request = _get_logado("street_view:abrir", {"lon": "-46.6559", "lat": "-23.5614"})

    resposta = views.abrir(request)

    assert resposta.status_code == 302
    assert resposta["Location"] == URL_DO_PANORAMA


def test_abrir_anonimo_vai_para_o_login(client: Client) -> None:
    resposta = client.get(reverse("street_view:abrir"), {"lon": "-46.6559", "lat": "-23.5614"})

    assert resposta.status_code == 302
    assert resposta["Location"].startswith(settings.LOGIN_URL)
    assert "google" not in resposta["Location"]


@pytest.mark.parametrize(
    "dados",
    [
        {"lon": "abc", "lat": "-23.5614"},
        {"lon": "-46.6559"},
    ],
    ids=["lon-malformada", "lat-ausente"],
)
def test_abrir_com_coordenada_malformada_e_recusado(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
    dados: dict[str, str],
) -> None:
    _logar_sem_banco(monkeypatch)

    resposta = client.get(reverse("street_view:abrir"), dados)

    assert resposta.status_code == 422
    assert not resposta.has_header("Location")


# ---------------------------------------------------------------------------
# popup_bloqueado: o aviso que o janela_popup.js pede
# ---------------------------------------------------------------------------


def test_popup_bloqueado_responde_aviso_de_erro_e_recolhe_a_gaveta() -> None:
    request = _get_logado("street_view:popup_bloqueado", {"toggle": "gaveta-endereco-toggle"})

    resposta = views.popup_bloqueado(request)
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")

    aviso = soup.select_one('[role="alert"]')
    assert aviso is not None
    assert "alert-error" in aviso["class"]
    assert views.MSG_POPUP_BLOQUEADO in aviso.get_text()
    assert "pop-ups" in aviso.get_text()

    toggle = soup.find("input", id="gaveta-endereco-toggle")
    assert isinstance(toggle, Tag)
    assert toggle.has_attr("hx-swap-oob")
    assert not toggle.has_attr("checked")
