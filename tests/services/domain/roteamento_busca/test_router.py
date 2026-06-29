"""
Testes unitários do roteador de entrada (roteamento_busca).

A implementação atual usa strings simples nos campos dos parses (setor, codlog, etc.)
com computed_fields booleanos (setor_completo, codlog_completo, ...). Os testes validam
o comportamento do roteador end-to-end via `rotear_entrada`.
"""
import pytest

from services.domain.roteamento_busca import (
    CodlogParse,
    ContribuinteParse,
    EnderecoParse,
    EntradaRouter,
    LogradouroParse,
    RoteamentoQuery,
    RoteamentoStatus,
    TipoEntrada,
    rotear_entrada,
)


def rotear(texto: str, finished_typing: bool = False) -> ...:  # type: ignore[return]
    return rotear_entrada(RoteamentoQuery(texto=texto, finished_typing=finished_typing))


# ---------------------------------------------------------------------------
# Status: vazio e impossível
# ---------------------------------------------------------------------------


class TestStatusVazioEImpossivel:
    def test_vazio_string_vazia(self) -> None:
        r = rotear("")
        assert r.status == RoteamentoStatus.VAZIO
        assert r.candidatos == []
        assert r.match is None

    def test_vazio_so_espacos(self) -> None:
        r = rotear("   ")
        assert r.status == RoteamentoStatus.VAZIO

    def test_impossivel_13_digitos(self) -> None:
        r = rotear("0010010004001")
        assert r.status == RoteamentoStatus.IMPOSSIVEL
        assert r.candidatos == []

    def test_impossivel_preserva_texto_original(self) -> None:
        r = rotear("0010010004001")
        assert r.texto == "0010010004001"


# ---------------------------------------------------------------------------
# Contribuinte
# ---------------------------------------------------------------------------


class TestContribuinte:
    def test_com_pontos_parcial(self) -> None:
        r = rotear("001.001")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, ContribuinteParse)
        assert m.setor == "001"
        assert m.quadra == "001"
        assert m.lote == ""
        assert m.setor_completo is True
        assert m.quadra_completo is True
        assert m.lote_completo is False
        assert m.completo is False

    def test_completo_com_pontos(self) -> None:
        r = rotear("001.001.0004")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, ContribuinteParse)
        assert m.setor == "001"
        assert m.quadra == "001"
        assert m.lote == "0004"
        assert m.dv == ""
        assert m.completo is True

    def test_completo_com_pontos_e_dv(self) -> None:
        r = rotear("001.001.0004-01")
        m = r.match
        assert isinstance(m, ContribuinteParse)
        assert m.dv == "01"
        assert m.dv_completo is True
        assert m.completo is True

    def test_completo_sem_separadores(self) -> None:
        r = rotear("0010010004")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, ContribuinteParse)
        assert m.completo is True

    def test_com_dv_sem_separadores(self) -> None:
        r = rotear("001001000401")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, ContribuinteParse)
        assert m.dv == "01"
        assert m.dv_completo is True
        assert m.completo is True

    def test_mascara_sem_dv(self) -> None:
        r = rotear("001.001.0004")
        m = r.match
        assert isinstance(m, ContribuinteParse)
        assert m.mascara == "001.001.0004"

    def test_mascara_com_dv(self) -> None:
        r = rotear("001.001.0004-01")
        m = r.match
        assert isinstance(m, ContribuinteParse)
        assert m.mascara == "001.001.0004-01"

    def test_calcular_dv_levanta_not_implemented(self) -> None:
        r = rotear("001.001.0004")
        m = r.match
        assert isinstance(m, ContribuinteParse)
        with pytest.raises(NotImplementedError):
            m.calcular_dv()

    def test_tipo_enum(self) -> None:
        r = rotear("001.001.0004")
        assert r.tipos == [TipoEntrada.CONTRIBUINTE]

    def test_8_digitos_parcial(self) -> None:
        # 8 dígitos → setor e quadra completos, lote incompleto
        r = rotear("00100100")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, ContribuinteParse)
        assert m.setor_completo is True
        assert m.quadra_completo is True
        assert m.lote_completo is False
        assert m.completo is False


# ---------------------------------------------------------------------------
# Codlog
# ---------------------------------------------------------------------------


