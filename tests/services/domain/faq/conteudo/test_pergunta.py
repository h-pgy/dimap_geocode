from services.domain.faq import Pergunta


def test_pergunta_e_gravada_com_frases_capitalizadas_e_interrogacao_final() -> None:
    pergunta = Pergunta(texto="  tenho imóvel alugado. quem paga o IPTU ")
    assert pergunta.texto == "Tenho imóvel alugado. Quem paga o IPTU?"
    assert (
        pergunta.chave
        == Pergunta(texto="Tenho imóvel alugado. Quem paga o IPTU?").chave
    )
