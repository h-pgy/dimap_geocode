from pathlib import Path

import pandas as pd

from services.scripts.itbi import MAPA_COLUNAS, NOME_PARQUET, NOME_XLSX, ItbiParser

from .planilhas import aba_completa, escrever_xlsx

COLUNA_VALOR = "Valor de Transação (declarado pelo contribuinte)"


def test_parser_le_apenas_abas_no_padrao_mes_ano_e_deriva_mes(tmp_path: Path) -> None:
    originais = tmp_path / "originais"
    parseados = tmp_path / "parseados"
    escrever_xlsx(
        originais / NOME_XLSX.format(ano=2026),
        {
            "JAN-2026": aba_completa(linhas=2),
            "ABR_2026": aba_completa(linhas=3),
            "RESUMO": pd.DataFrame({"total do ano": [999]}),
        },
    )

    ItbiParser()(originais, parseados)

    quadro = pd.read_parquet(parseados / NOME_PARQUET.format(ano=2026))

    # Hífen e underscore são a mesma aba depois da normalização única (§6.1).
    assert sorted(int(mes) for mes in quadro["mes"].unique()) == [1, 4]
    assert len(quadro) == 5, "a aba fora do padrão entrou no parquet"
    assert "total do ano" not in quadro.columns


def test_parser_renomeia_colunas_e_deriva_is_financiamento(tmp_path: Path) -> None:
    originais = tmp_path / "originais"
    parseados = tmp_path / "parseados"

    aba = aba_completa(linhas=3)
    # Caixa, espaço sobrando e acento não impedem o casamento: os dois lados são normalizados.
    aba = aba.rename(
        columns={
            "Data de Transação": "  DATA DE TRANSACAO ",
            "Tipo de Financiamento": "tipo de financiamento",
        }
    )
    aba["tipo de financiamento"] = [None, "", "CARTEIRA HIPOTECARIA"]

    # A aba diz 2014 e o arquivo diz 2015: o ano é sempre o do portal, que viaja no nome do
    # arquivo — o ano da aba só serve para reconhecê-la.
    escrever_xlsx(originais / NOME_XLSX.format(ano=2015), {"DEZ-2014": aba})

    ItbiParser()(originais, parseados)

    quadro = pd.read_parquet(parseados / NOME_PARQUET.format(ano=2015))

    assert set(MAPA_COLUNAS.values()) <= set(quadro.columns)
    assert set(MAPA_COLUNAS) & set(quadro.columns) == set(), "cabeçalho original vazou no parquet"
    assert [int(ano) for ano in quadro["ano"]] == [2015, 2015, 2015]
    assert [int(mes) for mes in quadro["mes"]] == [12, 12, 12]
    assert [bool(flag) for flag in quadro["is_financiamento"]] == [False, False, True]


def test_linha_que_nao_converte_e_descartada_e_o_ano_entra(tmp_path: Path) -> None:
    originais = tmp_path / "originais"
    parseados = tmp_path / "parseados"

    # 1 linha de 40 (2,5%, abaixo do teto): é a linha digitada com célula a mais que empurra a
    # razão social para a coluna de valor — o defeito real de 2025.
    aba = aba_completa(linhas=40)
    valores = aba[COLUNA_VALOR].tolist()
    valores[7] = "RL BRAGA EMPREENDIMENTO IMOBILIARIO SPE LTDA"
    aba[COLUNA_VALOR] = valores
    escrever_xlsx(originais / NOME_XLSX.format(ano=2025), {"ABR-2025": aba})

    parse = ItbiParser()(originais, parseados)

    quadro = pd.read_parquet(parseados / NOME_PARQUET.format(ano=2025))
    assert parse.stats.anos_parseados == [2025], "uma linha podre não pode custar o ano"
    assert len(quadro) == 39
    assert "RL BRAGA EMPREENDIMENTO IMOBILIARIO SPE LTDA" not in quadro["cartorio"].tolist()
    # Descarte nunca é silencioso: quantas, e onde abrir o Excel (linha 9 = índice 7 + cabeçalho).
    assert parse.stats.linhas_descartadas_por_ano == {2025: 1}
    assert parse.stats.descartes_por_ano[2025] == ["ABR-2025:9"]


def test_descarte_acima_do_teto_derruba_o_ano(tmp_path: Path) -> None:
    originais = tmp_path / "originais"
    parseados = tmp_path / "parseados"

    # Metade não converte: isso não é linha ruim, é esquema que mudou — o ano cai inteiro,
    # como antes do teto, e o parquet da carga anterior segue valendo.
    aba = aba_completa(linhas=4)
    aba[COLUNA_VALOR] = ["N/D", 2.0, "N/D", 4.0]
    escrever_xlsx(originais / NOME_XLSX.format(ano=2011), {"JAN-2011": aba})

    parse = ItbiParser()(originais, parseados)

    assert parse.stats.anos_parseados == []
    assert 2011 in parse.stats.falhas_por_ano
    assert "50" in parse.stats.falhas_por_ano[2011], "a fração descartada tem que estar no erro"
    assert not (parseados / NOME_PARQUET.format(ano=2011)).exists()


