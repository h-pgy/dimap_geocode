import json
from typing import Any

import pytest
from bs4 import BeautifulSoup, Tag
from django.conf import settings
from django.http import HttpRequest
from django.test import Client, RequestFactory
from django.urls import reverse

import apps.geocodificacao_externa.views as views
from apps.unidades.models import CorUnidade, Unidade
from apps.user_admin.models import Perfil
from services.domain.geocodificador_externo import (
    ConsultaGeocodificacao,
    EnderecoExternoAttributes,
    EnderecoExternoFeature,
    GeocodificadorExterno,
    PoliticaGeocodificacao,
    Precisao,
    Provedor,
    ProvedorGeocodificacao,
    ProvedorIndisponivelError,
)
from services.domain.geometry import PointGeometry

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

ENDERECO_FORMATADO = "Alameda Santos, 1293 - Jardim Paulista, São Paulo - SP, 01419-002, Brasil"


class ProvedorDuble(ProvedorGeocodificacao):
    """Devolve os endereços combinados, ou levanta o erro combinado, e conta as chamadas."""

    provedor = Provedor.GOOGLE

    def __init__(
        self,
        enderecos: list[EnderecoExternoFeature],
        erro: Exception | None = None,
    ) -> None:
        super().__init__(PoliticaGeocodificacao())
        self._enderecos = enderecos
        self._erro = erro
        self.chamadas = 0

    def __call__(self, consulta: ConsultaGeocodificacao) -> list[EnderecoExternoFeature]:
        self.chamadas += 1
        if self._erro is not None:
            raise self._erro
        return self._enderecos


def _endereco_externo(precisao: Precisao = Precisao.IMOVEL) -> EnderecoExternoFeature:
    return EnderecoExternoFeature(
        geometry=PointGeometry(type="Point", coordinates=[-46.6571, -23.5621]),
        attributes=EnderecoExternoAttributes(
            endereco_formatado=ENDERECO_FORMATADO,
            municipio="São Paulo",
            uf="SP",
            provedor=Provedor.GOOGLE,
            precisao=precisao,
        ),
        crs=4326,
    )


def _unidade() -> Unidade:
    return Unidade(nome="DIMAP-1", cor=CorUnidade.AGUA_700)


def _perfil() -> Perfil:
    # Sem banco: o @login_required só pergunta is_authenticated, verdadeiro para qualquer Perfil; a
    # unidade em memória é o que o widget do usuário, no context processor, lê.
    return Perfil(rf="890001", nome="Servidor", sobrenome="Externo", unidade=_unidade())


def _post_logado(dados: dict[str, str]) -> HttpRequest:
    request = RequestFactory().post(reverse("geocodificacao_externa:selecionar"), dados)
    request.user = _perfil()
    return request


def _soup(conteudo: bytes) -> BeautifulSoup:
    return BeautifulSoup(conteudo.decode(), "html.parser")


def _payload(soup: BeautifulSoup) -> dict[str, Any] | None:
    script = soup.find("script", id="mapa-payload")
    if not isinstance(script, Tag):
        return None
    return json.loads(script.get_text())  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Geocodificou: ponto no mapa e gaveta do endereço externo
# ---------------------------------------------------------------------------


def test_geocodificar_externo_desenha_ponto_e_abre_gaveta() -> None:
    geocodificador = GeocodificadorExterno(ProvedorDuble([_endereco_externo(Precisao.INTERPOLADA)]))

    resposta = views.geocodificar_externo(_post_logado({}), geocodificador, "al santos, 1293")
    soup = _soup(resposta.content)

    payload = _payload(soup)
    assert payload is not None
    assert [f["geometry"]["type"] for f in payload["geometria"]["features"]] == ["Point"]

    gaveta = soup.find(id="gaveta-entidade")
    assert isinstance(gaveta, Tag)
    assert gaveta.has_attr("hx-swap-oob")
    texto = gaveta.get_text()
    assert ENDERECO_FORMATADO in texto
    assert "Google" in texto
    assert "Interpolada na via" in texto

    form = gaveta.find("form")
    assert isinstance(form, Tag)
    assert form["hx-post"] == reverse("lotes_mais_proximos:mais_proximo_do_ponto")
    campos = {i["name"]: i["value"] for i in form.find_all("input", type="hidden")}
    assert campos == {"lon": "-46.6571", "lat": "-23.5621", "origem": ENDERECO_FORMATADO}


# ---------------------------------------------------------------------------
# Falha do provedor: o aviso diz qual, e nada é desenhado
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("provedor", "mensagem", "tom_esperado"),
    [
        (ProvedorDuble([]), views.MSG_SEM_RESULTADO, "alert-warning"),
        (ProvedorDuble([], erro=ProvedorIndisponivelError("cota")), views.MSG_INDISPONIVEL, "alert-error"),
    ],
    ids=["sem-resultado-aceito", "provedor-indisponivel"],
)
def test_geocodificar_externo_com_falha_responde_aviso_que_diz_qual(
    provedor: ProvedorDuble,
    mensagem: str,
    tom_esperado: str,
) -> None:
    geocodificador = GeocodificadorExterno(provedor)

    resposta = views.geocodificar_externo(_post_logado({}), geocodificador, "al santos, 1293")
    soup = _soup(resposta.content)

    aviso = soup.select_one('[role="alert"]')
    assert aviso is not None
    assert mensagem in aviso.get_text()
    assert tom_esperado in aviso["class"]
    assert _payload(soup) is None


# ---------------------------------------------------------------------------
# A rota: login e configuração
# ---------------------------------------------------------------------------


def test_selecionar_anonimo_vai_para_o_login_sem_chamar_o_provedor(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provedor = ProvedorDuble([_endereco_externo()])
    monkeypatch.setattr(
        views,
        "build_geocodificador_externo",
        lambda _settings: GeocodificadorExterno(provedor),
    )

    resposta = client.post(reverse("geocodificacao_externa:selecionar"), {"texto": "al santos, 1293"})

    assert resposta.status_code == 302
    assert resposta["Location"].startswith(settings.LOGIN_URL)
    assert provedor.chamadas == 0


def test_selecionar_sem_configuracao_responde_indisponivel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(views, "build_geocodificador_externo", lambda _settings: None)

    resposta = views.selecionar(_post_logado({"texto": "al santos, 1293"}))
    soup = _soup(resposta.content)

    aviso = soup.select_one('[role="alert"]')
    assert aviso is not None
    assert views.MSG_INDISPONIVEL in aviso.get_text()
    assert "alert-error" in aviso["class"]
    assert _payload(soup) is None

