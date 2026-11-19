"""Montagem do índice da página de FAQ (SPEC faq/001): agrupamento, ordem e poda por visibilidade."""

from services.domain.faq import (
    Faq,
    Leitor,
    MontagemIndiceInput,
    MontarIndice,
    Pergunta,
    Resposta,
    Situacao,
    Tema,
    Visibilidade,
)

ANONIMO = Leitor()
SERVIDOR = Leitor(rf="1234567")


def _faq(id: int, pergunta: str, tema: Tema, **overrides: object) -> Faq:
    dados: dict[str, object] = {
        "id": id,
        "pergunta": Pergunta(texto=pergunta),
        "resposta": Resposta(markdown="Resposta."),
        "tema": tema,
        "situacao": Situacao.PUBLICADA,
    }
    dados.update(overrides)
    return Faq(**dados)  # type: ignore[arg-type]


def test_indice_agrupa_por_tema_e_subtema_em_ordem() -> None:
    certidoes = Tema(nome="Certidões", ordem=2)
    busca = Tema(nome="Busca", ordem=1)
    enderecos = Tema(nome="Endereços", pai=busca, ordem=1)
    lotes = Tema(nome="Lotes", pai=busca, ordem=0)
    vazio = Tema(nome="Sem FAQ visível", ordem=0)
    faqs = [
        _faq(1, "Zebra de certidão?", certidoes),
        _faq(2, "Abelha de certidão?", certidoes),
        _faq(3, "Pergunta de endereço", enderecos),
        _faq(4, "Pergunta de lote", lotes),
        _faq(5, "Pergunta direta na busca", busca),
        _faq(6, "Rascunho no tema vazio", vazio, situacao=Situacao.RASCUNHO),
    ]

    indice = MontarIndice()(MontagemIndiceInput(faqs=faqs, leitor=ANONIMO))

    assert [s.tema.nome for s in indice.secoes] == ["Busca", "Certidões"]
    busca_secao, certidoes_secao = indice.secoes
    assert [i.faq.id for i in busca_secao.itens] == [5]
    assert [s.subtema.nome for s in busca_secao.subtemas] == ["Lotes", "Endereços"]
    assert [i.faq.id for i in certidoes_secao.itens] == [2, 1]
    assert busca_secao.total == 3


def test_relacionada_invisivel_nao_vaza() -> None:
    tema = Tema(nome="Certidões")
    publica = _faq(1, "Pergunta pública", tema, relacionadas=[2, 3])
    interna = _faq(2, "Pergunta interna", tema, visibilidade=Visibilidade.INTERNA)
    rascunho = _faq(3, "Pergunta em rascunho", tema, situacao=Situacao.RASCUNHO)
    faqs = [publica, interna, rascunho]

    anonimo = MontarIndice()(MontagemIndiceInput(faqs=faqs, leitor=ANONIMO))
    servidor = MontarIndice()(MontagemIndiceInput(faqs=faqs, leitor=SERVIDOR))

    def da_publica(indice: object) -> list[int | None]:
        itens = indice.secoes[0].itens  # type: ignore[attr-defined]
        return [f.id for i in itens if i.faq.id == 1 for f in i.relacionadas]

    assert da_publica(anonimo) == []
    assert da_publica(servidor) == [2]