class TestCodlog:
    def test_codlog_com_traco_dv(self) -> None:
        r = rotear("16321-0")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, CodlogParse)
        assert m.codlog == "16321"
        assert m.digito_verificador == "0"
        assert m.codlog_completo is True
        assert m.dv_completo is True
        assert m.completo is True
        assert m.mascara == "16321-0"

    def test_codlog_5_digitos_sem_dv(self) -> None:
        # 5 dígitos → codlog completo (DV ausente), contribuinte parcial → AMBIGUO
        r = rotear("16321")
        assert r.status == RoteamentoStatus.AMBIGUO
        codlog = next(c for c in r.candidatos if isinstance(c, CodlogParse))
        assert codlog.codlog == "16321"
        assert codlog.digito_verificador == ""
        assert codlog.completo is True

    def test_ponto_rejeita_codlog(self) -> None:
        # ponto → codlog rejeitado, só contribuinte
        r = rotear("001.001")
        assert all(c.tipo == TipoEntrada.CONTRIBUINTE for c in r.candidatos)

    def test_mais_de_6_digitos_rejeita_codlog(self) -> None:
        # 7+ dígitos → só contribuinte
        r = rotear("0010010")
        assert r.status == RoteamentoStatus.UNICO
        assert r.tipos == [TipoEntrada.CONTRIBUINTE]

    def test_mascara_sem_dv(self) -> None:
        r = rotear("16321-0")
        m = r.match
        assert isinstance(m, CodlogParse)
        assert m.mascara == "16321-0"

    def test_calcular_dv_levanta_not_implemented(self) -> None:
        r = rotear("16321-0")
        m = r.match
        assert isinstance(m, CodlogParse)
        with pytest.raises(NotImplementedError):
            m.calcular_dv()


# ---------------------------------------------------------------------------
# Ambiguidade: dígitos sem separador de código
# ---------------------------------------------------------------------------


class TestAmbiguidade:
    def test_2_digitos_ambiguo(self) -> None:
        r = rotear("20")
        assert r.status == RoteamentoStatus.AMBIGUO
        assert TipoEntrada.CONTRIBUINTE in r.tipos
        assert TipoEntrada.CODLOG in r.tipos

        cont = next(c for c in r.candidatos if isinstance(c, ContribuinteParse))
        assert cont.setor == "20"
        assert cont.setor_completo is False
        assert cont.completo is False

        cod = next(c for c in r.candidatos if isinstance(c, CodlogParse))
        assert cod.codlog == "20"
        assert cod.codlog_completo is False
        assert cod.completo is False

    def test_6_digitos_ambiguo(self) -> None:
        # codlog completo (c/ DV) + contribuinte parcial
        r = rotear("163210")
        assert r.status == RoteamentoStatus.AMBIGUO
        assert TipoEntrada.CODLOG in r.tipos
        assert TipoEntrada.CONTRIBUINTE in r.tipos

    def test_7_digitos_so_contribuinte(self) -> None:
        r = rotear("0010010")
        assert r.status == RoteamentoStatus.UNICO
        assert r.tipos == [TipoEntrada.CONTRIBUINTE]

    def test_10_digitos_so_contribuinte(self) -> None:
        r = rotear("0010010004")
        assert r.status == RoteamentoStatus.UNICO
        assert r.tipos == [TipoEntrada.CONTRIBUINTE]


# ---------------------------------------------------------------------------
# Logradouro
# ---------------------------------------------------------------------------


class TestLogradouro:
    def test_tipo_e_nome_completo(self) -> None:
        r = rotear("Avenida Paulista")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, LogradouroParse)
        assert m.tipo_logradouro == "Avenida"
        assert m.nome == "Paulista"
        assert m.completo is True

    def test_so_nome_parcial(self) -> None:
        r = rotear("paulista")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, LogradouroParse)
        assert m.tipo_logradouro == ""
        assert m.nome == "paulista"
        assert m.completo is False

    def test_so_nome_finished_typing_completo(self) -> None:
        r = rotear("paulista", finished_typing=True)
        m = r.match
        assert isinstance(m, LogradouroParse)
        assert m.tipo_logradouro == ""
        assert m.nome == "paulista"
        assert m.completo is True

    def test_tipo_e_nome_parciais(self) -> None:
        r = rotear("rua itat")
        m = r.match
        assert isinstance(m, LogradouroParse)
        assert m.tipo_logradouro == "rua"
        assert m.nome == "itat"
        assert m.completo is True

    def test_rua_numerada_e_logradouro(self) -> None:
        r = rotear("rua 25 de março")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, LogradouroParse)
        assert m.tipo_logradouro == "rua"
        assert m.nome == "25 de março"
        assert m.completo is True

    def test_comeca_com_digito_nao_e_logradouro(self) -> None:
        r = rotear("20")
        assert TipoEntrada.LOGRADOURO not in r.tipos
        assert TipoEntrada.ENDERECO not in r.tipos

    def test_preserva_casing_e_acentos(self) -> None:
        r = rotear("Avenida Paulista")
        m = r.match
        assert isinstance(m, LogradouroParse)
        assert m.tipo_logradouro == "Avenida"
        assert m.nome == "Paulista"

    def test_tipo_enum(self) -> None:
        r = rotear("Avenida Paulista")
        assert r.tipos == [TipoEntrada.LOGRADOURO]

    def test_avenida_paulista_sempre_completo(self) -> None:
        # tipo + nome presentes → completo independente do finished_typing
        for ft in (True, False):
            r = rotear("avenida paulista", finished_typing=ft)
            m = r.match
            assert isinstance(m, LogradouroParse)
            assert m.completo is True


