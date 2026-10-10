"""
Testes do LoteAttributes (SPEC 010): campos de endereço da base oficial no pop-up do lote —
None -> '' para nome_logradouro/numero_porta e o computed_field `endereco`.
"""

from services.domain.lote_geocod.models import SITUACAO_ATIVA, LoteAttributes


def _base(**extra: object) -> LoteAttributes:
    dados: dict[str, object] = {
        "id_poligono": "P1",
        "setor": "001",
        "quadra": "002",
        "lote": "0003",
        "tipo_lote": "F",
    }
    dados.update(extra)
    return LoteAttributes(**dados)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# None -> '' em nome_logradouro / numero_porta
# ---------------------------------------------------------------------------


class TestNoneParaVazio:
    def test_defaults_sao_vazios(self) -> None:
        a = _base()
        assert a.nome_logradouro == ""
        assert a.numero_porta == ""

    def test_none_explicito_vira_vazio(self) -> None:
        a = _base(nome_logradouro=None, numero_porta=None)
        assert a.nome_logradouro == ""
        assert a.numero_porta == ""

    def test_valor_convertido_para_str(self) -> None:
        # cd_numero_porta pode vir numérico da feature WFS
        a = _base(numero_porta=100)
        assert a.numero_porta == "100"

    def test_codlog_opcional_fica_none(self) -> None:
        assert _base().codlog is None


# ---------------------------------------------------------------------------
# computed_field endereco
# ---------------------------------------------------------------------------


class TestEndereco:
    def test_nome_e_numero(self) -> None:
        a = _base(nome_logradouro="AV PAULISTA", numero_porta="100")
        assert a.endereco == "AV PAULISTA, 100"

    def test_so_nome(self) -> None:
        a = _base(nome_logradouro="AV PAULISTA")
        assert a.endereco == "AV PAULISTA"

    def test_nenhum(self) -> None:
        assert _base().endereco == ""

    def test_so_numero(self) -> None:
        a = _base(numero_porta="100")
        assert a.endereco == "100"

    def test_valor_cru_sem_normalizacao(self) -> None:
        # os valores vêm crus da base oficial — nada de chave normalizada aqui
        a = _base(nome_logradouro="AV PAULISTA", numero_porta="SEM NÚMERO")
        assert a.endereco == "AV PAULISTA, SEM NÚMERO"


# ---------------------------------------------------------------------------
# computed_field endereco_completo (SPEC localizacao_lote/001)
# ---------------------------------------------------------------------------


def test_endereco_completo_junta_complemento_so_quando_existe() -> None:
    com_complemento = _base(
        nome_logradouro="AV PAULISTA", numero_porta="100", complemento="APTO 12"
    )
    assert com_complemento.endereco_completo == "AV PAULISTA, 100 — APTO 12"

    sem_complemento = _base(nome_logradouro="AV PAULISTA", numero_porta="100")
    assert sem_complemento.endereco_completo == "AV PAULISTA, 100"


# ---------------------------------------------------------------------------
# computed_field sql (SPEC localizacao_lote/001)
# ---------------------------------------------------------------------------


def test_sql_so_existe_com_digito() -> None:
    assert _base().sql is None
    assert _base(digito="5").sql == "001.002.0003-5"


# ---------------------------------------------------------------------------
# computed_field possui_lancamento (SPEC localizacao_lote/001)
# ---------------------------------------------------------------------------


def test_possui_lancamento_exige_sql_e_situacao_ativa() -> None:
    ativo_sem_digito = _base(situacao=SITUACAO_ATIVA)
    assert ativo_sem_digito.possui_lancamento is False

    com_digito_sem_situacao_ativa = _base(digito="5", situacao=None)
    assert com_digito_sem_situacao_ativa.possui_lancamento is False

    com_digito_e_ativo = _base(digito="5", situacao=SITUACAO_ATIVA)
    assert com_digito_e_ativo.possui_lancamento is True
