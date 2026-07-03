"""
Testes do LoteAttributes (SPEC 010): campos de endereço da base oficial no pop-up do lote —
None -> '' para nome_logradouro/numero_porta e o computed_field `endereco`.
"""

from services.domain.lote_geocod.models import LoteAttributes


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