# ---------------------------------------------------------------------------
# Endereço
# ---------------------------------------------------------------------------


class TestEndereco:
    def test_tipo_nome_numero_com_virgula(self) -> None:
        r = rotear("avenida paulista, 3")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, EnderecoParse)
        assert m.logradouro.tipo_logradouro == "avenida"
        assert m.logradouro.nome == "paulista"
        assert m.numero == 3
        assert m.completo is True

    def test_tipo_nome_numero_sem_virgula(self) -> None:
        r = rotear("avenida paulista 3")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, EnderecoParse)
        assert m.logradouro.tipo_logradouro == "avenida"
        assert m.logradouro.nome == "paulista"
        assert m.numero == 3
        assert m.completo is True

    def test_so_nome_numero_sem_virgula_parcial(self) -> None:
        r = rotear("paulista 3")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, EnderecoParse)
        assert m.logradouro.tipo_logradouro == ""
        assert m.logradouro.nome == "paulista"
        assert m.numero == 3
        assert m.completo is False

    def test_so_nome_numero_com_virgula_parcial(self) -> None:
        r = rotear("paulista, 3")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, EnderecoParse)
        assert m.logradouro.tipo_logradouro == ""
        assert m.logradouro.nome == "paulista"
        assert m.numero == 3
        assert m.completo is False

    def test_so_nome_numero_finished_typing_completo(self) -> None:
        r = rotear("paulista, 300", finished_typing=True)
        m = r.match
        assert isinstance(m, EnderecoParse)
        assert m.logradouro.tipo_logradouro == ""
        assert m.numero == 300
        assert m.completo is True

    def test_descarta_complemento(self) -> None:
        r = rotear("avenida paulista, 3, consolação, são paulo")
        m = r.match
        assert isinstance(m, EnderecoParse)
        assert m.logradouro.tipo_logradouro == "avenida"
        assert m.logradouro.nome == "paulista"
        assert m.numero == 3
        assert m.completo is True

    def test_rua_numerada_com_virgula(self) -> None:
        r = rotear("rua 25 de março, 100")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, EnderecoParse)
        assert m.logradouro.tipo_logradouro == "rua"
        assert m.logradouro.nome == "25 de março"
        assert m.numero == 100
        assert m.completo is True

    def test_rua_numerada_sem_virgula(self) -> None:
        r = rotear("rua 25 de março 100")
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, EnderecoParse)
        assert m.logradouro.tipo_logradouro == "rua"
        assert m.logradouro.nome == "25 de março"
        assert m.numero == 100
        assert m.completo is True

    def test_exclusao_mutua_com_logradouro(self) -> None:
        r = rotear("avenida paulista 3")
        assert TipoEntrada.LOGRADOURO not in r.tipos

    def test_tipo_enum(self) -> None:
        r = rotear("avenida paulista, 3")
        assert r.tipos == [TipoEntrada.ENDERECO]


# ---------------------------------------------------------------------------
# finished_typing não afeta códigos
# ---------------------------------------------------------------------------


class TestFinishedTypingCodigos:
    def test_contribuinte_parcial_nao_afetado(self) -> None:
        r = rotear("00100100", finished_typing=True)
        assert r.status == RoteamentoStatus.UNICO
        m = r.match
        assert isinstance(m, ContribuinteParse)
        assert m.completo is False

    def test_codlog_parcial_nao_afetado(self) -> None:
        r = rotear("163", finished_typing=True)
        # ambíguo: prefixo de 3 dígitos
        assert r.status == RoteamentoStatus.AMBIGUO
        cod = next(c for c in r.candidatos if isinstance(c, CodlogParse))
        assert cod.completo is False


# ---------------------------------------------------------------------------
# Ponto de extensão de regras (contribuinte)
# ---------------------------------------------------------------------------


class TestExtensaoRegras:
    def test_regra_filtra_candidato_contribuinte(self) -> None:
        from services.domain.roteamento_busca.codlog import CodlogIdentifier
        from services.domain.roteamento_busca.contribuinte import ContribuinteIdentifier
        from services.domain.roteamento_busca.endereco import EnderecoIdentifier
        from services.domain.roteamento_busca.logradouro import LogradouroIdentifier

        # regra: setor não pode começar com dígito > 4
        regra_setor = lambda p: bool(p.setor) and p.setor[0] <= "4"
        router = EntradaRouter(
            identifiers=(
                ContribuinteIdentifier(regras=(regra_setor,)),
                CodlogIdentifier(),
                LogradouroIdentifier(),
                EnderecoIdentifier(),
            )
        )
        r = router(RoteamentoQuery(texto="5"))
        # contribuinte reprovado pela regra → só codlog
        assert r.status == RoteamentoStatus.UNICO
        assert r.tipos == [TipoEntrada.CODLOG]
