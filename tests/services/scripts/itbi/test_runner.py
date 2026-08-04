from collections.abc import Iterable, Iterator, Mapping
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from services.scripts.itbi import (
    OUTPUT_FILENAME,
    PASTA_ORIGINAIS,
    PASTA_PARSEADOS,
    ItbiCargaVaziaError,
    ItbiConfig,
    NOME_PARQUET,
    NOME_XLSX,
    run,
)
from services.utils.http import HttpFetchError
from services.utils.metadados import ler_metadados

from .planilhas import aba_completa, escrever_xlsx

ALVO_BUILD_FETCHER = "services.scripts.itbi.runner.build_fetcher"


def _url_xlsx(ano: int) -> str:
    # Absoluta de propósito: o urljoin do scraper a devolve intacta, então o dublê não precisa
    # saber qual é a URL da página do portal.
    return f"https://arquivos.portal.test/itbi_{ano}.xlsx"


def _pagina(anos: Iterable[int]) -> str:
    itens = "".join(
        f"<li><strong>{ano}</strong><a href='{_url_xlsx(ano)}'>Excel</a></li>" for ano in anos
    )
    return f"<html><body><section class='psp-agencies-content'><ul>{itens}</ul></section></body></html>"


class _Resposta:
    """O que o dublê devolve: texto para a página, bytes para o xlsx."""

    def __init__(self, *, text: str = "", content: bytes = b"") -> None:
        self.status_code = 200
        self.text = text
        self.content = content

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int | None = None) -> Iterator[bytes]:
        yield self.content


class _PortalDuble:
    """No lugar do HttpFetcher: serve a página e os xlsx, e falha nos anos combinados."""

    def __init__(
        self,
        html: str,
        arquivos: Mapping[str, bytes],
        falhas: Iterable[str] = (),
    ) -> None:
        self._html = html
        self._arquivos = dict(arquivos)
        self._falhas = set(falhas)

    def __call__(self, url: str, **kwargs: Any) -> _Resposta:
        if url in self._falhas:
            raise HttpFetchError(f"{url}: HTTP 503 após 4 tentativas")
        if url in self._arquivos:
            return _Resposta(content=self._arquivos[url])
        return _Resposta(text=self._html)


def _bytes_xlsx(tmp_path: Path, ano: int, abas: Mapping[str, pd.DataFrame]) -> bytes:
    origem = escrever_xlsx(tmp_path / "_fixtures" / f"{ano}.xlsx", abas)
    return origem.read_bytes()


def _portal(
    tmp_path: Path,
    *,
    publicados: Iterable[int],
    falham: Iterable[int] = (),
    abas: Mapping[int, Mapping[str, pd.DataFrame]] | None = None,
) -> _PortalDuble:
    publicados = list(publicados)
    por_ano = dict(abas or {})
    arquivos = {
        _url_xlsx(ano): _bytes_xlsx(
            tmp_path,
            ano,
            por_ano.get(ano, {f"JAN-{ano}": aba_completa(linhas=2)}),
        )
        for ano in publicados
    }
    return _PortalDuble(_pagina(publicados), arquivos, [_url_xlsx(ano) for ano in falham])


def _instalar(monkeypatch: pytest.MonkeyPatch, portal: _PortalDuble) -> None:
    monkeypatch.setattr(ALVO_BUILD_FETCHER, lambda *args, **kwargs: portal)


