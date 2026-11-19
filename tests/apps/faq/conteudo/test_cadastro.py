"""Gravação da FAQ (SPEC faq/001): a unicidade da pergunta entre FAQs e a palavra-chave por caminho."""

import pytest

from apps.faq.conteudo import gravar_faq
from apps.faq.models import Faq as FaqModel
from apps.faq.models import PalavraChave as PalavraChaveModel
from services.domain.faq import (
    Faq,
    PalavraChave,
    Pergunta,
    PerguntaJaRespondida,
    Resposta,
    Tema,
)

banco = pytest.mark.banco


def _faq(pergunta: str, variacoes: list[str] | None = None, **overrides: object) -> Faq:
    dados: dict[str, object] = {
        "pergunta": Pergunta(texto=pergunta),
        "variacoes": [Pergunta(texto=v) for v in variacoes or []],
        "resposta": Resposta(markdown="Resposta."),
        "tema": Tema(nome="Certidões"),
    }
    dados.update(overrides)
    return Faq(**dados)  # type: ignore[arg-type]


@banco
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("pergunta", "variacoes"),
    [
        ("como emito a certidao", []),
        ("Outra pergunta qualquer", ["COMO EMITO A CERTIDÃO!"]),
    ],
)
def test_pergunta_repetida_entre_faqs_eh_recusada(
    pergunta: str, variacoes: list[str]
) -> None:
    primeira = gravar_faq(_faq("Como emito a certidão?"))

    with pytest.raises(PerguntaJaRespondida) as erro:
        gravar_faq(_faq(pergunta, variacoes))

    assert [o.faq_id for o in erro.value.ocupadas] == [primeira]
    assert FaqModel.objects.count() == 1


@banco
@pytest.mark.django_db
def test_faq_grava_palavra_chave_pelo_caminho() -> None:
    iptu = PalavraChave(nome="IPTU")
    certidao = PalavraChave(nome="Certidão", pai=iptu)

    primeira = gravar_faq(_faq("Primeira pergunta?", palavras_chave=[certidao]))
    segunda = gravar_faq(_faq("Segunda pergunta?", palavras_chave=[certidao]))

    assert PalavraChaveModel.objects.count() == 2
    marcada = PalavraChaveModel.objects.get(nome="Certidão")
    assert marcada.pai is not None
    assert marcada.pai.nome == "IPTU"
    assert set(marcada.faqs.values_list("pk", flat=True)) == {primeira, segunda}
    assert not PalavraChaveModel.objects.get(nome="IPTU").faqs.exists()
