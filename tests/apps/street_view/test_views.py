import pytest
from bs4 import BeautifulSoup, Tag
from django.conf import settings
from django.http import HttpRequest
from django.test import Client, RequestFactory
from django.urls import reverse
from pydantic import SecretStr

import apps.street_view.views as views
from apps.unidades.models import CorUnidade, Unidade
from apps.user_admin.models import Perfil

CHAVE = "chave-de-navegador-de-teste"
LON = -46.6559
LAT = -23.5614
COORDENADAS = {"lon": str(LON), "lat": str(LAT)}
MOTIVOS_DE_FALTA = {"sem_imagem", "sem_imagem_no_destino", "indisponivel"}

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


def _get_logado(dados: dict[str, str]) -> HttpRequest:
    request = RequestFactory().get(reverse("street_view:abrir"), dados)
    request.user = _perfil()
    return request


def _post_logado() -> HttpRequest:
    request = RequestFactory().post(reverse("street_view:fechar"))
    request.user = _perfil()
    return request


def _logar_sem_banco(monkeypatch: pytest.MonkeyPatch) -> None:
    # O 422 nasce no PydanticValidationMiddleware, que só roda pelo Client; trocar quem o
    # AuthenticationMiddleware consulta loga o request sem sessão gravada.
    monkeypatch.setattr("django.contrib.auth.middleware.get_user", lambda _request: _perfil())


def _configurar_chave(monkeypatch: pytest.MonkeyPatch, chave: str) -> None:
    monkeypatch.setattr(views, "GOOGLE_MAPS_BROWSER_KEY", SecretStr(chave))


def abrir_panorama(monkeypatch: pytest.MonkeyPatch, chave: str) -> BeautifulSoup:
    _configurar_chave(monkeypatch, chave)
    resposta = views.abrir(_get_logado(COORDENADAS))
    assert resposta.status_code == 200
    return BeautifulSoup(resposta.content.decode(), "html.parser")


def _atributo(tag: Tag, nome: str) -> str:
    valor = tag[nome]
    assert isinstance(valor, str)
    return valor


# ---------------------------------------------------------------------------
# abrir: a gaveta do panorama
# ---------------------------------------------------------------------------


def test_abrir_logado_devolve_a_gaveta_do_panorama(monkeypatch: pytest.MonkeyPatch) -> None:
    soup = abrir_panorama(monkeypatch, CHAVE)

    # Irmã imediata do toggle marcado: é o que o CSS lê para abrir a gaveta no swap.
    placa = soup.select_one(".gaveta-toggle:checked + .gaveta-inferior")
    assert placa is not None
    assert "gaveta-inferior-puxavel" in placa["class"]

    palco = placa.select_one("[data-street-view]")
    assert palco is not None
    assert float(_atributo(palco, "data-lat")) == pytest.approx(LAT)
    assert float(_atributo(palco, "data-lon")) == pytest.approx(LON)
    assert float(_atributo(palco, "data-raio")) == views.STREET_VIEW_RAIO_M
    assert palco["data-chave"] == CHAVE

    botao = placa.select_one("button[data-selecionar-posicao]")
    assert botao is not None
    assert "Selecionar esta posição" in botao.get_text()
    assert botao.has_attr("disabled")
    assert botao["hx-post"] == reverse("street_view:fechar")

    marca = soup.find(id="contexto-acao")
    assert isinstance(marca, Tag)
    assert marca.has_attr("hx-swap-oob")
    assert marca["data-contexto-acao"] == "street-view"


def test_abrir_traz_as_faltas_escritas_e_ocultas(monkeypatch: pytest.MonkeyPatch) -> None:
    soup = abrir_panorama(monkeypatch, CHAVE)

    faltas = {_atributo(falta, "data-falta"): falta for falta in soup.select("[data-falta]")}
    assert set(faltas) == MOTIVOS_DE_FALTA
    for falta in faltas.values():
        assert falta.has_attr("hidden")
        assert falta.get_text(strip=True)
    assert f"{views.STREET_VIEW_RAIO_M:.0f} m" in faltas["sem_imagem"].get_text()


def test_abrir_sem_chave_abre_na_falta_indisponivel(monkeypatch: pytest.MonkeyPatch) -> None:
    soup = abrir_panorama(monkeypatch, "")

    assert soup.select_one(".gaveta-toggle:checked + .gaveta-inferior") is not None
    assert soup.select_one("[data-street-view]") is None
    assert soup.select_one("[data-selecionar-posicao]") is None
    indisponivel = soup.select_one('[data-falta="indisponivel"]')
    assert indisponivel is not None
    assert not indisponivel.has_attr("hidden")
    assert views.MSG_INDISPONIVEL in indisponivel.get_text()


def test_abrir_anonimo_vai_para_o_login(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configurar_chave(monkeypatch, CHAVE)

    resposta = client.get(reverse("street_view:abrir"), COORDENADAS)

    assert resposta.status_code == 302
    assert resposta["Location"].startswith(settings.LOGIN_URL)
    assert CHAVE not in resposta["Location"]
    assert CHAVE not in resposta.content.decode()


@pytest.mark.parametrize(
    "dados",
    [
        {"lon": "abc", "lat": str(LAT)},
        {"lon": str(LON)},
    ],
    ids=["lon-malformada", "lat-ausente"],
)
def test_abrir_com_coordenada_malformada_e_recusado(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
    dados: dict[str, str],
) -> None:
    _logar_sem_banco(monkeypatch)
    _configurar_chave(monkeypatch, CHAVE)

    resposta = client.get(reverse("street_view:abrir"), dados)

    assert resposta.status_code == 422
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")
    assert soup.select_one(".gaveta-inferior") is None
    assert soup.select_one("[data-street-view]") is None


# ---------------------------------------------------------------------------
# fechar: a gaveta esvazia e o contexto se encerra
# ---------------------------------------------------------------------------


def test_fechar_esvazia_a_gaveta_e_encerra_o_contexto(client: Client) -> None:
    resposta = views.fechar(_post_logado())
    soup = BeautifulSoup(resposta.content.decode(), "html.parser")

    marca = soup.find(id="contexto-acao")
    assert isinstance(marca, Tag)
    assert marca.has_attr("hx-swap-oob")
    assert not marca.has_attr("data-contexto-acao")
    # Só o OOB: o que sobra para o alvo do swap é o vazio que esvazia a gaveta.
    assert soup.find_all(True) == [marca]
    assert soup.get_text(strip=True) == ""

    anonimo = client.post(reverse("street_view:fechar"))

    assert anonimo.status_code == 302
    assert anonimo["Location"].startswith(settings.LOGIN_URL)