def test_divergencia_de_esquema_entra_no_parquet_e_nos_metadados(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    aba = aba_completa(linhas=2).drop(columns=["CEP"])
    aba["Coluna Nova Do Portal"] = ["a", "b"]
    _instalar(monkeypatch, _portal(tmp_path, publicados=[2025], abas={2025: {"JAN-2025": aba}}))

    resultado = run(ItbiConfig())

    quadro = pd.read_parquet(resultado.output_path)
    assert resultado.parse.anos_parseados == [2025], "a divergência derrubou o ano"
    assert "Coluna Nova Do Portal" not in quadro.columns
    assert quadro["cep"].isna().all()

    detalhes = ler_metadados()[OUTPUT_FILENAME].detalhes
    assert detalhes is not None
    # O ano é chave int no DTO e vira string no JSON dos metadados.
    assert detalhes["parse"]["colunas_desconhecidas_por_ano"]["2025"] == ["Coluna Nova Do Portal"]
    assert detalhes["parse"]["colunas_ausentes_por_ano"]["2025"] == ["cep"]


def test_xlsx_quebrado_nao_sobrescreve_o_parquet_do_ano(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _instalar(monkeypatch, _portal(tmp_path, publicados=[2024]))
    primeiro = run(ItbiConfig())

    parquet_do_ano = tmp_path / PASTA_PARSEADOS / NOME_PARQUET.format(ano=2024)
    bom = parquet_do_ano.read_bytes()
    valores_bons = pd.read_parquet(primeiro.output_path)["valor_transacao_declarado"].tolist()

    quebrada = aba_completa(linhas=2)
    quebrada["Valor de Transação (declarado pelo contribuinte)"] = ["N/D", "2.0"]
    _instalar(
        monkeypatch,
        _portal(tmp_path, publicados=[2024], abas={2024: {"JAN-2024": quebrada}}),
    )

    segundo = run(ItbiConfig())

    # A escrita é a última operação do ano: valor que não converte não custa o dado bom.
    assert parquet_do_ano.read_bytes() == bom
    assert 2024 in segundo.parse.falhas_por_ano
    assert segundo.anos_desatualizados == [2024]
    assert pd.read_parquet(segundo.output_path)["valor_transacao_declarado"].tolist() == valores_bons


def test_ano_despublicado_ou_nao_baixado_continua_no_parquet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 2024 veio de uma carga anterior e o portal parou de publicá-lo.
    escrever_xlsx(
        tmp_path / PASTA_ORIGINAIS / NOME_XLSX.format(ano=2024),
        {"JAN-2024": aba_completa(linhas=2)},
    )
    _instalar(monkeypatch, _portal(tmp_path, publicados=[2025]))

    despublicado = run(ItbiConfig())

    assert despublicado.coleta.anos_baixados == [2025]
    assert despublicado.consolidacao.anos_no_parquet == [2024, 2025]
    assert despublicado.anos_desatualizados == [2024]
    assert sorted(int(ano) for ano in pd.read_parquet(despublicado.output_path)["ano"].unique()) == [
        2024,
        2025,
    ]

    # Mesmo desfecho quando o portal publica o ano mas o download falha.
    _instalar(monkeypatch, _portal(tmp_path, publicados=[2024, 2025], falham=[2024]))

    sem_download = run(ItbiConfig())

    assert 2024 in sem_download.coleta.falhas_por_ano
    assert sem_download.consolidacao.anos_no_parquet == [2024, 2025]
    assert sem_download.anos_desatualizados == [2024]


def test_carga_sem_nenhum_ano_parseado_levanta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    anterior = tmp_path / OUTPUT_FILENAME
    anterior.write_bytes(b"parquet consolidado da carga anterior")
    _instalar(monkeypatch, _portal(tmp_path, publicados=[2025], falham=[2025]))

    with pytest.raises(ItbiCargaVaziaError):
        run(ItbiConfig())

    assert anterior.read_bytes() == b"parquet consolidado da carga anterior"


def test_run_sobrescreve_sem_acumular(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _instalar(monkeypatch, _portal(tmp_path, publicados=[2024, 2025]))

    primeiro = run(ItbiConfig())
    quadro_primeiro = pd.read_parquet(primeiro.output_path)

    segundo = run(ItbiConfig(), verbose=True)

    assert pd.read_parquet(segundo.output_path).equals(quadro_primeiro)
    assert sorted(caminho.name for caminho in (tmp_path / PASTA_ORIGINAIS).iterdir()) == [
        NOME_XLSX.format(ano=2024),
        NOME_XLSX.format(ano=2025),
    ]
    assert sorted(caminho.name for caminho in (tmp_path / PASTA_PARSEADOS).iterdir()) == [
        NOME_PARQUET.format(ano=2024),
        NOME_PARQUET.format(ano=2025),
    ]
    assert list(tmp_path.rglob("*.tmp")) == [], "temporário de escrita atômica ficou para trás"

    # --verbose apura e devolve mais: a contagem por ano só existe quando pedida.
    assert primeiro.linhas_por_ano is None
    assert segundo.linhas_por_ano == {2024: 2, 2025: 2}


def test_ano_publicado_e_nao_baixado_sai_em_anos_ausentes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 2024 é publicado, o download falha e não há arquivo anterior em disco: ele nunca chega ao
    # parquet, e é justamente esse caso que `anos_desatualizados` não enxerga.
    _instalar(monkeypatch, _portal(tmp_path, publicados=[2024, 2025], falham=[2024]))

    resultado = run(ItbiConfig())

    assert resultado.coleta.anos_publicados == [2024, 2025]
    assert resultado.consolidacao.anos_no_parquet == [2025]
    assert resultado.anos_ausentes == [2024]
    assert resultado.anos_desatualizados == []
