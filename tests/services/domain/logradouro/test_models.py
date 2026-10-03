from services.domain.logradouro import Logradouro

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _logradouro(
    tipo_logradouro: str,
    nome_logradouro: str,
    titulo: str | None = None,
    preposicao: str | None = None,
) -> Logradouro:
    return Logradouro(
        codlog="156566",
        tipo_logradouro=tipo_logradouro,
        titulo=titulo,
        preposicao=preposicao,
        nome_logradouro=nome_logradouro,
    )


# ---------------------------------------------------------------------------
# Nome completo: tipo, título, preposição e nome
# ---------------------------------------------------------------------------


def test_nome_completo_do_logradouro_junta_titulo_e_preposicao() -> None:
    consolacao = _logradouro("R", "CONSOLACAO", preposicao="DA")
    luis_antonio = _logradouro("AV", "LUIS ANTONIO", titulo="BRIG")
    paulista = _logradouro("AV", "PAULISTA")
    sem_tipo = _logradouro("", "LUIS ANTONIO", titulo="BRIG")

    assert consolacao.nome_completo == "R DA CONSOLACAO"
    assert luis_antonio.nome_completo == "AV BRIG LUIS ANTONIO"
    assert luis_antonio.denominacao == "BRIG LUIS ANTONIO"
    assert paulista.nome_completo == "AV PAULISTA"
    assert sem_tipo.nome_completo == "BRIG LUIS ANTONIO"
