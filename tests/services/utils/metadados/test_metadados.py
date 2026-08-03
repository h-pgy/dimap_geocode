import json
from datetime import datetime
from pathlib import Path

import pytest

from services.utils.metadados import METADADOS_FILENAME, ler_metadados, registrar_execucao

ARQUIVO = "enderecos_fiscais.parquet"
VIZINHO = "nomes_logradouros.parquet"


def test_ler_metadados_sem_arquivo() -> None:
    # Primeira execução / checkout limpo: o JSON ainda não existe em data/.
    assert ler_metadados() == {}


def test_registro_de_sucesso_sobrescreve_so_a_propria_chave(tmp_path: Path) -> None:
    with registrar_execucao(VIZINHO, manual=True) as registro:
        registro.sucesso(registros=7)

    with registrar_execucao(ARQUIVO, manual=True) as registro:
        registro.sucesso(registros=42)

    metadados = ler_metadados()

    assert set(metadados) == {VIZINHO, ARQUIVO}
    assert metadados[VIZINHO].registros == 7, "o registro de um arquivo apagou o do outro"

    gravado = metadados[ARQUIVO]
    assert gravado.status == "sucesso"
    assert gravado.manual is True
    assert gravado.registros == 42
    assert gravado.last_successful_run == gravado.last_run
    assert gravado.erro is None

    # O JSON é lido por gente e pela fase 2: as datas ficam em dia-mês-ano com hora.
    bruto = json.loads((tmp_path / METADADOS_FILENAME).read_text(encoding="utf-8"))
    hoje = datetime.now().strftime("%d-%m-%Y")
    assert bruto[ARQUIVO]["last_run"].startswith(hoje)
    assert bruto[ARQUIVO]["last_successful_run"].startswith(hoje)


def test_registro_de_falha_guarda_erro_e_preserva_last_successful_run() -> None:
    with registrar_execucao(ARQUIVO, manual=True) as registro:
        registro.sucesso(registros=42)
    sucesso_anterior = ler_metadados()[ARQUIVO]

    # O registro é observabilidade, não try/except: o comando precisa continuar falhando.
    with pytest.raises(RuntimeError):
        with registrar_execucao(ARQUIVO, manual=False):
            raise RuntimeError("GeoSampa fora do ar")

    falha = ler_metadados()[ARQUIVO]

    assert falha.status == "falha"
    assert falha.manual is False
    assert falha.erro == "RuntimeError: GeoSampa fora do ar"
    assert falha.traceback is not None
    assert "RuntimeError" in falha.traceback
    assert falha.last_run >= sucesso_anterior.last_run

    # A memória do último sucesso sobrevive à tentativa que falhou — é dela que a fase 2 depende.
    assert falha.last_successful_run == sucesso_anterior.last_successful_run
    assert falha.registros == 42
