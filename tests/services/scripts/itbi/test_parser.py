from pathlib import Path

import pandas as pd

from services.scripts.itbi import MAPA_COLUNAS, NOME_PARQUET, NOME_XLSX, ItbiParser

from .planilhas import aba_completa, escrever_xlsx


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