def _aba_com_cabecalho_acc_duplicado(linhas: int = 3) -> pd.DataFrame:
    """Reproduz o defeito de 2019–2024: a descrição do padrão grafada como `ACC (IPTU)`."""
    aba = aba_completa(linhas=linhas)
    colunas = list(aba.columns)
    colunas[colunas.index("Descrição do padrão (IPTU)")] = "ACC (IPTU)"
    # Dois cabeçalhos iguais: é a leitura do Excel que devolve o segundo como "ACC (IPTU).1".
    aba.columns = colunas
    return aba


def test_patcher_do_acc_recupera_a_descricao_do_padrao(tmp_path: Path) -> None:
    originais = tmp_path / "originais"
    parseados = tmp_path / "parseados"
    escrever_xlsx(
        originais / NOME_XLSX.format(ano=2021),
        {"JAN-2021": _aba_com_cabecalho_acc_duplicado()},
    )

    parse = ItbiParser()(originais, parseados)

    quadro = pd.read_parquet(parseados / NOME_PARQUET.format(ano=2021))
    assert parse.stats.anos_parseados == [2021]
    assert quadro["padrao_construtivo_desc"].tolist() == [
        "padrao_construtivo_desc-0",
        "padrao_construtivo_desc-1",
        "padrao_construtivo_desc-2",
    ]
    assert quadro["ano_construcao_corrigido"].tolist() == [1.0, 2.0, 3.0]


def test_patcher_nao_se_aplica_a_ano_fora_da_lista(tmp_path: Path) -> None:
    originais = tmp_path / "originais"
    parseados = tmp_path / "parseados"
    escrever_xlsx(
        originais / NOME_XLSX.format(ano=2010),
        {"JAN-2010": _aba_com_cabecalho_acc_duplicado()},
    )

    parse = ItbiParser()(originais, parseados)

    # O conserto é datado, não universal: defeito não diagnosticado continua derrubando o ano.
    assert parse.stats.anos_parseados == []
    assert 2010 in parse.stats.falhas_por_ano


def test_patcher_recupera_aba_com_cabecalho_no_rodape(tmp_path: Path) -> None:
    originais = tmp_path / "originais"
    parseados = tmp_path / "parseados"

    # `Bairro` existe na planilha e não no MAPA_COLUNAS: sem ela a ordem canônica não bate.
    def _com_bairro(linhas: int) -> pd.DataFrame:
        aba = aba_completa(linhas=linhas)
        aba.insert(4, "Bairro", [f"bairro-{linha}" for linha in range(linhas)])
        return aba

    escrever_xlsx(
        originais / NOME_XLSX.format(ano=2024),
        {"JAN-2024": _com_bairro(25), "FEV-2024": _com_bairro(3)},
        cabecalho_no_rodape={"JAN-2024"},
    )

    parse = ItbiParser()(originais, parseados)

    quadro = pd.read_parquet(parseados / NOME_PARQUET.format(ano=2024))
    assert parse.stats.anos_parseados == [2024]
    # A linha de título que ficou no corpo é descartada pelo teto; a transação que virou
    # cabeçalho é perda definitiva do portal. Sobram 24 de JAN e as 3 de FEV.
    assert len(quadro) == 27
    assert parse.stats.linhas_descartadas_por_ano == {2024: 1}
    assert "N° do Cadastro (SQL)" not in quadro["sql_num"].tolist(), "a linha de título virou dado"
    assert quadro["sql_num"].tolist().count("sql_num-0") == 1, "só FEV tem a linha 0"
    assert quadro["logradouro_nome"].notna().all(), "as colunas de JAN saíram nulas"


def test_patcher_corrige_o_typo_pardao(tmp_path: Path) -> None:
    originais = tmp_path / "originais"
    parseados = tmp_path / "parseados"

    aba = aba_completa(linhas=3)
    aba = aba.rename(columns={"Descrição do padrão (IPTU)": "Descrição do pardão (IPTU)"})
    escrever_xlsx(originais / NOME_XLSX.format(ano=2026), {"JAN-2026": aba})

    parse = ItbiParser()(originais, parseados)

    quadro = pd.read_parquet(parseados / NOME_PARQUET.format(ano=2026))
    assert parse.stats.anos_parseados == [2026]
    assert quadro["padrao_construtivo_desc"].notna().all()
    assert parse.stats.colunas_ausentes_por_ano == {}
    assert parse.stats.colunas_desconhecidas_por_ano == {}
