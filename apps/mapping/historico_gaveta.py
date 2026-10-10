from typing import Any

from django.contrib.sessions.backends.base import SessionBase
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from pydantic import ValidationError

from services.domain.historico_gaveta import (
    AberturaInput,
    AbrirNoHistorico,
    Cena,
    Etiqueta,
    HistoricoGaveta,
    ItemHistorico,
    RetiradaInput,
    TirarDoHistorico,
)

CHAVE_SESSAO = "mapping.historico_gaveta"
TEMPLATE_CENA = "mapping/_cena.html"


def historico_da_sessao(sessao: SessionBase) -> HistoricoGaveta:
    bruto = sessao.get(CHAVE_SESSAO)
    if bruto is None:
        return HistoricoGaveta()
    try:
        return HistoricoGaveta.model_validate(bruto)
    except ValidationError:
        # Sessão gravada por outra versão do modelo: recomeça vazia, em vez de derrubar a tela.
        return HistoricoGaveta()


def abrir_no_historico(sessao: SessionBase, item: ItemHistorico) -> None:
    abrir = AbrirNoHistorico()
    historico = abrir(AberturaInput(historico=historico_da_sessao(sessao), item=item))
    sessao[CHAVE_SESSAO] = historico.model_dump(mode="json")


def tirar_do_historico(sessao: SessionBase, chave: str) -> None:
    tirar = TirarDoHistorico()
    historico = tirar(RetiradaInput(historico=historico_da_sessao(sessao), chave=chave))
    sessao[CHAVE_SESSAO] = historico.model_dump(mode="json")


def responder_cena(
    request: HttpRequest,
    etiqueta: Etiqueta,
    template_gaveta: str,
    contexto: dict[str, Any],
) -> HttpResponse:
    # Renderizada uma vez só: o mesmo texto vai para a sessão e para a resposta.
    gaveta = render_to_string(template_gaveta, contexto | {"etiqueta": etiqueta}, request)
    cena = Cena(gaveta=gaveta, mapa=contexto["payload"])
    abrir_no_historico(request.session, ItemHistorico(etiqueta=etiqueta, cena=cena))
    return render(request, TEMPLATE_CENA, contexto_cena(cena))


def contexto_cena(cena: Cena) -> dict[str, Any]:
    return {"payload": cena.mapa, "gaveta": cena.gaveta}
